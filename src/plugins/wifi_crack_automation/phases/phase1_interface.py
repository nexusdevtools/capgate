# /home/nexus/dev/projects/capgate/src/capgate/plugins/wifi_crack_automation/phases/phase1_interface.py
import os
import sys
from typing import Dict, Any, Optional, List

from core.interface_manager import InterfaceInfo  # For type hinting if used directly
from plugins.wifi_crack_automation.utils.interface import enable_monitor_mode, list_wireless_interfaces, list_all_interfaces
from plugins.wifi_crack_automation.state.context import context, reset_context, set_context, get_context
from core.context import AppContext  # If you have a central AppContext type definition

from core.logger import logger

class MockInterfaceInfo:
    def __init__(self, name, is_wireless, supports_monitor, is_usb=False, current_mode="unknown", ip_address=None, ssid=None):
        self.name = name
        self.is_wireless = is_wireless
        self.supported_modes = ["monitor", "managed"] if supports_monitor else ["managed"]
        self.is_usb = is_usb
        self.current_mode = current_mode
        self.ip_address = ip_address
        self.ssid = ssid

    def supports_monitor_mode(self) -> bool:
        return "monitor" in self.supported_modes

    def __repr__(self):
        usb_tag = "[USB] " if self.is_usb else ""
        mon_tag = "[Mon Capable] " if self.supports_monitor_mode() else "[No Mon] "
        return f"{usb_tag}{self.name} {mon_tag}({self.current_mode}, SSID: {self.ssid or 'N/A'})"

def get_mock_interfaces_rich() -> List[MockInterfaceInfo]:
    return [
        MockInterfaceInfo(name="mock_usb0", is_wireless=True, supports_monitor=True, is_usb=True, current_mode="managed", ssid="MockWifi"),
        MockInterfaceInfo(name="mock_wlan0", is_wireless=True, supports_monitor=True, is_usb=False, current_mode="monitor"),
        MockInterfaceInfo(name="mock_eth0", is_wireless=False, supports_monitor=False, current_mode="ethernet", ip_address="192.168.1.100")
    ]

