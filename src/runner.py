# runner.py

import sys
from typing import Optional, Dict, Any, List
import json
from pathlib import Path

from core.debug_tools import debug_var
from core.debug_tools import dump_context, print_exception
from core.logger import logger
from core.plugin_loader import PluginLoader
from core.context import AppContext
from core.interface_manager import InterfaceManager, InterfaceInfo
from paths import ensure_directories

ensure_directories()


class CapGateRunner:
    """
    Central runner class responsible for initializing core systems,
    managing context, and executing plugins or workflows.
    """

    def __init__(self, context: Optional[AppContext] = None, cli_state: Optional[Dict[str, Any]] = None):
        self.context = context or AppContext()
        self.plugin_loader = PluginLoader()
        self.interface_manager = InterfaceManager()
        self.logger = logger
        self.cli_state = cli_state or {}
        self._initialize_context()

    def _initialize_context(self):
        """
        Initialize the application context with all available interfaces.
        """
        interfaces = self.interface_manager.get_interfaces()
        self.context.set("interfaces", interfaces)
        self.logger.info(f"Initialized context with {len(interfaces)} network interfaces.")

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
        Executes a given plugin by name, passing context and arguments.
        """
        if name not in self.plugin_loader.plugins:
            self.logger.error(f"Plugin '{name}' not found.")
            return None

        plugin = self.plugin_loader.plugins[name]
        try:
            debug_var(name, "Plugin Name")
            debug_var(args, "Args")
            debug_var(kwargs, "Kwargs")
            dump_context(self.context)

            self.logger.info(f"Executing plugin '{name}' with arguments {args} {kwargs}")
            return plugin.module.run(self.context, *args, **kwargs)
        except Exception as e:
            print_exception(e)
            self.logger.error(f"Plugin '{name}' execution failed: {e}")
            return

    def get_interfaces(
        self,
        wireless_only: bool = False,
        monitor_only: bool = False,
        is_up_only: bool = False
    ) -> List[InterfaceInfo]:
        """
        Return a filtered list of InterfaceInfo objects.
        """
        interfaces: List[InterfaceInfo] = self.context.get("interfaces", [])
        debug_var(wireless_only, "wireless_only")
        debug_var(monitor_only, "monitor_only")
        debug_var(is_up_only, "is_up_only")
        debug_var(interfaces, "Available Interfaces Before Filtering")

        if wireless_only:
            interfaces = [iface for iface in interfaces if iface.is_wireless]
        if monitor_only:
            interfaces = [iface for iface in interfaces if iface.supports_monitor_mode()]
        if is_up_only:
            interfaces = [iface for iface in interfaces if iface.is_up]

        debug_var(interfaces, "Filtered Interfaces")
        return interfaces

    def run(self, *args: Any, plugin_name: Optional[str] = None, **kwargs: Any):
        """
        Entrypoint to execute a plugin or default flow.
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
    
    def load_discovery(self, path: str = None) -> dict:
        """
        Load discovery JSON topology data.
        Falls back to default paths if path not specified.
        """
        default_paths = [
            Path("data/topology/discovery.json"),
            Path("capgate/data/topology/discovery.json"),
            Path("src/data/topology/discovery.json"),
            Path("/home/nexus/capgate/data/topology/discovery.json"),
        ]
        if path:
            p = Path(path)
            if p.exists():
                with p.open("r") as f:
                    return json.load(f)
            else:
                self.logger.error(f"Discovery file not found: {path}")
                return {}
        else:
            for p in default_paths:
                if p.exists():
                    with p.open("r") as f:
                        return json.load(f)
            self.logger.error("No discovery.json found in default locations.")
            return {}

def main():
    """
    Main entrypoint for the CapGate Runner.
    Initializes the runner and processes command line arguments.
    """
    try:
        ensure_directories()
        runner = CapGateRunner()
        runner.run(*sys.argv[1:])
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)
