# /home/nexus/dev/projects/capgate/src/capgate/plugins/wifi_crack_automation/main.py

import json
from typing import Optional

# Correct relative import for logger (assuming 'core' is relative to 'capgate/src')
# You might need to adjust sys.path or the import if 'core' is not directly accessible
# from this file's perspective when run standalone.
# For CapGate's internal structure, 'from core.logger import logger' is typically how it's done.
from core.logger import logger
# Correct relative import for helpers.shelltools
from helpers import shelltools
# Correct relative imports for phases
from plugins.wifi_crack_automation.phases.phase1_interface import \
    select_interface
from plugins.wifi_crack_automation.phases.phase2_scan import scan_for_networks
from plugins.wifi_crack_automation.phases.phase3_capture import \
    capture_handshake
from plugins.wifi_crack_automation.phases.phase4_crack import crack_handshake
# Correct relative import for plugin's local context
from plugins.wifi_crack_automation.state.context import \
    context as plugin_local_context
from plugins.wifi_crack_automation.state.context import \
    reset_context as reset_plugin_local_context


# Define a mock AppContext if you want to run main.py directly for debugging
class MockAppContext:
    def __init__(self, initial_values=None):
        self._context = initial_values if initial_values is not None else {}

    def get(self, key, default=None):
        return self._context.get(key, default)

    def __setitem__(self, key, value):
        self._context[key] = value

    def __getitem__(self, key):
        return self._context[key]

# The CapGateRunner calls plugin modules with: plugin_module.run(app_context_instance, *cli_args_for_plugin)
def run(app_context, *plugin_args: str): # app_context is the global AppContext from CapGateRunner
    """
    Main entry point for the Wi-Fi Crack Automation plugin.
    Manages the overall workflow from interface setup to cracking,
    and ensures proper cleanup of network states.
    """
    plugin_name = "wifi_crack_automation" # For clearer logging
    logger.info(f"[PLUGIN {plugin_name}] Starting execution...")
    
    # Reset plugin's local state context at the start of each run for isolation
    reset_plugin_local_context()

    # --- Populate plugin_local_context from global AppContext and plugin_args ---
    # This makes global settings and CLI args available to plugin phases via plugin_local_context
    plugin_local_context["app_context"] = app_context 
    plugin_local_context["mock_mode"] = app_context.get("mock_mode", False) 
    plugin_local_context["auto_select"] = app_context.get("auto_select", False)
    plugin_local_context["scan_duration_seconds"] = app_context.get("wifi_scan_duration", 15) 
    plugin_local_context["network_security_filter"] = app_context.get("wifi_security_filter", "WPA")

    # Example: If your plugin can take a target BSSID from the command line via CapGate
    # e.g., `capgate run wifi_crack_automation <target_bssid>`
    if plugin_args:
        plugin_local_context["target_bssid_cli_arg"] = plugin_args[0]
        logger.info(f"[PLUGIN {plugin_name}] Received target BSSID from CLI: {plugin_args[0]}")


    # --- Main plugin workflow with cleanup ---
    try:
        # Phase 1: Interface Selection and Monitor Mode
        if not select_interface(plugin_local_context): # select_interface updates plugin_local_context
            logger.error(f"[PLUGIN {plugin_name}] Halted: Interface Selection & Monitor Mode (Phase 1) failed.")
            return # Exit plugin execution if this critical phase fails

        monitor_interface = plugin_local_context.get("monitor_interface")
        if not monitor_interface: # Should be caught by select_interface returning False, but an extra safeguard
            logger.error(f"[PLUGIN {plugin_name}] Halted: Monitor interface not available after Phase 1.")
            return
        logger.info(f"[PLUGIN {plugin_name}] Phase 1 complete. Using monitor interface: {monitor_interface}")

        # Phase 2: Scan for Networks
        selected_target_network = scan_for_networks(plugin_local_context)
        if not selected_target_network:
            logger.error(f"[PLUGIN {plugin_name}] Halted: Network Scan (Phase 2) failed or no target selected.")
            return
        
        target_bssid = plugin_local_context.get("target_bssid")
        target_channel = plugin_local_context.get("target_channel")
        target_essid = plugin_local_context.get("target_essid")
        logger.info(f"[PLUGIN {plugin_name}] Phase 2 complete. Target: ESSID='{target_essid}', BSSID={target_bssid}, Channel={target_channel}")

        # Phase 3: Capture Handshake
        if not capture_handshake(plugin_local_context):
            logger.error(f"[PLUGIN {plugin_name}] Halted: Capture Handshake (Phase 3) failed.")
            return
        logger.info(f"[PLUGIN {plugin_name}] Phase 3 complete. Handshake capture attempted for BSSID: {target_bssid}.")

        # Phase 4: Crack Handshake
        crack_success = crack_handshake(plugin_local_context)
        logger.info(f"[PLUGIN {plugin_name}] Phase 4 complete. Cracking attempted.")

        logger.info(f"\n===== PLUGIN {plugin_name} SUMMARY =====")
        # Create a serializable summary, excluding the full AppContext object
        summary_for_print = {k: v for k, v in plugin_local_context.items() if k != "app_context"}
        try:
            print(json.dumps(summary_for_print, indent=4, default=str)) # default=str for non-serializable items
        except TypeError as e:
            logger.error(f"Could not serialize plugin context for summary: {e}")
            print(f"Raw plugin_local_context (potential serialization issue): {summary_for_print}")


        if crack_success:
            logger.info(f"\n[✓] SUCCESS: [PLUGIN {plugin_name}] Crack complete. Key found: {plugin_local_context.get('key_found')}")
        else:
            logger.error(f"\n[✘] FAILURE: [PLUGIN {plugin_name}] Crack unsuccessful or not attempted.")

    except Exception as e:
        logger.exception(f"[PLUGIN {plugin_name}] An unexpected error occurred during execution: {e}")
        # The 'finally' block will still execute for cleanup.

    finally:
        logger.info(f"[*] [PLUGIN {plugin_name}] Starting cleanup phase...")

        nm_was_set_unmanaged: bool = plugin_local_context.get("nm_was_set_unmanaged", False)
        original_physical_interface: Optional[str] = plugin_local_context.get("original_interface_for_nm")
        monitor_interface_name_final: Optional[str] = plugin_local_context.get("monitor_interface")

        # Restore NetworkManager management if it was changed by the script
        if nm_was_set_unmanaged and original_physical_interface:
            logger.info(f"Restoring NetworkManager management for {original_physical_interface}.")
            try:
                shelltools.run_command(f"nmcli dev set {original_physical_interface} managed yes", require_root=True)
                # Optional: bring it up / reconnect if needed, NetworkManager might do this automatically
                # shelltools.run_command(f"ip link set {original_physical_interface} up", require_root=True, check=False)
                # shelltools.run_command(f"nmcli dev connect {original_physical_interface}", require_root=True, check=False)
                logger.info(f"NetworkManager management for {original_physical_interface} should be restored.")
            except Exception as e_nm_restore:
                logger.error(f"Failed to restore NetworkManager management for {original_physical_interface}: {e_nm_restore}")
        
        # Stop the monitor interface if it was created by airmon-ng (and is different from the original)
        if monitor_interface_name_final and original_physical_interface and monitor_interface_name_final != original_physical_interface:
            # This condition suggests airmon-ng might have created a new interface (e.g., wlan0mon from wlan0)
            logger.info(f"Attempting to stop monitor interface {monitor_interface_name_final} (if distinct and created by airmon-ng).")
            try:
                # This command is most relevant if airmon-ng was used.
                # It might fail harmlessly if the interface was not an airmon-ng VIF or already down/gone.
                shelltools.run_command(f"airmon-ng stop {monitor_interface_name_final}", require_root=True, check=False)
            except Exception as e_stop_mon:
                logger.warning(f"Could not stop monitor interface {monitor_interface_name_final} with airmon-ng: {e_stop_mon}.")
        
        # As a general measure, ensure the original physical interface is up.
        # This is particularly important if 'ip link set <iface> down' was used and NM/airmon-ng didn't bring it up.
        if original_physical_interface:
             try:
                 logger.info(f"Ensuring original physical interface {original_physical_interface} is up.")
                 shelltools.run_command(f"ip link set {original_physical_interface} up", require_root=True, check=False)
             except Exception as e_link_up:
                 logger.warning(f"Failed to ensure link is up for {original_physical_interface}: {e_link_up}")

        logger.info(f"[*] [PLUGIN {plugin_name}] Execution and cleanup finished.")

