import importlib
import json
import traceback
from pathlib import Path
from types import ModuleType
from typing import Dict, Any, List, Optional

from base.logger import get_logger
my_logger = get_logger("my_submodule")



class Plugin:
    """
    Represents a loaded plugin with its metadata and logic.
    """
    def __init__(self, name: str, module: ModuleType, metadata: Dict[str, Any]):
        self.name = name
        self.module = module
        self.metadata = metadata

    def run(self, *args: Any, **kwargs: Any):
        """
        Delegates execution to the plugin's main.run()
        """
        if hasattr(self.module, "run"):
            return self.module.run(*args, **kwargs)
        else:
            raise AttributeError(f"Plugin '{self.name}' is missing a `run()` function.")


class PluginLoader:
    """
    Dynamically loads plugins from the plugins directory.
    Each plugin must have:
        - A metadata.json file with required fields
        - A main.py file with a `run()` function
    """

    def __init__(self, plugin_dir: str = "src/plugins"):
        self.plugin_dir = Path(plugin_dir).resolve()
        self.plugins: Dict[str, Plugin] = {}
        self._discover_plugins()

    def _discover_plugins(self):
        """
        Discover and import all valid plugin modules.
        """
        my_logger.info(f"🔍 Scanning for plugins in {self.plugin_dir}")
        for plugin_path in self.plugin_dir.iterdir():
            if not plugin_path.is_dir() or plugin_path.name.startswith("__"):
                continue

            try:
                metadata_file = plugin_path / "metadata.json"
                main_file = plugin_path / "main.py"

                if not metadata_file.exists() or not main_file.exists():
                    my_logger.warning(f"⚠️ Skipping {plugin_path.name}: missing metadata or main.py")
                    continue

                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                module_name = f"plugins.{plugin_path.name}.main"
                module = importlib.import_module(module_name)

                plugin = Plugin(
                    name=plugin_path.name,
                    module=module,
                    metadata=metadata
                )

                self.plugins[plugin_path.name] = plugin
                my_logger.info(f"✅ Loaded plugin: {plugin_path.name}")

            except Exception as e:
                my_logger.error(f"❌ Failed to load plugin '{plugin_path.name}': {e}")
                my_logger.debug(traceback.format_exc())

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """
        Retrieve a plugin by its folder name.
        """
        return self.plugins.get(name)

    def list_plugins(self) -> List[str]:
        """
        Return a list of available plugin names.
        """
        return list(self.plugins.keys())

    def run_plugin(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Run a specific plugin by name.
        """
        plugin = self.get_plugin(name)
        if plugin:
            my_logger.info(f"🚀 Running plugin '{name}'")
            return plugin.run(*args, **kwargs)
        else:
            my_logger.warning(f"⚠️ Plugin '{name}' not found.")
            return None
