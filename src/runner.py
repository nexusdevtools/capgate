# capgate/core/runner.py — CapGate Execution Engine

import sys
import json
import ipaddress # Added for network parsing
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.logger import logger
from core.plugin_loader import PluginLoader
from core.interface_manager import InterfaceInfo # Keep for InterfaceInfo schema
from core.debug_tools import debug_var, dump_context, print_exception

# Updated context imports
from core.state_management.context import get_context # Only need get_context, as it's a singleton
from core.state_management.state import get_state, AppState # Need AppState and its getter

# Import your scanner functions
# Ensure these paths are correct relative to your project structure
from vision.scanners.device_scanner import scan_devices
from vision.scanners.iface_scan import scan_interfaces_and_update_state # Updated to use AppState
from vision.scanners.arp_scan import arp_scan
from vision.scanners.iface_scan import scan_interfaces_and_update_context

from paths import ensure_directories

ensure_directories()


class CapGateRunner:
    """
    Central runner class responsible for initializing core systems,
    managing context, and executing plugins or workflows.
    """

    def __init__(self, cli_state: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.cli_state = cli_state or {}

        # Get the singleton context instance
        self.context = get_context()
        # Get the singleton app state instance (which is already referenced by self.context.state)
        self.app_state = get_state() 

        self.plugin_loader = PluginLoader()
        # The InterfaceManager's role might be partly absorbed by scan_interfaces_and_update_context,
        # but keep it if it has other responsibilities.
        # If scan_interfaces_and_update_context is comprehensive, InterfaceManager might become redundant here.
        # For now, let's assume scan_interfaces_and_update_context is the primary interface scanner.
        # self.interface_manager = InterfaceManager() 
        
        self._initialize_core_state() # Renamed to reflect broader initialization

    def _initialize_core_state(self):
        """
        Orchestrates initial discovery scans to populate the AppState.discovery_graph.
        """
        self.logger.info("Starting comprehensive core state initialization...")

        # Initialize discovery_graph if it's None
        if self.app_state.discovery_graph is None:
            self.app_state.discovery_graph = {"interfaces": {}, "devices": {}}

        # --- Step 1: Discover and add interfaces to AppState.discovery_graph ---
        # The `scan_interfaces_and_update_context` needs to know it should update AppState directly
        # or the runner needs to pull the data from it and set it.
        # Let's modify `scan_interfaces_and_update_context` to accept an AppState object directly
        # or have it return the discovered interfaces, and the runner sets them.
        
        # Option A (Better): Modify scan_interfaces_and_update_context to take AppState
        # For this to work, you'd need to change `scan_interfaces_and_update_context(ctx: AppContext)`
        # to `scan_interfaces_and_update_state(app_state: AppState)`.
        # Assuming we can pass app_state directly to scanners now:
        scan_interfaces_and_update_state(self.app_state) # <--- Potential change needed in iface_scan.py
        
        # Option B (If scanners must only talk to CapGateContext):
        # Temp context for interfaces, then move to AppState
        # temp_iface_context = CapGateContext() # This would be if scanner can't take AppState directly
        # scan_interfaces_and_update_context(temp_iface_context)
        # self.app_state.discovery_graph['interfaces'] = temp_iface_context.get("interfaces", {})


        # Let's assume for now the scanner directly populates discovery_graph in AppState
        # after modification. So, the interfaces will be in self.app_state.discovery_graph['interfaces']

        num_interfaces = len(self.app_state.discovery_graph.get("interfaces", {}))
        self.logger.info(f"Initialized state with {num_interfaces} network interfaces.")

        # --- Step 2: Perform initial device discovery (ARP table for quick local view) ---
        # Similarly, `scan_devices_from_arp_table` should update AppState directly
        scan_devices_from_arp_table_and_update_state(self.app_state) # <--- Potential change needed in device_scan.py

        # --- Step 3: Perform active ARP scan on active interfaces (more comprehensive device discovery) ---
        interfaces_for_scan = self.app_state.discovery_graph.get("interfaces", {}).values()
        
        for iface_info_dict in interfaces_for_scan:
            # Reconstruct InterfaceInfo object from dict for property access if needed, or access dict keys
            # iface_obj = InterfaceInfo(**iface_info_dict) # If you want to use methods like .is_up
            
            if iface_info_dict.get("is_up") and iface_info_dict.get("ip_address"):
                interface_name = iface_info_dict.get("name")
                ip_with_cidr = iface_info_dict.get("ip_address") 

                if interface_name and ip_with_cidr:
                    try:
                        network_obj = ipaddress.ip_network(ip_with_cidr, strict=False)
                        target_range = str(network_obj)
                        
                        self.logger.info(f"Performing active ARP scan on {interface_name} for range {target_range}")
                        discovered_devices = arp_scan(interface_name, target_range)

                        for dev_info in discovered_devices:
                            mac = dev_info.get("mac")
                            ip = dev_info.get("ip")
                            if mac and ip:
                                # Add/Update device directly in app_state.discovery_graph['devices']
                                # This requires a new method in AppState or manual dict update
                                self.app_state.discovery_graph['devices'][mac] = {
                                    "mac": mac,
                                    "ip": ip,
                                    "hostname": dev_info.get("hostname"), # If arp_scan provides it
                                    "vendor": None, # TODO: Lookup
                                    "is_router": False, # Needs further checks
                                    "last_seen": time.time(), # Use time.time() from runner's scope if that's allowed
                                }
                                self.logger.info(f"Discovered via ARP scan: {mac} ({ip})")
                    except ValueError as ve:
                        self.logger.warning(f"Invalid IP address or network format for {interface_name}: {ip_with_cidr} - {ve}")
                    except Exception as e:
                        self.logger.error(f"Error during ARP scan on {interface_name}: {e}")
                else:
                    self.logger.debug(f"Skipping ARP scan for {interface_name}: not up or no IP.")
            else:
                self.logger.debug(f"Skipping ARP scan for {iface_info_dict.get('name')}: not up or no IP.")


        total_devices = len(self.app_state.discovery_graph.get("devices", {}))
        self.logger.info(f"Finished comprehensive core state initialization. Total devices found: {total_devices}.")


    def list_plugins(self):
        """
        Prints all available plugins and basic metadata.
        """
        plugins = self.plugin_loader.plugins
        if not plugins:
            self.logger.warning("No plugins available.")
            return

        self.logger.info("📦 Available Plugins:")
        for name, plugin in plugins.items():
            desc = plugin.metadata.get("description", "No description provided.")
            author = plugin.metadata.get("author", "Unknown")
            version = plugin.metadata.get("version", "0.0")
            self.logger.info(f" - {name} v{version} by {author}: {desc}")

    def run_plugin(self, name: str, *args: Any, **kwargs: Any):
        """
        Executes a plugin by name with context injection.
        The plugin will receive the CapGateContext, which in turn
        provides access to the shared AppState.
        """
        if name not in self.plugin_loader.plugins:
            self.logger.error(f"Plugin '{name}' not found.")
            return None

        plugin = self.plugin_loader.plugins[name]

        try:
            debug_var(name, "Plugin Name")
            debug_var(args, "Args")
            debug_var(kwargs, "Kwargs")
            # Dump the current state of the context (which includes a reference to AppState)
            dump_context(self.context) 

            self.logger.info(f"🚀 Executing plugin '{name}' with arguments {args} {kwargs}")
            # Pass the CapGateContext to the plugin's run method
            return plugin.module.run(self.context, *args, **kwargs)
        except Exception as e:
            print_exception(e)
            self.logger.error(f"❌ Plugin '{name}' execution failed: {e}")
            return

    def get_interfaces(
        self,
        wireless_only: bool = False,
        monitor_only: bool = False,
        is_up_only: bool = False
    ) -> List[InterfaceInfo]:
        """
        Filter and return network interfaces from AppState.discovery_graph.
        """
        # Retrieve interfaces from the AppState's discovery_graph
        interfaces_data = self.app_state.discovery_graph.get("interfaces", {}).values()
        
        # Convert the dictionary data back into InterfaceInfo objects for consistent filtering
        interfaces_list: List[InterfaceInfo] = []
        for iface_data in interfaces_data:
            try:
                # Assuming InterfaceInfo constructor can take the dictionary directly
                interfaces_list.append(InterfaceInfo(**iface_data))
            except TypeError as te:
                self.logger.error(f"Error converting interface data to InterfaceInfo: {iface_data} - {te}")
                continue


        debug_var(wireless_only, "wireless_only")
        debug_var(monitor_only, "monitor_only")
        debug_var(is_up_only, "is_up_only")
        debug_var([i.name for i in interfaces_list], "Available Interfaces Before Filtering (Names)") # Log names for readability

        filtered_interfaces = interfaces_list

        if wireless_only:
            filtered_interfaces = [i for i in filtered_interfaces if i.is_wireless]
        if monitor_only:
            filtered_interfaces = [i for i in filtered_interfaces if i.supports_monitor_mode()]
        if is_up_only:
            filtered_interfaces = [i for i in filtered_interfaces if i.is_up]

        debug_var([i.name for i in filtered_interfaces], "Filtered Interfaces (Names)") # Log names for readability
        return filtered_interfaces

    def run(self, *args: Any, plugin_name: Optional[str] = None, **kwargs: Any):
        """
        Entry point to execute a plugin or display plugin list.
        """
        self.logger.info("🚀 CapGate Runner Initialized")

        if plugin_name:
            self.logger.info(f"➡️ Attempting to run plugin: {plugin_name}")
            self.run_plugin(plugin_name, *args, **kwargs)
        else:
            self.logger.info("No plugin specified. Listing available plugins...\n")
            self.list_plugins()
            self.logger.info("Use 'capgate run <plugin_name>' to execute a specific plugin.")

        self.logger.info("🛑 CapGate Runner Finished")
        return False

    def load_discovery_json(self, path: Optional[str] = None):
        """
        Load topology data from discovery.json (default or custom path)
        directly into AppState.discovery_graph.
        """
        default_paths = [
            Path("data/topology/discovery.json"),
            Path("capgate/data/topology/discovery.json"),
            Path("src/data/topology/discovery.json"),
            Path("/home/nexus/capgate/data/topology/discovery.json"),
        ]
        loaded_data = {}
        if path:
            p = Path(path)
            if p.exists():
                with p.open("r") as f:
                    loaded_data = json.load(f)
            else:
                self.logger.error(f"Discovery file not found: {path}")
        else:
            for p in default_paths:
                if p.exists():
                    with p.open("r", encoding="utf-8") as f: # Added encoding
                        loaded_data = json.load(f)
                        self.logger.info(f"Loaded discovery.json from: {p}")
                        break
            if not loaded_data:
                self.logger.error("No discovery.json found in default locations.")
        
        if loaded_data:
            # Assuming discovery.json contains "interfaces" and "devices" directly
            self.app_state.discovery_graph['interfaces'].update(loaded_data.get("interfaces", {}))
            self.app_state.discovery_graph['devices'].update(loaded_data.get("devices", {}))
            self.logger.info(f"Successfully loaded {len(loaded_data.get('interfaces', {}))} interfaces and {len(loaded_data.get('devices', {}))} devices from JSON.")
        
        # Return the loaded data if needed, or simply update state.
        return loaded_data


def main():
    """
    Main script entry point for command-line use.
    """
    try:
        ensure_directories()
        runner = CapGateRunner()
        runner.run(*sys.argv[1:])
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)
