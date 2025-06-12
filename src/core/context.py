"""
context.py — Central context object for CapGate
Provides a shared space to store configuration, state, and service references.
Accessible by plugins and core components alike.

✅ Highlights:

    - Thread-safe singleton pattern (_lock) ensures only one instance exists.
    - Acts like a global store without using actual global variables.
    - Automatically detects and stores available interfaces on initialization.
    - All core components and plugins can import and modify shared state like this:

        from capgate.core.context import AppContext

        ctx = AppContext()
        ctx.set("interfaces", ["wlan0", "wlan1"])
"""

from threading import Lock
from typing import Any, Dict, Optional  # <-- you were missing Optional before!

from core.interface_manager import InterfaceManager
from core.logger import logger


class AppContext:
    """
    Singleton-style context manager for the application.
    Allows safe sharing of global state (e.g. loaded config, interfaces, etc.).
    """

    _instance: Optional["AppContext"] = None
    _lock = Lock()
    _store: Dict[str, Any]  # <-- Add this line

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._store = {}
                cls._instance._init_context()
                logger.debug("🔧 Initialized new AppContext instance")
        return cls._instance

    def _init_context(self):
        interface_manager = InterfaceManager()
        self.interfaces = interface_manager.get_interfaces()
        logger.info(
            f"Initialized context with {len(self.interfaces)} network interfaces."
        )
        self.set("interfaces", self.interfaces)

    def set(self, key: str, value: Any):
        logger.debug(f"📥 Setting context key: '{key}'")
        self._store[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        value = self._store.get(key, default)
        logger.debug(f"📤 Retrieved context key: '{key}' -> {value!r}")
        return value

    def has(self, key: str) -> bool:
        exists = key in self._store
        logger.debug(f"🔎 Context has key '{key}': {exists}")
        return exists

    def remove(self, key: str):
        if key in self._store:
            logger.debug(f"🧹 Removing context key: '{key}'")
            del self._store[key]

    def clear(self):
        logger.warning("⚠️ Clearing entire AppContext store")
        self._store.clear()

    def as_dict(self) -> Dict[str, Any]:
        logger.debug("📋 Exporting context as dict")
        return dict(self._store)
