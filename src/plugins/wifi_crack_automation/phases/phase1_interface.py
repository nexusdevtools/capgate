# src/plugins/wifi_crack_automation/phases/phase1_interface.py

import os
from typing import Dict, Any, Optional, List

# Core CapGate imports
from core.logger import logger
from core.state_management.context import CapGateContext # Use the main CapGateContext
from core.state_management.state import AppState # Access AppState via CapGateContext.state

# New core component for interface control
from core.interface_controller import InterfaceController # Import the new controller

from db.schemas.interface import Interface # Use the official Interface schema
# Removed imports from plugins.wifi_crack_automation.utils.interface
# as their logic has been moved or absorbed into core components.
# Removed old context imports.

def select_interface(app_context: CapGateContext) -> bool:
    """
    Phase 1: Selects a suitable wireless interface for monitor mode from AppState.
    It then attempts to enable monitor mode using the InterfaceController.

    Args:
        app_context (CapGateContext): The global CapGate context for the current run.

    Returns:
        bool: True if a monitor-capable interface is selected and successfully put into
              monitor mode; False otherwise.
    """
    logger.info("Phase 1: Selecting Wireless Interface and Enabling Monitor Mode")

    if os.geteuid() != 0:
        logger.critical("This plugin phase requires root privileges to manage interfaces.")
        return False

    # Get the AppState from the CapGateContext
    app_state: AppState = app_context.state
    # Instantiate the InterfaceController with the global AppState
    interface_controller = InterfaceController(app_state)

    # Get all interfaces as Pydantic models from the current AppState
    all_interfaces_data: Dict[str, Any] = app_state.get_discovery_graph().get("interfaces", {})
    all_iface_objects: List[Interface] = []
    for _, iface_data in all_interfaces_data.items():
        try:
            all_iface_objects.append(Interface(**iface_data))
        except Exception as e:
            logger.warning(f"Skipping malformed interface data from AppState: {iface_data} - {e}")
            continue

    if not all_iface_objects:
        logger.error("No interfaces found in AppState. Please ensure discovery has run.")
        return False

    # Filter for wireless, monitor-capable interfaces
    candidate_interfaces: List[Interface] = [
        iface for iface in all_iface_objects 
        if iface.driver and iface.mode != "ethernet" and iface.supports_monitor # is_wireless might not be directly in schema
    ]

    if not candidate_interfaces:
        logger.warning("No wireless interfaces capable of monitor mode found in AppState.")
        # Log all wireless interfaces found, even if not monitor capable, for user info
        all_wireless_names = [iface.name for iface in all_iface_objects if iface.driver and iface.mode != "ethernet"]
        logger.info(f"All detected wireless interfaces from AppState: {', '.join(all_wireless_names) or 'None'}")
        return False
    
    logger.info(f"Candidate interfaces from AppState for monitor mode: {[iface.name for iface in candidate_interfaces]}")
    
    selected_iface_obj: Optional[Interface] = None
    
    # Check for auto-selection (e.g., from CLI args or config in runtime_meta)
    auto_select: bool = app_context.get("auto_select_interface", False) 

    if auto_select:
        # Prioritize interfaces that are currently UP and connected, then monitor-capable
        # Or, implement specific logic for "best" interface selection (e.g., by signal quality, specific driver)
        if selected_iface_obj is None and candidate_interfaces:
            selected_iface_obj = candidate_interfaces[0] # Just pick the first one for auto-select if no other criteria
            if selected_iface_obj:
                logger.info("Auto-selected first available monitor-capable interface: %s", selected_iface_obj.name)
        else:
            logger.error("No monitor-capable interface found to auto-select.")
            return False
    elif len(candidate_interfaces) == 1:
        selected_iface_obj = candidate_interfaces[0]
        logger.info("Only one suitable interface found, auto-selecting: %s", selected_iface_obj.name)
    else:
        # Prompt user to select if multiple candidates
        print("\nAvailable monitor-capable wireless interfaces (from AppState):")
        for i, iface_obj in enumerate(candidate_interfaces, 1):
            # Use attributes from the Interface Pydantic model
            print(f"  {i}. {iface_obj.name} (Mode: {iface_obj.mode}, SSID: {iface_obj.ssid or 'N/A'})")
        try:
            choice_str = input(f"Select interface [1-{len(candidate_interfaces)}] (default 1): ").strip()
            if not choice_str: choice_str = "1"
            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(candidate_interfaces):
                selected_iface_obj = candidate_interfaces[choice_idx]
            else:
                logger.error(f"Invalid selection index.")
                return False
        except (ValueError, EOFError, IndexError) as e:
            logger.error(f"Invalid input for interface selection: {e}")
            return False
    
    if not selected_iface_obj:
        logger.error("No interface was selected from AppState list.")
        return False
    
    selected_physical_iface_name: str = selected_iface_obj.name

    # Store selected interface info in runtime_meta for this plugin run
    app_context.set("selected_interface_name", selected_physical_iface_name)
    app_context.set("original_interface_for_nm", selected_physical_iface_name) # Used for NetworkManager restoration later

    monitor_iface_name_actual: Optional[str] = None
    nm_unmanaged_flag: bool = False

    logger.info(f"Attempting to enable monitor mode on {selected_physical_iface_name}...")
    # Call the new InterfaceController's method
    monitor_iface_name_actual, nm_unmanaged_flag = interface_controller.enable_monitor_mode(selected_physical_iface_name)
    
    if monitor_iface_name_actual:
        # Store the actual monitor interface name and NM flag in runtime_meta
        app_context.set("monitor_interface", monitor_iface_name_actual)
        app_context.set("nm_was_set_unmanaged", nm_unmanaged_flag)
        logger.info(f"[✓] Phase 1 Succeeded. Monitor Interface: {monitor_iface_name_actual}, NM was set unmanaged by script: {nm_unmanaged_flag}")
        return True
    else:
        logger.error("[✘] Phase 1 Failed: Could not enable monitor mode.")
        app_context.set("monitor_interface", None)
        app_context.set("nm_was_set_unmanaged", nm_unmanaged_flag)
        return False

# Removed the __main__ block as plugin phases are not meant to be run standalone like this
# The runner orchestrates them.
# if __name__ == "__main__":
#     ...