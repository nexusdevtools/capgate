# src/core/interface_controller.py
"""
Interface Controller: Provides high-level functions to manage network interface states,
such as enabling/disabling monitor mode, managing NetworkManager, etc.
"""

import re
from typing import Optional, Tuple

from core.logger import logger
from core.state_management.state import AppState
from helpers import shelltools
from db.schemas.interface import Interface

class InterfaceController:
    """
    Manages network interface states and operations, integrating with AppState.
    """
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.logger = logger

    def enable_monitor_mode(self, interface_name: str) -> Tuple[Optional[str], bool]:
        """
        Enable monitor mode on the given interface.
        - Manages NetworkManager to prevent interference.
        - Tries ip/iw first, then falls back to airmon-ng.
        - Parses the actual monitor interface name.
        - Updates the interface's mode in AppState if successful.
        
        Args:
            interface_name (str): The name of the interface to put into monitor mode.

        Returns:
            Tuple[Optional[str], bool]: A tuple containing:
                - The name of the new monitor interface (e.g., 'wlan0mon' or 'wlan0') if successful, None otherwise.
                - A boolean indicating if NetworkManager was set to unmanaged by this function.
        """
        actual_monitor_iface_name: Optional[str] = None
        nm_was_set_unmanaged: bool = False

        current_iface_data = self.app_state.get_discovery_graph().get("interfaces", {}).get(interface_name)
        if not current_iface_data or not current_iface_data.get('driver') or current_iface_data.get('mode') == "ethernet":
            self.logger.error(f"Interface {interface_name} not found or is not a wireless interface in AppState. Cannot enable monitor mode.")
            return None, False

        try:
            nm_managed_command = f"nmcli -g GENERAL.NM-MANAGED dev show {interface_name}"
            nm_managed_output = shelltools.run_command_no_check(
                nm_managed_command, require_root=True
            ).strip().lower()

            self.logger.debug(f"Output of '{nm_managed_command}': '{nm_managed_output}'")

            if nm_managed_output == "yes":
                self.logger.info(f"NetworkManager is managing {interface_name}. Setting to unmanaged.")
                shelltools.run_command(f"nmcli dev set {interface_name} managed no", require_root=True)
                nm_was_set_unmanaged = True
            else:
                self.logger.info(f"NetworkManager is not actively managing {interface_name} (was: '{nm_managed_output}').")

        except Exception as e:
            self.logger.warning(f"Could not check/modify NetworkManager status for {interface_name}: {e}. Proceeding with caution.")

        try:
            self.logger.info(f"Attempting to set {interface_name} to monitor mode using ip/iw.")
            shelltools.run_command(f"ip link set {interface_name} down", require_root=True)
            shelltools.run_command(f"iw dev {interface_name} set type monitor", require_root=True)
            shelltools.run_command(f"ip link set {interface_name} up", require_root=True)
            
            iw_info = shelltools.run_command(f"iw dev {interface_name} info", require_root=True)
            if "type monitor" in iw_info.lower():
                actual_monitor_iface_name = interface_name
                self.logger.info(f"[✓] {interface_name} successfully set to monitor mode using ip/iw.")
            else:
                self.logger.warning(f"ip/iw commands ran for {interface_name}, but mode is not 'monitor'. Current info: {iw_info}")
                raise Exception("Mode not 'monitor' after ip/iw attempt")

        except Exception as e_iw: 
            self.logger.warning(f"Setting monitor mode with ip/iw failed for {interface_name} (Error: {e_iw}). Trying airmon-ng...")
            try:
                self.logger.info(f"Attempting to set {interface_name} to monitor mode using airmon-ng.")
                airmon_output = shelltools.run_command(f"airmon-ng start {interface_name}", require_root=True)
                self.logger.debug(f"airmon-ng start {interface_name} output: {airmon_output}")

                match = re.search(
                    r"(?:monitor mode enabled on (\w+mon\d*|\w+mon)|(wlan\d+mon))",
                    airmon_output,
                    re.IGNORECASE
                )
                parsed_name = None
                if match:
                    parsed_name = match.group(1) or match.group(2)

                if parsed_name:
                    actual_monitor_iface_name = parsed_name.strip()
                    self.logger.info(f"[✓] Monitor mode enabled via airmon-ng. New monitor interface: {actual_monitor_iface_name}.")
                else:
                    iw_info_after_airmon = shelltools.run_command(f"iw dev {interface_name} info", require_root=True, check=False)
                    if "type monitor" in iw_info_after_airmon.lower():
                        actual_monitor_iface_name = interface_name
                        self.logger.info(f"[✓] airmon-ng seems to have set {interface_name} to monitor mode directly.")
                    else:
                        self.logger.error(f"airmon-ng ran but could not parse monitor interface name from output, and {interface_name} is not in monitor mode.")
            
            except Exception as e_airmon:
                self.logger.error(f"airmon-ng also failed to set monitor mode for {interface_name}. Error: {e_airmon}")
        
        finally:
            # Cleanup for NetworkManager if monitor mode setup FAILED and NM was unmanaged by us
            if actual_monitor_iface_name is None and nm_was_set_unmanaged:
                self.logger.info(f"Monitor mode setup failed for {interface_name}. Restoring NetworkManager management as immediate cleanup.")
                try:
                    shelltools.run_command(f"nmcli dev set {interface_name} managed yes", require_root=True)
                    nm_was_set_unmanaged = False # Indicate we've handled the restoration due to failure
                except Exception as e_nm_restore:
                    self.logger.error(f"Failed to restore NetworkManager management for {interface_name} after setup failure: {e_nm_restore}")

        if actual_monitor_iface_name:
            # Get a copy of the current interface data from AppState
            # Need to re-fetch as `Interface` object to use its methods and then update its dict representation
            iface_schema_data = self.app_state.get_discovery_graph().get("interfaces", {}).get(interface_name)
            if iface_schema_data:
                try:
                    # Create Pydantic model, update its mode, then convert back to dict
                    updated_iface = Interface(**iface_schema_data)
                    updated_iface.mode = "monitor"
                    self.app_state.update_interfaces({interface_name: updated_iface.to_dict()})
                    self.logger.info(f"[✓] AppState updated for {interface_name}: mode set to 'monitor'.")
                except Exception as e:
                    self.logger.warning(f"Could not update {interface_name} mode in AppState: {e}. Data: {iface_schema_data}")
            else:
                self.logger.warning(f"Successfully put {interface_name} into monitor mode, but interface data not found in AppState to update.")

            self.logger.info(f"[✓] Monitor mode active on: {actual_monitor_iface_name}. Original NM management was {'yes' if nm_was_set_unmanaged else 'no/other (not modified or restored yet)'}.")
        else:
            self.logger.error(f"[✘] Failed to enable monitor mode for {interface_name} after all attempts.")
        
        return actual_monitor_iface_name, nm_was_set_unmanaged

    def restore_interface_state(self, 
                                original_physical_interface: str, 
                                nm_was_set_unmanaged: bool, 
                                monitor_interface_name_final: Optional[str]):
        """
        Restores the network interface state after plugin execution.
        This includes restoring NetworkManager management and stopping monitor interfaces.

        Args:
            original_physical_interface (str): The name of the original physical interface.
            nm_was_set_unmanaged (bool): True if NetworkManager was set to unmanaged by the script.
            monitor_interface_name_final (Optional[str]): The name of the monitor interface that was created/used.
        """
        self.logger.info(f"[*] Starting cleanup for interface {original_physical_interface}...")

        # Restore NetworkManager management if it was changed by the script
        if nm_was_set_unmanaged: # Only restore if we changed it
            self.logger.info(f"Restoring NetworkManager management for {original_physical_interface}.")
            try:
                shelltools.run_command(f"nmcli dev set {original_physical_interface} managed yes", require_root=True)
                # After setting to managed, NM should ideally bring it up/reconnect.
                # Explicitly bringing it up might interfere with NM, but often harmless.
                # shelltools.run_command(f"ip link set {original_physical_interface} up", require_root=True, check=False)
                self.logger.info(f"NetworkManager management for {original_physical_interface} restored.")
            except Exception as e_nm_restore:
                self.logger.error(f"Failed to restore NetworkManager management for {original_physical_interface}: {e_nm_restore}")
        
        # Stop the monitor interface if it was distinct from the original and was created
        if monitor_interface_name_final and original_physical_interface and monitor_interface_name_final != original_physical_interface:
            self.logger.info(f"Attempting to stop monitor interface {monitor_interface_name_final} (if distinct).")
            try:
                # Use `airmon-ng stop` as it handles the removal of the VIF
                shelltools.run_command(f"airmon-ng stop {monitor_interface_name_final}", require_root=True, check=False)
                self.logger.info(f"Monitor interface {monitor_interface_name_final} stopped.")
            except Exception as e_stop_mon:
                self.logger.warning(f"Could not stop monitor interface {monitor_interface_name_final} with airmon-ng: {e_stop_mon}.")
        elif monitor_interface_name_final == original_physical_interface and monitor_interface_name_final:
            # If the original interface itself was put into monitor mode (e.g., via ip/iw),
            # try to set it back to managed mode (or 'auto' for common drivers).
            self.logger.info(f"Attempting to set {original_physical_interface} back to managed/auto mode.")
            try:
                shelltools.run_command(f"iw dev {original_physical_interface} set type managed", require_root=True)
                shelltools.run_command(f"ip link set {original_physical_interface} up", require_root=True)
                self.logger.info(f"Interface {original_physical_interface} set back to managed mode.")
            except Exception as e_revert:
                self.logger.warning(f"Failed to revert {original_physical_interface} from monitor mode to managed: {e_revert}.")
        
        # As a general measure, ensure the original physical interface is up.
        # This is particularly important if 'ip link set <iface> down' was used.
        if original_physical_interface:
             try:
                 self.logger.info(f"Ensuring original physical interface {original_physical_interface} is up.")
                 shelltools.run_command(f"ip link set {original_physical_interface} up", require_root=True, check=False)
             except Exception as e_link_up:
                 self.logger.warning(f"Failed to ensure link is up for {original_physical_interface}: {e_link_up}")

        self.logger.info(f"[*] Cleanup for interface {original_physical_interface} finished.")