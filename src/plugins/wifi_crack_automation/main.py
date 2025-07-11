# /home/nexus/capgate/src/plugins/wifi_crack_automation/main.py

import json
from typing import Optional, Any
import sys
import os

# Core CapGate imports
from base.logger import logger
# Removed direct shelltools import from here unless specifically needed outside InterfaceController/scanners
# from helpers import shelltools 
from base.state_management.context import CapGateContext
from base.interface_controller import InterfaceController

# Imports for phases (these phases will need refactoring next!)
from plugins.wifi_crack_automation.phases.phase1_interface import select_interface
from plugins.wifi_crack_automation.phases.phase2_scan import scan_for_networks
from plugins.wifi_crack_automation.phases.phase3_capture import capture_handshake
from plugins.wifi_crack_automation.phases.phase4_crack import crack_handshake

# Define plugin_name globally for use in __main__ block as well
plugin_name = "wifi_crack_automation" 

def run(app_context: CapGateContext, *plugin_args: str):
    """
    Main entry point for the Wi-Fi Crack Automation plugin.
    Manages the overall workflow from interface setup to cracking,
    and ensures proper cleanup of network states.
    """
    logger.info(f"[PLUGIN {plugin_name}] Starting execution...")
    
    interface_controller = InterfaceController(app_context.state)

    # --- Populate runtime_meta from global AppContext and plugin_args ---
    # Retrieve settings from app_context.state.user_config (AppState's user_config)
    app_context.set("scan_duration_seconds", app_context.state.user_config.get("wifi_scan_duration", 15))
    app_context.set("network_security_filter", app_context.state.user_config.get("wifi_security_filter", "WPA"))
    
    # Handle auto_select directly from plugin_args
    if "--auto" in plugin_args:
        app_context.set("auto_select_interface", True)
    else:
        app_context.set("auto_select_interface", False)

    target_bssid_cli_arg: Optional[str] = None
    if "--target" in plugin_args:
        try:
            target_bssid_cli_arg = plugin_args[plugin_args.index("--target") + 1]
            app_context.set("target_bssid_cli_arg", target_bssid_cli_arg)
            logger.info(f"[PLUGIN {plugin_name}] Received target BSSID from CLI: {target_bssid_cli_arg}")
        except IndexError:
            logger.error(f"[PLUGIN {plugin_name}] --target option requires a BSSID argument.")

    # --- Main plugin workflow with cleanup ---
    try:
        # Phase 1: Interface Selection and Monitor Mode
        if not select_interface(app_context): # Pass CapGateContext
            logger.error(f"[PLUGIN {plugin_name}] Halted: Interface Selection & Monitor Mode (Phase 1) failed.")
            return False

        monitor_interface_name = app_context.get("monitor_interface")
        if not monitor_interface_name:
            logger.error(f"[PLUGIN {plugin_name}] Halted: Monitor interface not available after Phase 1.")
            return False
        logger.info(f"[PLUGIN {plugin_name}] Phase 1 complete. Using monitor interface: {monitor_interface_name}")

        # Phase 2: Scan for Networks
        # CRITICAL: Pass CapGateContext. phase2_scan.py needs to be updated next.
        selected_target_network = scan_for_networks(app_context) 
        if not selected_target_network:
            logger.error(f"[PLUGIN {plugin_name}] Halted: Network Scan (Phase 2) failed or no target selected.")
            return False
        
        target_bssid = app_context.get("target_bssid")
        target_channel = app_context.get("target_channel")
        target_essid = app_context.get("target_essid")
        logger.info(f"[PLUGIN {plugin_name}] Phase 2 complete. Target: ESSID='{target_essid}', BSSID={target_bssid}, Channel={target_channel}")

        # Phase 3: Capture Handshake
        # CRITICAL: Pass CapGateContext. phase3_capture.py needs to be updated.
        if not capture_handshake(app_context):
            logger.error(f"[PLUGIN {plugin_name}] Halted: Capture Handshake (Phase 3) failed.")
            return False
        logger.info(f"[PLUGIN {plugin_name}] Phase 3 complete. Handshake capture attempted for BSSID: {target_bssid}.")

        # Phase 4: Crack Handshake
        # CRITICAL: Pass CapGateContext. phase4_crack.py needs to be updated.
        crack_success = crack_handshake(app_context)
        logger.info(f"[PLUGIN {plugin_name}] Phase 4 complete. Cracking attempted.")

        logger.info(f"\n===== PLUGIN {plugin_name} SUMMARY =====")
        summary_for_print = app_context.to_dict() # Get runtime_meta as dict
        try:
            print(json.dumps(summary_for_print, indent=4, default=str)) 
        except TypeError as e:
            logger.error(f"Could not serialize plugin context for summary: {e}")
            print(f"Raw app_context.runtime_meta (potential serialization issue): {summary_for_print}")

        if crack_success:
            logger.info(f"\n[✓] SUCCESS: [PLUGIN {plugin_name}] Crack complete. Key found: {app_context.get('key_found')}")
        else:
            logger.error(f"\n[✘] FAILURE: [PLUGIN {plugin_name}] Crack unsuccessful or not attempted.")

    except Exception as e:
        from base.debug_tools import print_exception
        print_exception(e, f"[PLUGIN {plugin_name}] An unexpected error occurred during execution")
        return False

    finally:
        logger.info(f"[*] [PLUGIN {plugin_name}] Starting cleanup phase...")

        nm_was_set_unmanaged: bool = app_context.get("nm_was_set_unmanaged", False)
        original_physical_interface: Optional[str] = app_context.get("original_interface_for_nm")
        monitor_interface_name_final: Optional[str] = app_context.get("monitor_interface")

        if original_physical_interface:
            interface_controller.restore_interface_state(
                original_physical_interface, 
                nm_was_set_unmanaged, 
                monitor_interface_name_final
            )
        else:
            logger.info("No original physical interface recorded. Skipping interface cleanup.")

        logger.info(f"[*] [PLUGIN {plugin_name}] Execution and cleanup finished.")
        return True

# --- Standalone Debugging Block ---
if __name__ == "__main__":
    # Adjust sys.path to ensure core CapGate modules are discoverable
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        sys.path.insert(0, os.path.join(project_root, 'src'))

    from runner import CapGateRunner
    # No direct is_root import needed here; runner will handle privileged operations

    logger.info("--- Starting Wi-Fi Crack Automation Plugin Standalone Test ---")

    mock_cli_state: dict[str, Any] = {} 
    runner = CapGateRunner(cli_state=mock_cli_state) 

    test_plugin_args = ["--auto"] 

    logger.info(f"Simulating plugin run with args: {test_plugin_args}")
    success = runner.run_plugin(plugin_name, *test_plugin_args)

    if success:
        logger.info("--- Wi-Fi Crack Automation Plugin Standalone Test: SUCCEEDED ---")
    else:
        logger.error("--- Wi-Fi Crack Automation Plugin Standalone Test: FAILED ---")
        logger.info("--- End of Standalone Test ---")
