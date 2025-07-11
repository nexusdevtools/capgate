# src/runner.py

import sys
import json
import ipaddress
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from base.logger import logger
from base.plugin_loader import PluginLoader
from base.state_management.state import get_state, AppState
from base.debug_tools import debug_var, dump_context, print_exception
from base.state_management.context import get_context, CapGateContext

from db.schemas.device import Device
from db.schemas.interface import Interface

from vision.scanners.device_scanner import scan_devices_from_arp_table_and_update_state
from vision.scanners.iface_scanner import scan_interfaces_and_update_state
from vision.scanners.arp_scan import arp_scan

# CRITICAL FIX: Import the explicit function from paths
from paths import ensure_directories_for_capgate_startup # <--- CRITICAL FIX

# The global call at the end of paths.py should be removed if runner is always the entry.
# If paths.py is imported by other modules first, it might run anyway.
# To ensure it runs ONLY when the CapGate app starts (via runner), it's best to remove
# the global ensure_directories() call in paths.py itself and let runner call it.


class CapGateRunner:
    """
    Central runner class responsible for initializing core systems,
    managing context, and executing plugins or workflows.
    """

    def __init__(self, cli_state: Optional[Dict[str, Any]] = None):
        # CRITICAL FIX: Explicitly ensure directories *before* any managers are initialized
        # This prevents issues where managers try to create subdirs before top-level dirs exist.
        ensure_directories_for_capgate_startup() 

        self.logger = logger
        self.cli_state = cli_state or {}

        self.context: CapGateContext = get_context()
        self.app_state: AppState = get_state() 

        self.plugin_loader = PluginLoader()
        
        self._initialize_core_state() 

    def _initialize_core_state(self):
        self.logger.info("Starting comprehensive core state initialization...")

        scan_interfaces_and_update_state(self.app_state) 
        
        num_interfaces = len(self.app_state.discovery_graph.get("interfaces", {}))
        self.logger.info(f"Initialized state with {num_interfaces} network interfaces.")

        scan_devices_from_arp_table_and_update_state(self.app_state) 

        interfaces_for_scan_data = self.app_state.get_discovery_graph().get("interfaces", {}).values()
        
        for iface_info_dict in interfaces_for_scan_data:
            if iface_info_dict.get("is_up") and iface_info_dict.get("ip_address"):
                interface_name = iface_info_dict.get("name")
                ip_with_cidr = iface_info_dict.get("ip_address") 

                if interface_name and ip_with_cidr:
                    try:
                        network_obj = ipaddress.ip_network(ip_with_cidr, strict=False)
                        target_range = str(network_obj)
                        
                        self.logger.info(f"Performing active ARP scan on {interface_name} for range {target_range}")
                        discovered_devices_raw = arp_scan(interface_name, target_range)

                        for dev_info_raw in discovered_devices_raw:
                            mac = dev_info_raw.get("mac")
                            ip = dev_info_raw.get("ip")
                            if mac and ip:
                                existing_dev_data = self.app_state.discovery_graph['devices'].get(mac, {})
                                merged_data: Dict[str, Any] = {**existing_dev_data, **{
                                    "mac": mac,
                                    "ip": ip,
                                    "hostname": dev_info_raw.get("hostname"),
                                    "vendor": None,
                                    "is_router": False,
                                    "last_seen": time.time(),
                                }}
                                
                                validated_dev_data = Device(**merged_data).to_dict()

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
        if name not in self.plugin_loader.plugins:
            self.logger.error(f"Plugin '{name}' not found.")
            return None

        plugin = self.plugin_loader.plugins[name]

        try:
            debug_var(name, "Plugin Name")
            debug_var(args, "Args")
            debug_var(kwargs, "Kwargs")
            dump_context(self.context) 

            self.logger.info(f"🚀 Executing plugin '{name}' with arguments {args} {kwargs}")
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
    ) -> List[Interface]:
        interfaces_data = self.app_state.get_discovery_graph().get("interfaces", {}).values()
        
        interfaces_list: List[Interface] = []
        for iface_data in interfaces_data:
            try:
                interfaces_list.append(Interface(**iface_data))
            except Exception as e:
                self.logger.error(f"Error converting interface data to Interface model: {iface_data} - {e}")
                continue

        debug_var(wireless_only, "wireless_only")
        debug_var(monitor_only, "monitor_only")
        debug_var(is_up_only, "is_up_only")
        debug_var([i.name for i in interfaces_list], "Available Interfaces Before Filtering (Names)") 

        filtered_interfaces = interfaces_list

        if wireless_only:
            filtered_interfaces = [i for i in filtered_interfaces if i.driver and i.mode != "ethernet"]
        if monitor_only:
            filtered_interfaces = [i for i in filtered_interfaces if i.supports_monitor]
        if is_up_only:
            filtered_interfaces = [i for i in filtered_interfaces if i.is_up]

        debug_var([i.name for i in filtered_interfaces], "Filtered Interfaces (Names)") 
        return filtered_interfaces

    def run(self, *args: Any, plugin_name: Optional[str] = None, **kwargs: Any):
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

    def load_discovery_json(self, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
        # ensure_directories() is now called by CapGateRunner.__init__()
        runner = CapGateRunner()
        runner.run(*sys.argv[1:])
    except Exception as e:
        logger.error("An error occurred: %s", e)
        sys.exit(1)