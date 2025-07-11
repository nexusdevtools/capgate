# src/core/state_management/state.py
"""
state.py — Central Application State
Manages persistent, shared data across CapGate tools and plugins.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Union, Any
import json
from threading import RLock

class AppState:
    """
    Central application state store.
    All access to its attributes should ideally be via helper methods for thread-safety.

    Attributes:
        loaded_plugins (List[str]): Plugins registered by the system.
        discovery_graph (Dict[str, Any]): Live or cached network map ({'interfaces': {}, 'devices': {}}).
        user_config (Dict): User-defined configuration settings.
    """
    def __init__(self):
        self.loaded_plugins: List[str] = []
        # Initialize discovery_graph as an empty dict with required keys if it's meant to always exist
        # This ensures it's never None once AppState is created.
        self.discovery_graph: Dict[str, Any] = {"interfaces": {}, "devices": {}}
        self.user_config: Dict[str, Any] = {}
        self._lock: RLock = RLock() # Lock for AppState's attributes

    # --- Thread-safe attribute access methods for clarity and safety ---

    def get_loaded_plugins(self) -> List[str]:
        """Returns a copy of the list of loaded plugins."""
        with self._lock:
            return list(self.loaded_plugins)

    def set_loaded_plugins(self, plugins: List[str]) -> None:
        """Sets the list of loaded plugins."""
        with self._lock:
            self.loaded_plugins = plugins

    def get_discovery_graph(self) -> Dict[str, Any]:
        """Returns the discovery_graph, ensuring it's initialized."""
        with self._lock:
            # Already initialized in __init__, so just return it.
            return self.discovery_graph # Return reference, as updates will be done on sub-dicts

    def update_interfaces(self, interfaces_data: Dict[str, Any]) -> None:
        """Updates the interfaces within the discovery_graph."""
        with self._lock:
            self.discovery_graph['interfaces'].update(interfaces_data)

    def update_devices(self, devices_data: Dict[str, Any]) -> None:
        """Updates the devices within the discovery_graph."""
        with self._lock:
            self.discovery_graph['devices'].update(devices_data)

    def get_user_config(self) -> Dict[str, Any]:
        """Returns a copy of the user configuration."""
        with self._lock:
            return dict(self.user_config)

    def set_user_config(self, config: Dict[str, Any]) -> None:
        """Sets the user configuration."""
        with self._lock:
            self.user_config = config

    # --- Persistence methods ---
    def to_dict(self) -> Dict[str, Union[List[str], Dict[str, Any]]]:
        """Return the full state as a dictionary."""
        with self._lock: # Ensure thread-safe read for export
            return {
                "loaded_plugins": list(self.loaded_plugins),
                # Ensure discovery_graph is a dict for consistency, even if it was None.
                "discovery_graph": dict(self.discovery_graph) if self.discovery_graph else {"interfaces": {}, "devices": {}},
                "user_config": dict(self.user_config)
            }

    def save_to_file(self, path: str):
        """Persist the current state to a JSON file."""
        with self._lock: # Ensure thread-safe write
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.to_dict(), f, indent=4)
            except IOError as e:
                # Using print here, consider integrating with your logger if it's available globally or passed
                print(f"Error saving state to file {path}: {e}") 

    def load_from_file(self, path: str):
        """Load saved state from a JSON file."""
        with self._lock: # Ensure thread-safe load
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.loaded_plugins = data.get("loaded_plugins", [])
                    
                    loaded_dg = data.get("discovery_graph")
                    if loaded_dg is not None:
                        # Ensure loaded_dg keys exist or provide defaults
                        self.discovery_graph = {
                            "interfaces": loaded_dg.get("interfaces", {}),
                            "devices": loaded_dg.get("devices", {})
                        }
                    else:
                        self.discovery_graph = {"interfaces": {}, "devices": {}} # Default empty
                    self.user_config = data.get("user_config", {})
            except FileNotFoundError:
                print(f"State file not found: {path}. Starting with default state.")
                self.loaded_plugins = []
                self.discovery_graph = {"interfaces": {}, "devices": {}}
                self.user_config = {}
            except json.JSONDecodeError as e:
                print(f"Error decoding state file {path}: {e}. Starting with default state.")
                self.loaded_plugins = []
                self.discovery_graph = {"interfaces": {}, "devices": {}}
                self.user_config = {}
            except IOError as e:
                print(f"Error loading state from file {path}: {e}. Starting with default state.")
                self.loaded_plugins = []
                self.discovery_graph = {"interfaces": {}, "devices": {}}
                self.user_config = {}


# Singleton accessor
_state_instance: Optional[AppState] = None # Explicitly type as Optional

def get_state() -> AppState:
    """Returns the singleton AppState instance."""
    global _state_instance
    if _state_instance is None:
        _state_instance = AppState()
    return _state_instance