import sys
from typing import Optional, List

from core.logger import logger
from core.plugin_loader import PluginLoader
from core.context import AppContext
from core.interface_manager import InterfaceManager

from paths import ensure_directories
ensure_directories()


class CapGateRunner:
    """
    Central runner class responsible for initializing core systems,
    managing context, and executing plugins or workflows.
    """

    def __init__(self, context: Optional[AppContext] = None):
        self.context = context or AppContext()
        self.plugin_loader = PluginLoader()
        self.interface_manager = InterfaceManager()
        self.logger = logger
        self._initialize_context()

    def _initialize_context(self):
        """
        Initialize the application context with interfaces and other necessary data.
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

    def run_plugin(self, name: str, *args, **kwargs):
        if name not in self.plugin_loader.plugins:
            self.logger.error(f"Plugin '{name}' not found.")
            return None

        plugin = self.plugin_loader.plugins[name]
        try:
            self.logger.info(f"Executing plugin '{name}' with arguments {args} {kwargs}")
            return plugin.module.run(self.context, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Plugin '{name}' execution failed: {e}")
            return None
    
    def get_interfaces(self, wireless_only: bool = False, monitor_only: bool = False) -> List[str]:
        """
        Return filtered list of interfaces based on flags.
        """
        interfaces = self.context.get("interfaces", [])
        if wireless_only:
            interfaces = [iface for iface in interfaces if iface.is_wireless]
        if monitor_only:
            interfaces = [iface for iface in interfaces if iface.supports_monitor]
        return [iface.name for iface in interfaces]

    def run(self, plugin_name: Optional[str] = None, *args, **kwargs):
        """
        Entrypoint for the runner. Executes default flow or a plugin.
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
        # Note: In a real-world scenario, you might want to handle the exit more gracefully.
        # For example, you might want to clean up resources or log the exit status.
        # return False is a hard exit and should be used with caution.
        # In this case, it's used to indicate that the script has finished executing.
        # You might want to consider using a more graceful shutdown process in a production environment.
        # For example, you could use a signal handler to catch termination signals and clean up before exiting.
        # This would allow you to close any open files, release resources, or perform any other necessary cleanup.
        # However, for the sake of simplicity and clarity in this example, we're using return False.