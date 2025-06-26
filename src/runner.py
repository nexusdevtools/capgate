# capgate/core/runner.py — CapGate Execution Engine

import sys
import json
import ipaddress
import time # Added for last_seen timestamp
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.logger import logger
from core.plugin_loader import PluginLoader
# Import the Interface Pydantic schema directly, as it's the new data model
from db.schemas.interface import Interface # <--- CRITICAL CHANGE: Changed from InterfaceInfo
from db.schemas.device import Device  # <-- Add this import for Device schema

from core.debug_tools import debug_var, dump_context, print_exception

# Updated context imports
from core.state_management.context import get_context, CapGateContext
from core.state_management.state import get_state, AppState # Correct AppState import

# Import your scanner functions (ensure correct paths based on your tree)
from vision.scanners.device_scanner import scan_devices_from_arp_table_and_update_state # Renamed as per discussion
from vision.scanners.iface_scanner import scan_interfaces_and_update_state # Renamed as per discussion
from vision.scanners.arp_scan import arp_scan # Utility function, returns dicts, doesn't update state directly

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
        self.context: CapGateContext = get_context()
        # Get the singleton app state instance (which is already referenced by self.context.state)
        self.app_state: AppState = get_state() 

        self.plugin_loader = PluginLoader()
        # InterfaceManager's role is now primarily as an accessor to AppState
        # and a trigger for rescanning, not to manage its own list of interfaces.
        # It's better to instantiate it only if explicitly needed for its methods.
        # Or remove it from __init__ if its refresh method is triggered directly.
        # For now, let's keep it minimal, assuming core setup is handled by scanners directly.
        # self.interface_manager = InterfaceManager() 
        
        self._initialize_core_state() # Renamed to reflect broader initialization

    def _initialize_core_state(self):
        """
        Orchestrates initial discovery scans to populate the AppState.discovery_graph.
        """
        self.logger.info("Starting comprehensive core state initialization...")

        # Initialize discovery_graph if it's None in AppState (AppState __init__ now handles this)
        # if self.app_state.discovery_graph is None:
        #     self.app_state.discovery_graph = {"interfaces": {}, "devices": {}}

        # --- Step 1: Discover and add interfaces to AppState.discovery_graph ---
        # `scan_interfaces_and_update_state` now directly updates `self.app_state.discovery_graph['interfaces']`
        scan_interfaces_and_update_state(self.app_state) 
        
        num_interfaces = len(self.app_state.discovery_graph.get("interfaces", {}))
        self.logger.info(f"Initialized state with {num_interfaces} network interfaces.")

        # --- Step 2: Perform initial device discovery (ARP table for quick local view) ---
        # `scan_devices_from_arp_table_and_update_state` now directly updates `self.app_state.discovery_graph['devices']`
        scan_devices_from_arp_table_and_update_state(self.app_state) 

        # --- Step 3: Perform active ARP scan on active interfaces (more comprehensive device discovery) ---
        # Retrieve interfaces from the app_state's discovery_graph (which are dicts at this point)
        interfaces_for_scan_data = self.app_state.discovery_graph.get("interfaces", {}).values()
        
        for iface_info_dict in interfaces_for_scan_data:
            # Check if interface is up and has an IP address to perform ARP scan
            if iface_info_dict.get("is_up") and iface_info_dict.get("ip_address"):
                interface_name = iface_info_dict.get("name")
                ip_with_cidr = iface_info_dict.get("ip_address") 

                if interface_name and ip_with_cidr:
                    try:
                        # Use ipaddress to get the network range from CIDR
                        network_obj = ipaddress.ip_network(ip_with_cidr, strict=False)
                        target_range = str(network_obj)
                        
                        self.logger.info(f"Performing active ARP scan on {interface_name} for range {target_range}")
                        # arp_scan is a utility, it returns raw device dictionaries
                        discovered_devices_raw = arp_scan(interface_name, target_range)

                        for dev_info_raw in discovered_devices_raw:
                            mac = dev_info_raw.get("mac")
                            ip = dev_info_raw.get("ip")
                            if mac and ip:
                                # Prepare device data for update
                                # It's good practice to create the Pydantic model for validation
                                # then convert to dict for storage.
                                # Merge with existing data if device already partially exists to retain info.
                                existing_dev_data = self.app_state.discovery_graph['devices'].get(mac, {})
                                
                                # Create a temporary Pydantic model to merge and validate new data
                                # If existing_dev_data contains all fields, pass it first, then overwrite with new.
                                merged_data: Dict[str, Any] = {**existing_dev_data, **{
                                    "mac": mac,
                                    "ip": ip,
                                    "hostname": dev_info_raw.get("hostname"), # If arp_scan provides it
                                    "vendor": None, # Needs external lookup
                                    "is_router": False, # Needs further checks
                                    "last_seen": time.time(), # Timestamp when this device was actively seen
                                }}
                                
                                # Validate with Device schema and convert to dictionary
                                validated_dev_data = Device(**merged_data).to_dict()

                                # Update the global AppState with the device data
                                self.app_state.update_devices({mac: validated_dev_data})
                                self.logger.info(f"Discovered via ARP scan: {mac} ({ip})")
                    except ValueError as ve:
                        self.logger.warning(f"Invalid IP address or network format for {interface_name}: {ip_with_cidr} - {ve}")
                    except Exception as e:
                        self.logger.error(f"Error during ARP scan on {interface_name}: {e}")
                else:
                    self.logger.debug(f"Skipping ARP scan for {iface_info_dict.get('name')}: name or IP missing.")
            else:
                self.logger.debug(f"Skipping ARP scan for {iface_info_dict.get('name')}: interface not up or no IP address configured.")


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
    ) -> List[Interface]: # <--- CRITICAL CHANGE: Return type is now List[Interface]
        """
        Filter and return network interfaces from AppState.discovery_graph.
        """
        # Retrieve interfaces data from the AppState's discovery_graph
        interfaces_data = self.app_state.discovery_graph.get("interfaces", {}).values()
        
        # Convert the dictionary data back into Pydantic Interface objects for consistent filtering
        interfaces_list: List[Interface] = []
        for iface_data in interfaces_data:
            try:
                interfaces_list.append(Interface(**iface_data))
            except Exception as e: # Catch generic Exception for parsing issues
                self.logger.error(f"Error converting interface data to Interface model: {iface_data} - {e}")
                continue

        debug_var(wireless_only, "wireless_only")
        debug_var(monitor_only, "monitor_only")
        debug_var(is_up_only, "is_up_only")
        debug_var([i.name for i in interfaces_list], "Available Interfaces Before Filtering (Names)") 

        filtered_interfaces = interfaces_list

        if wireless_only:
            # Use attributes from the Interface Pydantic model
            filtered_interfaces = [i for i in filtered_interfaces if i.driver and i.mode != "ethernet"] # Check for driver and not "ethernet" mode
        if monitor_only:
            filtered_interfaces = [i for i in filtered_interfaces if i.supports_monitor] # Direct access to supports_monitor
        if is_up_only:
            filtered_interfaces = [i for i in filtered_interfaces if i.is_up] # Direct access to is_up

        debug_var([i.name for i in filtered_interfaces], "Filtered Interfaces (Names)") 
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

    def load_discovery_json(self, path: Optional[str] = None) -> Optional[dict[str, Any]]:
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
        loaded_data: Dict[str, Any] = {}
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
                    with p.open("r", encoding="utf-8") as f: 
                        loaded_data = json.load(f)
                        self.logger.info(f"Loaded discovery.json from: {p}")
                        break
            if not loaded_data:
                self.logger.error("No discovery.json found in default locations.")
        
        if loaded_data:
            # The AppState.__init__ guarantees discovery_graph is initialized
            
            # Update the interfaces and devices within discovery_graph
            # Use AppState's update methods for thread-safety and internal consistency
            self.app_state.update_interfaces(loaded_data.get("interfaces", {}))
            self.app_state.update_devices(loaded_data.get("devices", {}))
            
            self.logger.info(
                "Successfully loaded %d interfaces and %d devices from JSON into AppState.",
                len(self.app_state.discovery_graph.get('interfaces', {})),
                len(self.app_state.discovery_graph.get('devices', {}))
            )
        
        return loaded_data


def main():
    """
    Main script entry point for command-line use.
    """
    try:
        ensure_directories()
        runner = CapGateRunner()
        # Uncomment the line below if you want to automatically load
        # a default discovery.json at startup.
        # runner.load_discovery_json() 
        runner.run(*sys.argv[1:])
    except Exception as e:
        logger.error("An error occurred: %s", e)
        sys.exit(1)
