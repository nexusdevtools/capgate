# src/core/interface_manager.py

from typing import List, Optional

from base.logger import logger
# Import the global AppState directly
from base.state_management.state import AppState, get_state
# Import the official Interface schema
from db.schemas.interface import Interface

# You might still need shelltools if other parts of CapGate rely on it,
# but for interface management, the direct subprocess calls are now in iface_scanner.py.
# If shelltools is not used elsewhere, you can consider removing this import.


# We no longer need this custom InterfaceInfo class, as we use db.schemas.interface.Interface
# class InterfaceInfo:
#     ... (removed) ...

class InterfaceManager:
    """
    Manages access to and triggers detection of detailed information
    about system network interfaces, leveraging the AppState.
    """
    def __init__(self):
        # Get the global AppState instance
        self.app_state: AppState = get_state()
        # No need to load interfaces here; _initialize_core_state in runner.py will do that.
        # self.interfaces_info is effectively self.app_state.discovery_graph['interfaces']

    def _get_interfaces_from_state(self) -> List[Interface]:
        """
        Helper to retrieve Interface Pydantic models from AppState.
        """
        interfaces_data = self.app_state.discovery_graph.get("interfaces", {}).values()
        # Convert the stored dictionaries back into Pydantic Interface models
        interfaces_list: List[Interface] = []
        for iface_data in interfaces_data:
            try:
                interfaces_list.append(Interface(**iface_data))
            except Exception as e:
                logger.error(f"Failed to load Interface from AppState data: {iface_data} - {e}")
        return interfaces_list

    def get_interfaces(self, 
                       wireless_only: bool = False, 
                       monitor_capable_only: bool = False,
                       is_up_only: bool = False) -> List[Interface]: # Return type is now List[Interface]
        """
        Filter and return network interfaces from AppState.
        """
        # Get all interfaces as Pydantic models from the current state
        all_interfaces = self._get_interfaces_from_state()
        result = list(all_interfaces) # Create a mutable copy for filtering

        if wireless_only:
            # Assuming 'is_wireless' is a direct attribute on your Interface schema
            result = [iface for iface in result if iface.driver and iface.mode != "ethernet"] # Check for driver presence and not ethernet
        if monitor_capable_only:
            # Interface schema now has supports_monitor property directly
            result = [iface for iface in result if iface.supports_monitor]
        if is_up_only:
            # Interface schema now has is_up property directly
            result = [iface for iface in result if iface.is_up]
            
        logger.debug(f"Filtered interfaces: {[i.name for i in result]}")
        return result

    def get_interface_by_name(self, name: str) -> Optional[Interface]: # Return type is now Optional[Interface]
        """
        Retrieve a single interface by its name from AppState.
        """
        interface_data = self.app_state.discovery_graph.get("interfaces", {}).get(name)
        if interface_data:
            try:
                return Interface(**interface_data)
            except Exception as e:
                logger.error(f"Failed to load Interface '{name}' from AppState data: {interface_data} - {e}")
                return None
        return None

    def refresh_interfaces(self):
        """
        Triggers a re-scan of interfaces by the iface_scanner and updates the AppState.
        """
        logger.info("Refreshing interface list by re-running iface_scanner...")
        # Import the scanner dynamically here to avoid circular dependencies if runner imports InterfaceManager
        from vision.scanners.iface_scanner import scan_interfaces_and_update_state
        scan_interfaces_and_update_state(self.app_state)
        logger.info("Interface list refresh complete.")


# Example usage (for testing this file standalone):
if __name__ == "__main__":
    # In a standalone run, initialize the AppState and trigger the scan
    # It's crucial that iface_scanner.py also has its __main__ block removed
    # or updated to not run automatically when imported.
    from base.state_management.state import get_state
    from vision.scanners.iface_scanner import scan_interfaces_and_update_state
    from base.debug_tools import dump_app_state # Assuming this exists

    test_app_state = get_state()
    
    # Manually trigger the initial scan to populate AppState
    scan_interfaces_and_update_state(test_app_state)
    
    manager = InterfaceManager() # This will get the already populated AppState
    
    print(f"\n--- AppState after initial scan ---")
    dump_app_state(test_app_state)

    all_ifaces = manager.get_interfaces()
    print(f"\n--- All Detected Interfaces ({len(all_ifaces)}) ---")
    for iface in all_ifaces:
        print(iface.model_dump_json(indent=2)) # Use Pydantic's JSON export for nice printing

    wireless_ifaces = manager.get_interfaces(wireless_only=True)
    print(f"\n--- Wireless Interfaces ({len(wireless_ifaces)}) ---")
    for iface in wireless_ifaces:
        print(iface.name)
    
    # Refresh and check again
    manager.refresh_interfaces()
    print("\n--- After Refreshing Interfaces ---")
    all_ifaces_after_refresh = manager.get_interfaces()
    print(f"Total interfaces after refresh: {len(all_ifaces_after_refresh)}")
    if all_ifaces_after_refresh:
        print(f"Example refreshed interface: {all_ifaces_after_refresh[0].name}")

    # Test specific interface lookup
    test_iface_name = "lo" # default if no wireless
    if wireless_ifaces:
        test_iface_name = wireless_ifaces[0].name
    specific_iface = manager.get_interface_by_name(test_iface_name)
    if specific_iface:
        print(f"\n--- Details for Interface '{test_iface_name}' (from get_interface_by_name) ---")
        print(specific_iface.model_dump_json(indent=2))
    else:
        print(f"\nInterface '{test_iface_name}' not found by get_interface_by_name.")
