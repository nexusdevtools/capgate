# core/state_management/state.py
"""
state.py — Central Application State
Manages persistent, shared data across CapGate tools and plugins.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Union, Any
import json


class AppState:
    """
    Central application state store.

    Attributes:
        loaded_plugins (List[str]): Plugins registered by the system.
        discovery_graph (Optional[Dict]): Live or cached network map.
        user_config (Dict): User-defined configuration settings.
    """
    def __init__(self):
        self.loaded_plugins: List[str] = []
        self.discovery_graph: Optional[Dict[str, Any]] = None
        self.user_config: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Union[List[str], Optional[Dict[str, Any]], Dict[str, Any]]]:
        """Return the full state as a dictionary."""
        return {
            "loaded_plugins": self.loaded_plugins,
            "discovery_graph": self.discovery_graph,
            "user_config": self.user_config
        }

    def save_to_file(self, path: str):
        """Persist the current state to a JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4)

    def load_from_file(self, path: str):
        """Load saved state from a JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.loaded_plugins = data.get("loaded_plugins", [])
            self.discovery_graph = data.get("discovery_graph")
            self.user_config = data.get("user_config", {})


# Singleton accessor
_state_instance = AppState()

def get_state() -> AppState:
    """Returns the singleton AppState instance."""
    return _state_instance
