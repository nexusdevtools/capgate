# capgate/core/context.py — Central context object for CapGate
"""
Central shared context object for CapGate.

✅ Highlights:
- Thread-safe Singleton pattern ensures only one instance.
- Stores interfaces, devices, credentials, plugin state, and event log.
- Can be updated directly or through `.update()` method.
- Compatible with all plugins and core modules.

Usage:
    from core.context import AppContext

    ctx = AppContext()
    ctx.update("device", "AA:BB:CC:DD:EE:FF", device.model_dump())
    ctx.get("interfaces")
"""

from threading import Lock
from typing import Any, Dict, Optional, List
import time

from capgate_types.db.schemas.device_types import DeviceSchema
from capgate_types.core.context_types import (
    InterfaceData,
    CredentialData,
    MetadataEntry,
    EventLogEntry,
)
from core.interface_manager import InterfaceManager
from core.logger import logger


class AppContext:
    _instance: Optional["AppContext"] = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_context()
                logger.debug("🔧 Created AppContext singleton instance.")
        return cls._instance

    def _init_context(self):
        # Private backing store (free-form)
        self._store: Dict[str, Any] = {}

        # Core structured components
        self.interfaces: Dict[str, InterfaceData] = {}
        self.devices: Dict[str, DeviceSchema] = {}
        self.credentials: Dict[str, CredentialData] = {}
        self.metadata: Dict[str, MetadataEntry] = {}
        self.event_log: List[EventLogEntry] = []

        # Initialize and preload detected interfaces
        interface_manager = InterfaceManager()
        self.interfaces = {
            iface.name: iface.__dict__ for iface in interface_manager.get_interfaces()
        }
        self.set("interfaces", self.interfaces)
        logger.info(f"Initialized context with {len(self.interfaces)} network interfaces.")

    # -- Core KV Store ----------------------------

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
        logger.warning("⚠️ Clearing entire AppContext store and subsystems.")
        self._store.clear()
        self.interfaces.clear()
        self.devices.clear()
        self.credentials.clear()
        self.metadata.clear()
        self.event_log.clear()

    # -- Unified Update Interface ----------------------------

    def update(self, category: str, item_id: str, data: dict):
        """
        Injects structured data into a context category.

        Args:
            category (str): One of 'interface', 'device', 'credential', 'meta'
            item_id (str): Unique key (e.g. MAC address, iface name)
            data (dict): Structured value, e.g. `device.model_dump()`
        """
        if category == "interface":
            self.interfaces[item_id] = data
        elif category == "device":
            self.devices[item_id] = data
        elif category == "credential":
            self.credentials[item_id] = data
        elif category == "meta":
            self.metadata[item_id] = data
        else:
            logger.warning(f"⚠️ Unknown update category: '{category}'")
            return

        self._log_event(category, item_id, data)

    # -- Event Logging ----------------------------

    def _log_event(self, type: str, id: str, data: dict):
        event: EventLogEntry = {
            "timestamp": time.time(),
            "type": type,
            "id": id,
            "data": data,
        }
        self.event_log.append(event)
        logger.debug(f"🧠 Logged event: {type} ({id})")

    # -- Export ------------------------------------

    def as_dict(self) -> Dict[str, Any]:
        """
        Return a full snapshot of the current context as a serializable dict.
        Useful for debugging, export, or state dumping.
        """
        logger.debug("📋 Exporting AppContext as dictionary.")
        return {
            "interfaces": self.interfaces,
            "devices": self.devices,
            "credentials": self.credentials,
            "metadata": self.metadata,
            "store": dict(self._store),
            "event_log": list(self.event_log),
        }
    def __repr__(self):
        return f"<AppContext: {len(self.interfaces)} interfaces, {len(self.devices)} devices, {len(self.credentials)} credentials, {len(self.metadata)} metadata entries>"
    def __str__(self):
        return f"AppContext with {len(self.interfaces)} interfaces, {len(self.devices)} devices, {len(self.credentials)} credentials, {len(self.metadata)} metadata entries, and {len(self.event_log)} events logged."
    def __len__(self):
        return len(self._store)
    def __contains__(self, key: str) -> bool:
        return key in self._store