# --- TEMPORARY DEBUGGING BLOCK ---
if __name__ == "__main__":
    import os
    import sys

    # Add the 'src' directory to sys.path so Python can find 'core' and 'plugins'
    # Adjust this path based on where you run the script from
    script_dir = os.path.dirname(os.path.abspath(__file__))
    capgate_src_dir = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..')) # Adjust '..' count as needed
    
    # The 'capgate/src' directory needs to be on the Python path
    # If your project root is 'capgate', then add 'capgate/src'
    # E.g., if you're in ~/dev/projects/capgate/src/plugins/wifi_crack_automation/
    # You want to add ~/dev/projects/capgate/src to sys.path
    if capgate_src_dir not in sys.path:
        sys.path.insert(0, capgate_src_dir)
    
    # Try to import necessary components now that sys.path is adjusted
    try:
        from core.context import AppContext  # If AppContext is a real class
        from helpers.shelltools import \
            is_root  # Assuming this is a utility function to check root privileges
    except ImportError as e:
        print(f"[CRITICAL] Could not import CapGate core components for standalone debugging: {e}")
        print("Please ensure your PYTHONPATH or sys.path setup is correct for the CapGate project structure.")
        sys.exit(1)

    # Mock AppContext for testing
    mock_app_context = MockAppContext(initial_values={
        "mock_mode": False,
        "auto_select": False,
        "wifi_scan_duration": 15,
        "wifi_security_filter": "WPA",
        "interfaces": ["wlan0", "wlan1"], # Provide some mock interfaces for select_interface
        # Add any other global settings your plugin expects from app_context
    })

    # You can simulate CLI arguments here if needed
    mock_plugin_args = [] 
    # mock_plugin_args = ["AA:BB:CC:DD:EE:FF"] # Example: passing a target BSSID

    # Check for root privileges before running the plugin logic
    if not is_root():
        print("[CRITICAL] This plugin requires root privileges. Please run this script with 'sudo'.")
        # Example of how you might instruct the user to run it:
        print(f"Example: sudo {sys.executable} {os.path.abspath(__file__)}")
        sys.exit(1)

    print("\n--- Running plugin's main function directly for debugging ---")
    run(mock_app_context, *mock_plugin_args)
    print("--- Debugging run complete ---")

# --- END OF TEMPORARY DEBUGGING BLOCK ---