def select_interface(plugin_local_context: Dict[str, Any]) -> bool:
    logger.info("Phase 1: Selecting Wireless Interface")

    if os.geteuid() != 0:
        logger.critical("This plugin phase requires root privileges to manage interfaces.")
        return False

    mock_mode: bool = plugin_local_context.get("mock_mode", False)
    app_context: Optional[Any] = plugin_local_context.get("app_context")
    
    all_iface_objects: List[Any] = []
    raw_interface_names: List[str] = []
    selected_physical_iface_name: str = ""

    if mock_mode:
        mock_iface_infos = get_mock_interfaces_rich()
        if not mock_iface_infos:
            logger.error("[MOCK MODE] No mock interfaces defined.")
            return False
        selected_physical_iface_name = mock_iface_infos[0].name
        logger.info(f"[MOCK MODE] Using mock interface: {selected_physical_iface_name}")
    elif app_context and app_context.get("interfaces"):
        all_iface_objects = app_context.get("interfaces", [])
        if not all_iface_objects:
            logger.error("AppContext provided, but no interfaces found. InterfaceManager might have failed.")
            return False
        logger.info(f"Using detailed interface list from AppContext ({len(all_iface_objects)} total interfaces found).")

        candidate_interfaces: List[Any] = [
            iface for iface in all_iface_objects 
            if getattr(iface, 'is_wireless', False) and hasattr(iface, 'supports_monitor_mode') and iface.supports_monitor_mode()
        ]

        if not candidate_interfaces:
            logger.warning("No wireless interfaces capable of monitor mode found from AppContext list.")
            all_wireless_names = [iface.name for iface in all_iface_objects if getattr(iface, 'is_wireless', False)]
            logger.info(f"All detected wireless interfaces from AppContext (may not be monitor capable): {', '.join(all_wireless_names) or 'None'}")
            return False
        
        logger.info(f"Candidate interfaces from AppContext for monitor mode: {[iface.name for iface in candidate_interfaces]}")
        
        selected_iface_obj: Optional[Any] = None
        auto_select: bool = plugin_local_context.get("auto_select", False)

        if auto_select:
            usb_monitor_adapters = [iface for iface in candidate_interfaces if getattr(iface, 'is_usb', False)]
            if usb_monitor_adapters:
                selected_iface_obj = usb_monitor_adapters[0]
                if selected_iface_obj is not None:
                    logger.info("Auto-selected USB monitor-capable interface: %s", selected_iface_obj.name)
                else:
                    logger.error("No USB monitor-capable interface found to auto-select.")
            else:
                selected_iface_obj = candidate_interfaces[0]
                if selected_iface_obj is not None:
                    logger.info("Auto-selected first available monitor-capable interface: %s", selected_iface_obj.name)
                else:
                    logger.error("No monitor-capable interface found to auto-select.")
        elif len(candidate_interfaces) == 1:
            selected_iface_obj = candidate_interfaces[0]
            if selected_iface_obj is not None:
                logger.info("Only one suitable interface found, auto-selecting: %s", selected_iface_obj.name)
            else:
                logger.error("Only one candidate interface found, but it is None.")
                return False
        else:
            print("\nAvailable monitor-capable wireless interfaces (from AppContext):")
            for i, iface_obj in enumerate(candidate_interfaces, 1):
                usb_tag = "[USB] " if getattr(iface_obj, 'is_usb', False) else ""
                current_mode = getattr(iface_obj, 'current_mode', 'N/A')
                ssid = getattr(iface_obj, 'ssid', 'N/A')
                print(f"  {i}. {usb_tag}{iface_obj.name} (Mode: {current_mode}, SSID: {ssid or 'None'}) - Monitor Capable")
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
            logger.error("No interface was selected from AppContext list.")
            return False
        selected_physical_iface_name = selected_iface_obj.name
    
    else:
        logger.info("AppContext not available or no interfaces provided; attempting direct discovery...")
        raw_interface_names = list_wireless_interfaces()
        if not raw_interface_names:
            logger.info("'list_wireless_interfaces' (iw dev) found nothing. Trying 'list_all_interfaces' (airmon-ng/iwconfig)...")
            raw_interface_names = list_all_interfaces()
            if not raw_interface_names:
                logger.error("No wireless interfaces detected by any utility (iw dev, airmon-ng, iwconfig).")
                return False
        
        logger.info(f"Discovered wireless interfaces (names only): {', '.join(raw_interface_names)}")
        auto_select: bool = plugin_local_context.get("auto_select", False)
        if auto_select or len(raw_interface_names) == 1:
            selected_physical_iface_name = raw_interface_names[0]
            logger.info(f"Auto-selected interface (direct discovery): {selected_physical_iface_name}")
        else:
            print("\nAvailable wireless interfaces (direct discovery):")
            for i, iface_name_str in enumerate(raw_interface_names, 1):
                print(f"  {i}. {iface_name_str} (Capabilities not pre-fetched; will attempt monitor mode)")
            try:
                choice_str = input(f"Select interface [1-{len(raw_interface_names)}] (default 1): ").strip()
                if not choice_str: choice_str = "1"
                choice_idx = int(choice_str) - 1
                if 0 <= choice_idx < len(raw_interface_names):
                    selected_physical_iface_name = raw_interface_names[choice_idx]
                else:
                    logger.error(f"Invalid selection index.")
                    return False
            except (ValueError, EOFError, IndexError) as e:
                logger.error(f"Invalid input for interface selection: {e}")
                return False
        if not selected_physical_iface_name:
            logger.error("No interface was selected (direct discovery).")
            return False

    # --- Use context file for state ---
    set_context("interface", selected_physical_iface_name)
    set_context("original_interface_for_nm", selected_physical_iface_name)

    monitor_iface_name_actual: Optional[str] = None
    nm_unmanaged_flag: bool = False

    if mock_mode:
        monitor_iface_name_actual = f"{selected_physical_iface_name}mon"
        nm_unmanaged_flag = False 
        logger.info(f"[MOCK MODE] Pretending to enable monitor mode on {selected_physical_iface_name} -> {monitor_iface_name_actual}")
    else:
        logger.info(f"Attempting to enable monitor mode on {selected_physical_iface_name}...")
        monitor_iface_name_actual, nm_unmanaged_flag = enable_monitor_mode(selected_physical_iface_name, app_context)
    
    if monitor_iface_name_actual:
        set_context("monitor_interface", monitor_iface_name_actual)
        set_context("nm_was_set_unmanaged", nm_unmanaged_flag)
        logger.info(f"[✓] Phase 1 Succeeded. Monitor Interface: {monitor_iface_name_actual}, NM was set unmanaged by script: {nm_unmanaged_flag}")
        return True
    else:
        logger.error("[✘] Phase 1 Failed: Could not enable monitor mode.")
        set_context("monitor_interface", None)
        set_context("nm_was_set_unmanaged", nm_unmanaged_flag)
        return False

if __name__ == "__main__":
    print("=== CapGate Phase 1: Interface Selection Standalone Test ===")
    _mock_mode_standalone = True
    if len(sys.argv) > 1 and sys.argv[1].lower() == "system":
        _mock_mode_standalone = False
        print("Attempting SYSTEM test (non-mocked, requires sudo and iw/nmcli etc. to be installed).")
    else:
        print("Running in MOCK mode. To run system test: python phase1_interface.py system")

    test_context: Dict[str, Any] = {
        "auto_select": False, 
        "mock_mode": _mock_mode_standalone, 
        "app_context": None, 
    }

    reset_context()  # Always reset before test

    if select_interface(test_context):
        logger.info("Standalone Test: Phase 1 completed successfully.")
    else:
        logger.error("Standalone Test: Phase 1 failed.")
    
    logger.info(f"Final standalone context: {context}")