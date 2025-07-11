# src/core/dhcp_dns_manager.py
"""
DHCP/DNS Manager: Provides high-level functions to set up and manage DHCP and DNS services,
primarily using dnsmasq.
"""

import os
import subprocess
import time
import shlex
from typing import Optional, List, Dict, Tuple

from base.logger import logger
from helpers import shelltools
from paths import CAPGATE_CONFIG_DIR # Only import the constant, not the function


class DhcpDnsManager:
    """
    Manages DHCP and DNS services using dnsmasq for rogue APs.
    """
    def __init__(self):
        self.logger = logger
        self._dnsmasq_process: Optional[subprocess.Popen[bytes]] = None
        self._dnsmasq_config_path: Optional[str] = None
        self._dns_hosts_path: Optional[str] = None
        
        # Ensure the specific dnsmasq config directory exists
        self.config_dir = os.path.join(CAPGATE_CONFIG_DIR, "dnsmasq")
        os.makedirs(self.config_dir, exist_ok=True) # <--- FIXED: Call os.makedirs directly
        self.logger.debug("[DhcpDnsManager] Config directory ensured: %s", self.config_dir)
    
    # Keeping __del__ as you added it, but note its execution is not guaranteed
    # on program exit (only on garbage collection). Explicit cleanup in plugin's
    # finally block is safer.
    def __del__(self):
        """
        Cleanup: Stop any running dnsmasq process and remove config files on object deletion.
        """
        self.logger.debug("[DhcpDnsManager] Cleaning up on object deletion...")
        self.stop_dhcp_dns() # This will now handle both stopping and removing files

    def _generate_dnsmasq_config(
        self,
        interface: str,
        dhcp_start_ip: str,
        dhcp_end_ip: str,
        dhcp_lease_time: str, # e.g., "12h"
        gateway_ip: str,      # IP of the rogue AP (our machine)
        dns_server_ip: Optional[str] = None, # Upstream DNS server (e.g., 8.8.8.8)
        dns_entries: Optional[Dict[str, str]] = None # {"hostname": "ip_address"}
    ) -> Optional[Tuple[str, Optional[str]]]:
        """
        Generates dnsmasq.conf and optional dns_hosts file.
        """
        config_path = os.path.join(self.config_dir, f"dnsmasq_{interface}.conf")
        hosts_path: Optional[str] = None

        config_content: List[str] = [ # Explicitly type config_content as List[str]
            f"interface={interface}",
            f"dhcp-range={dhcp_start_ip},{dhcp_end_ip},{dhcp_lease_time}",
            f"dhcp-option=3,{gateway_ip}", # Router/Gateway
            f"dhcp-option=6,{gateway_ip}", # DNS server (initially our machine)
            "log-queries",
            "log-dhcp",
            "no-resolv", # Do not read /etc/resolv.conf
        ]

        if dns_server_ip:
            config_content.append(f"server={dns_server_ip}")
        
        if dns_entries:
            hosts_path = os.path.join(self.config_dir, f"dnsmasq_{interface}.hosts")
            hosts_content: List[str] = [] # Explicitly type hosts_content as List[str]
            for hostname, ip_address in dns_entries.items():
                hosts_content.append(f"{ip_address} {hostname}")
            
            try:
                with open(hosts_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(hosts_content))
                config_content.append(f"addn-hosts={hosts_path}")
                self.logger.debug("[DhcpDnsManager] Generated dnsmasq hosts file: %s", hosts_path)
            except IOError as e:
                self.logger.error("[DhcpDnsManager] Failed to write dnsmasq hosts file to %s: %s", hosts_path, e)
                return None

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("\n".join(config_content))
            self.logger.debug("[DhcpDnsManager] Generated dnsmasq config: %s", config_path)
            return config_path, hosts_path
        except IOError as e:
            self.logger.error("[DhcpDnsManager] Failed to write dnsmasq config file to %s: %s", config_path, e)
            return None

    def start_dhcp_dns(
        self,
        interface: str,
        dhcp_start_ip: str,
        dhcp_end_ip: str,
        dhcp_lease_time: str,
        gateway_ip: str,
        dns_server_ip: Optional[str] = None,
        dns_entries: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Starts DHCP and DNS services on the given interface using dnsmasq.
        """
        self.logger.info("[DhcpDnsManager] Attempting to start DHCP/DNS on %s with range %s-%s...", interface, dhcp_start_ip, dhcp_end_ip)

        self.logger.debug("[DhcpDnsManager] Killing any existing dnsmasq processes...")
        shelltools.run_command("killall -q dnsmasq", require_root=True, check=False)
        time.sleep(1)

        config_tuple = self._generate_dnsmasq_config(
            interface, dhcp_start_ip, dhcp_end_ip, dhcp_lease_time,
            gateway_ip, dns_server_ip, dns_entries
        )
        if not config_tuple or not config_tuple[0]:
            return False
        
        config_path, hosts_path = config_tuple
        self._dnsmasq_config_path = config_path
        self._dns_hosts_path = hosts_path

        dnsmasq_cmd: List[str] = ["dnsmasq", "-C", config_path] # Explicitly type dnsmasq_cmd
        if hosts_path:
            dnsmasq_cmd.extend(["-H", hosts_path])

        self.logger.debug(f"[DhcpDnsManager] Executing dnsmasq: {shlex.join(dnsmasq_cmd)}")
        try:
            self._dnsmasq_process = subprocess.Popen(
                dnsmasq_cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                preexec_fn=os.setpgrp
            )
            time.sleep(3)

            if self._dnsmasq_process.poll() is not None:
                self.logger.error(f"[DhcpDnsManager] dnsmasq terminated prematurely. Exit code: {self._dnsmasq_process.returncode}")
                # You could try to capture dnsmasq's stderr from a Popen with PIPE if debugging issues.
                return False
            
            self.logger.info("[DhcpDnsManager] DHCP/DNS started successfully on %s.", interface)
            return True

        except FileNotFoundError:
            self.logger.error("[DhcpDnsManager] dnsmasq command not found. Please ensure it's installed and in your PATH.")
            return False
        except Exception as e:
            self.logger.error("[DhcpDnsManager] Failed to start dnsmasq on %s: %s", interface, e)
            if self._dnsmasq_process and self._dnsmasq_process.poll() is None:
                self._dnsmasq_process.terminate()
            return False

    def stop_dhcp_dns(self) -> bool:
        """
        Stops the running dnsmasq process and cleans up config files.
        """
        self.logger.info("[DhcpDnsManager] Attempting to stop dnsmasq process and clean up...")
        if self._dnsmasq_process and self._dnsmasq_process.poll() is None:
            self.logger.debug("[DhcpDnsManager] Terminating dnsmasq process.")
            self._dnsmasq_process.terminate()
            try:
                self._dnsmasq_process.wait(timeout=5)
                self.logger.info("[DhcpDnsManager] dnsmasq process stopped successfully.")
            except subprocess.TimeoutExpired:
                self.logger.warning("[DhcpDnsManager] dnsmasq did not terminate gracefully, killing.")
                self._dnsmasq_process.kill()
                self._dnsmasq_process.wait()
        else:
            self.logger.info("[DhcpDnsManager] No active dnsmasq process found to stop.")

        # Cleanup config files (moved to _remove_config_files for consistency if __del__ uses it)
        self._remove_config_files()
        
        return True

    def _remove_config_files(self):
        """
        Helper to remove dnsmasq configuration files.
        """
        if self._dnsmasq_config_path and os.path.exists(self._dnsmasq_config_path):
            try:
                os.remove(self._dnsmasq_config_path)
                self.logger.debug("[DhcpDnsManager] Removed dnsmasq config file: %s", self._dnsmasq_config_path)
            except OSError as e:
                self.logger.warning("[DhcpDnsManager] Could not remove dnsmasq config file %s: %s", self._dnsmasq_config_path, e)
        
        if self._dns_hosts_path and os.path.exists(self._dns_hosts_path):
            try:
                os.remove(self._dns_hosts_path)
                self.logger.debug("[DhcpDnsManager] Removed dnsmasq hosts file: %s", self._dns_hosts_path)
            except OSError as e:
                self.logger.warning("[DhcpDnsManager] Could not remove dnsmasq hosts file %s: %s", self._dns_hosts_path, e)