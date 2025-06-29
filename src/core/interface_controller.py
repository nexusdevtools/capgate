# src/core/interface_controller.py
"""
Interface Controller: Provides low-level control over network interfaces,
including setting monitor mode, restoring original states, and managing
NetworkManager integration.
"""

import subprocess
import time
import re
from typing import Optional, Tuple, List, Dict, Any

from core.logger import logger
from helpers import shelltools
from core.state_management.state import AppState
from db.schemas.interface import Interface # Import Interface schema


class InterfaceController:
    """
    Manages direct control of network interfaces and their modes.
    """
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.logger = logger

    def enable_monitor_mode(self, interface: str) -> Tuple[Optional[str], bool]:
        """
        Sets a given wireless interface to monitor mode.
        Handles NetworkManager integration.

        Args:
            interface (str): The name of the wireless interface (e.g., 'wlan0').

        Returns:
            Tuple[Optional[str], bool]: A tuple containing:
                - The name of the interface in monitor mode (can be original or new 'mon' interface).
                - True if NetworkManager was managing the interface and was set to unmanaged by this function, False otherwise.
        """
        self.logger.info(f"Attempting to enable monitor mode on {interface}...")

        # 1. Check NetworkManager status
        nm_managed_by_us: bool = False
        try:
            # Check if NM is managing, and if it's in a connected/activating state
            nm_status_output = shelltools.run_command(f"nmcli -g GENERAL.STATE,GENERAL.NM-MANAGED dev show {interface}", require_root=True, check=False).strip().lower()
            
            # Example output: "10 (unmanaged)\nyes" or "30 (disconnected)\nyes" or "100 (connected)\nyes"
            # Split by newline and take the "yes"/"no" from the second line (GENERAL.NM-MANAGED)
            nm_managed_state = nm_status_output.splitlines()[-1] if "\n" in nm_status_output else nm_status_output
            
            if "yes" in nm_managed_state or "connected" in nm_status_output or "connecting" in nm_status_output or "activated" in nm_status_output: # Check both state and managed status
                self.logger.info(f"NetworkManager is managing {interface}. Setting to unmanaged.")
                shelltools.run_command(["nmcli", "dev", "disconnect", interface], require_root=True, check=False) # Disconnect first
                shelltools.run_command(["nmcli", "dev", "set", interface, "managed", "no"], require_root=True, check=False)
                nm_managed_by_us = True
                time.sleep(1) # Give NetworkManager time to release the interface
            else:
                self.logger.info(f"NetworkManager is not actively managing {interface} (was: '{nm_managed_state}').")
        except Exception as e:
            self.logger.warning(f"Could not check/unmanage NetworkManager for {interface}: {e}. Proceeding assuming manual management is needed.")

        # 2. Set interface to monitor mode using ip/iw
        try:
            self.logger.info(f"Attempting to set {interface} to monitor mode using ip/iw.")
            shelltools.run_command(["ip", "link", "set", interface, "down"], require_root=True)
            shelltools.run_command(["iw", "dev", interface, "set", "type", "monitor"], require_root=True)
            shelltools.run_command(["ip", "link", "set", interface, "up"], require_root=True)
            
            time.sleep(1) # Give it a moment to apply changes

            # Verify monitor mode
            iw_info_result = shelltools.run_command(f"iw dev {interface} info", require_root=True)
            if "type monitor" in iw_info_result:
                self.logger.info(f"[✓] {interface} successfully set to monitor mode using ip/iw.")
                
                # CRITICAL FIX: Update AppState with the new mode
                iface_data = self.app_state.get_discovery_graph().get("interfaces", {}).get(interface)
                if iface_data:
                    updated_iface = Interface(**iface_data)
                    updated_iface.mode = 'monitor'
                    updated_iface.is_up = True # Ensure it's marked as up
                    self.app_state.update_interfaces({interface: updated_iface.to_dict()})
                    self.logger.info(f"[✓] AppState updated for {interface}: mode set to 'monitor'.")

                self.logger.info(f"[✓] Monitor mode active on: {interface}. Original NM management was {'yes' if nm_managed_by_us else 'no/other'}.")
                return interface, nm_managed_by_us
            else:
                self.logger.error(f"[✘] Failed to set {interface} to monitor mode. 'type monitor' not found in iw info.")
                self.restore_interface_state(interface, nm_managed_by_us, interface) # Attempt to revert
                return None, False

        except FileNotFoundError:
            self.logger.error("Required command (ip or iw) not found. Please ensure wireless tools are installed.")
            return None, False
        except Exception as e:
            self.logger.error(f"Error setting {interface} to monitor mode: {e}")
            self.restore_interface_state(interface, nm_managed_by_us, interface) # Attempt to revert
            return None, False

    def restore_interface_state(self, original_iface_name: str, nm_was_managed: bool, current_monitor_iface_name: str) -> bool:
        """
        Restores a wireless interface from monitor mode to its original state.
        If NetworkManager was managing it, it attempts to return control.

        Args:
            original_iface_name (str): The original interface name (e.g., 'wlan0').
            nm_was_managed (bool): True if NetworkManager was managing it before monitor mode.
            current_monitor_iface_name (str): The interface name currently in monitor mode (e.g., 'wlan0mon' or 'wlan0').

        Returns:
            bool: True if restoration was successful, False otherwise.
        """
        self.logger.info(f"[*] Starting cleanup for interface {current_monitor_iface_name}...")
        
        cleanup_success = True

        try:
            # 1. Set interface type back to managed
            self.logger.info(f"Attempting to set {current_monitor_iface_name} back to managed/auto mode.")
            shelltools.run_command(["iw", "dev", current_monitor_iface_name, "set", "type", "managed"], require_root=True, check=False)
            shelltools.run_command(["ip", "link", "set", current_monitor_iface_name, "up"], require_root=True, check=False)
            self.logger.info(f"Interface {current_monitor_iface_name} set back to managed mode.")

            # CRITICAL FIX: Update AppState with the restored mode
            iface_data = self.app_state.get_discovery_graph().get("interfaces", {}).get(current_monitor_iface_name)
            if iface_data:
                updated_iface = Interface(**iface_data)
                updated_iface.mode = 'managed' # Assume managed mode is the desired restore for wireless
                updated_iface.is_up = True # Ensure it's up
                self.app_state.update_interfaces({current_monitor_iface_name: updated_iface.to_dict()})
                self.logger.debug(f"AppState updated for {current_monitor_iface_name}: mode set to 'managed'.")
            
            # 2. Return control to NetworkManager if it was managing it
            if nm_was_managed: # This should be the 'original NM management' status passed in.
                self.logger.info(f"Restoring NetworkManager management for {current_monitor_iface_name}.")
                shelltools.run_command(["nmcli", "dev", "set", current_monitor_iface_name, "managed", "yes"], require_root=True, check=False)
                self.logger.info(f"NetworkManager management for {current_monitor_iface_name} restored.")
            else:
                self.logger.info(f"NetworkManager was not managing {current_monitor_iface_name} originally, skipping NM restore.")


        except Exception as e:
            self.logger.warning(f"Failed to revert {current_monitor_iface_name} from monitor mode to managed: {e}. Manual intervention may be required.")
            cleanup_success = False

        # 3. Ensure the physical interface is up (redundant if nmcli manages, but safe)
        self.logger.info(f"Ensuring original physical interface {original_iface_name} is up.")
        shelltools.run_command(["ip", "link", "set", original_iface_name, "up"], require_root=True, check=False)
        
        self.logger.info(f"[*] Cleanup for interface {current_monitor_iface_name} finished.")
        return cleanup_success
    