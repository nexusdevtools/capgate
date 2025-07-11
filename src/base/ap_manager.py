# src/core/ap_manager.py
"""
AP Manager: Provides high-level functions to create and manage Access Points (APs),
primarily using hostapd.
"""

import os
import subprocess
import time
import shlex
from typing import Optional, List, Dict, Any # Added List import explicitly

from base.logger import logger
from base.state_management.state import AppState
from helpers import shelltools
from db.schemas.interface import Interface


class APManager:
    """
    Manages Access Point creation and control using hostapd.
    """
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.logger = logger
        # FIXED: Corrected Popen type hint from str to bytes, as stdout/stderr are DEVNULL and not text=True
        self._hostapd_process: Optional[subprocess.Popen[bytes]] = None 
        self._hostapd_config_path: Optional[str] = None

    def _generate_hostapd_config(
        self,
        interface: str,
        ssid: str,
        channel: int,
        hw_mode: str, # e.g., 'g', 'n', 'a'
        config_dir: str = "/tmp"
    ) -> Optional[str]:
        """
        Generates a hostapd configuration file.
        """
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, f"hostapd_{interface}.conf")

        config_content: List[str] = [ # Explicitly type config_content as List[str]
            f"interface={interface}",
            "driver=nl80211", # nl80211 is the standard Linux driver interface for wireless
            f"ssid={ssid}",
            f"hw_mode={hw_mode}",
            f"channel={channel}",
            "macaddr_acl=0", # Allow all MACs
            "accept_mac_file=/dev/null",
            "auth_algs=1", # Open System authentication
            "wmm_enabled=1", # Wi-Fi Multimedia
            "ignore_broadcast_ssid=0", # Broadcast SSID
            # No WPA/WPA2/WPA3 settings for an open Evil Twin redirect
            # For a fake AP with password, you'd add wpa=2, wpa_passphrase=..., rsne_pairwise=...
        ]

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("\n".join(config_content))
            self.logger.debug("[APManager] Generated hostapd config: %s", config_path)
            return config_path
        except IOError as e:
            self.logger.error("[APManager] Failed to write hostapd config file to %s: %s", config_path, e)
            return None

    def start_ap(
        self,
        interface: str,
        ssid: str,
        channel: int,
        hw_mode: str,
        mac_spoof: Optional[str] = None
    ) -> bool:
        """
        Starts an Access Point on the given interface using hostapd.
        
        Args:
            interface (str): The wireless interface to use (must not be in monitor mode).
            ssid (str): The SSID (network name) of the AP.
            channel (int): The channel to host the AP on.
            hw_mode (str): Hardware mode ('g' for 2.4GHz, 'a' for 5GHz, 'n' for HT mode).
            mac_spoof (Optional[str]): MAC address to spoof the AP's interface to.

        Returns:
            bool: True if the AP started successfully, False otherwise.
        """
        self.logger.info("[APManager] Attempting to start AP '%s' on %s (channel %s, mode %s)...", ssid, interface, channel, hw_mode)

        current_iface_data_dict: Optional[Dict[str, Any]] = self.app_state.get_discovery_graph().get("interfaces", {}).get(interface)
        if not current_iface_data_dict:
            self.logger.error("[APManager] Interface %s not found in AppState. Cannot start AP.", interface)
            return False
        
        try:
            current_iface_obj: Interface = Interface(**current_iface_data_dict)
        except Exception as e:
            self.logger.error(f"[APManager] Invalid interface data in AppState for {interface}: {e}. Cannot start AP.")
            return False

        if not current_iface_obj.driver or current_iface_obj.mode == "ethernet":
            self.logger.error(f"[APManager] Interface {interface} is not a wireless interface (Driver: {current_iface_obj.driver}, Mode: {current_iface_obj.mode}). Cannot start AP.")
            return False
        
        if current_iface_obj.mode == 'monitor':
            self.logger.error(f"[APManager] Interface {interface} is currently in monitor mode. Cannot start AP. Please stop monitor mode first.")
            return False
        
        # 1. Spoof MAC if requested
        if mac_spoof:
            self.logger.info("[APManager] Spoofing MAC of %s to %s...", interface, mac_spoof)
            try:
                shelltools.run_command(["ip", "link", "set", interface, "down"], require_root=True, check=False)
                shelltools.run_command(["ip", "link", "set", interface, "address", mac_spoof], require_root=True)
                shelltools.run_command(["ip", "link", "set", interface, "up"], require_root=True, check=False)
                self.logger.info("[APManager] MAC spoof successful for %s.", interface)
            except Exception as e:
                self.logger.error("[APManager] Failed to spoof MAC for %s: %s", interface, e)
                return False
            
            current_iface_obj.mac = mac_spoof.upper()
            self.app_state.update_interfaces({interface: current_iface_obj.to_dict()})
            self.logger.debug("[APManager] AppState updated with new MAC for %s.", interface)


        # 2. Generate hostapd config
        config_path = self._generate_hostapd_config(interface, ssid, channel, hw_mode)
        if not config_path:
            return False

        self._hostapd_config_path = config_path # Store for later cleanup

        # 3. Start hostapd process
        hostapd_cmd: List[str] = ["hostapd", config_path] # Explicitly type as List[str]
        self.logger.debug(f"[APManager] Executing hostapd: {shlex.join(hostapd_cmd)}")
        try:
            self._hostapd_process = subprocess.Popen( # Assignment here matches the new Popen[bytes] hint
                hostapd_cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                preexec_fn=os.setpgrp
            )
            time.sleep(3) 

            if self._hostapd_process.poll() is not None:
                self.logger.error(f"[APManager] hostapd terminated prematurely. Exit code: {self._hostapd_process.returncode}")
                return False
            self.logger.debug("[APManager] hostapd process started successfully.")
            # Wait a bit to ensure hostapd is fully up
            time.sleep(2)
            # Check if hostapd is running
            if self._hostapd_process.poll() is not None:
                self.logger.error("[APManager] hostapd process is not running after start. Check logs for errors.")
                return False
            # If we reach here, hostapd started successfully
            self.logger.info("[APManager] hostapd started successfully.")
            self.logger.info("[APManager] AP '%s' started successfully on %s.", ssid, interface)

            current_iface_obj.mode = 'AP'
            current_iface_obj.ssid = ssid
            current_iface_obj.channel_frequency = f"{channel} ({hw_mode} band)"
            current_iface_obj.is_up = True
            current_iface_obj.is_wireless = True # This field should exist in Interface schema now
            current_iface_obj.supports_ap = True
            current_iface_obj.supports_managed = False # AP mode does not support managed
            current_iface_obj.supports_monitor = False # AP mode does not support monitor
            current_iface_obj.supports_mesh = False # AP mode does not support mesh
            current_iface_obj.supports_p2p = False # AP mode does not support P2P
            current_iface_obj.supports_adhoc = False # AP mode does not support adhoc
            current_iface_obj.supports_wds = False # AP mode does not support WDS
            current_iface_obj.supports_vap = False # AP mode does not support VAP
            current_iface_obj.supports_tdma = False # AP mode does not support TDMA
            current_iface_obj.supports_mimo = False # AP mode does not support MIMO
            current_iface_obj.supports_5ghz = False # Default to False, set later if hw_mode supports it
            current_iface_obj.supports_6ghz = False # Default to False, set later if hw_mode supports it
            current_iface_obj.supports_2ghz = False # Default to False, set later if hw_mode supports it
            current_iface_obj.supports_11ax = False # Default to False, set later if hw_mode supports it
            current_iface_obj.supports_11ac = False # Default to False, set later if hw_mode supports it
            current_iface_obj.supports_11n = False # Default to False, set later if hw_mode supports it
            current_iface_obj.supports_11g = False # Default to False

            if 'g' in hw_mode:
                current_iface_obj.supports_2ghz = True
                current_iface_obj.supports_11g = True
                current_iface_obj.supports_11b = True
            if 'a' in hw_mode:
                current_iface_obj.supports_5ghz = True
                current_iface_obj.supports_11a = True
            if 'n' in hw_mode:
                current_iface_obj.supports_11n = True
            if 'ac' in hw_mode:
                current_iface_obj.supports_11ac = True
            if 'ax' in hw_mode:
                current_iface_obj.supports_11ax = True

            self.app_state.update_interfaces({interface: current_iface_obj.to_dict()})
            self.logger.debug("[APManager] AppState updated for %s: mode set to 'AP'.", interface)

            return True

        except FileNotFoundError:
            self.logger.error("[APManager] hostapd command not found. Please ensure it's installed and in your PATH.")
            return False
        except Exception as e:
            self.logger.error("[APManager] Failed to start hostapd on %s: %s", interface, e)
            if self._hostapd_process and self._hostapd_process.poll() is None:
                self._hostapd_process.terminate()
            return False

    def stop_ap(self) -> bool:
        """
        Stops the running Access Point and cleans up.
        """
        self.logger.info("[APManager] Attempting to stop hostapd process...")
        if self._hostapd_process and self._hostapd_process.poll() is None:
            self.logger.debug("[APManager] Terminating hostapd process.")
            self._hostapd_process.terminate()
            try:
                self._hostapd_process.wait(timeout=5)
                self.logger.info("[APManager] hostapd process stopped successfully.")
            except subprocess.TimeoutExpired:
                self.logger.warning("[APManager] hostapd did not terminate gracefully, killing.")
                self._hostapd_process.kill()
                self._hostapd_process.wait()
        else:
            self.logger.info("[APManager] No active hostapd process found to stop.")

        if self._hostapd_config_path and os.path.exists(self._hostapd_config_path):
            try:
                os.remove(self._hostapd_config_path)
                self.logger.debug("[APManager] Removed hostapd config file: %s", self._hostapd_config_path)
            except OSError as e:
                self.logger.warning("[APManager] Could not remove hostapd config file %s: %s", self._hostapd_config_path, e)

        return True
