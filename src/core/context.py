# capgate/core/context.py — Central context object for CapGate
# Provides a shared space to store configuration, state, and service references.
# Accessible by plugins and core components alike.

"""
✅ Highlights:

    - Thread-safe singleton pattern (_lock) ensures only one instance exists.
    - Global knowledge store for interfaces, devices, credentials, plugin state.
    - Continuous event log for historical intelligence and ML training.
    - Fully extensible and schema-compatible.
    - Usage:

        from core.context import AppContext

        ctx = AppContext()
        ctx.update("interface", "wlan0", iface_obj.dict())
        ctx.devices["AA:BB:CC:DD:EE:FF"] = device_obj
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
                logger.debug("🔧 Initialized new AppContext instance")
        return cls._instance

    def _init_context(self):
        self._store: Dict[str, Any] = {}
        self.interfaces: Dict[str, InterfaceData] = {}
        self.devices: Dict[str, DeviceSchema] = {}
        self.credentials: Dict[str, CredentialData] = {}
        self.metadata: Dict[str, MetadataEntry] = {}
        self.event_log: List[EventLogEntry] = []

        interface_manager = InterfaceManager()
        self.interfaces = interface_manager.get_interfaces()
        self.set("interfaces", self.interfaces)
        logger.info(f"Initialized context with {len(self.interfaces)} network interfaces.")

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
        self.interfaces.clear()
        self.devices.clear()
        self.credentials.clear()
        self.metadata.clear()
        self.event_log.clear()

    def update(self, type: str, id: str, data: dict):
        if type == "interface":
            self.interfaces[id] = data
        elif type == "device":
            self.devices[id] = data
        elif type == "credential":
            self.credentials[id] = data
        elif type == "meta":
            self.metadata[id] = data
        else:
            logger.warning(f"Unknown update type: {type}")

        self._log_event(type, id, data)

    def _log_event(self, type: str, id: str, data: dict):
        event: EventLogEntry = {
            "timestamp": time.time(),
            "type": type,
            "id": id,
            "data": data,
        }
        self.event_log.append(event)
        logger.debug(f"🧠 Logged event: {type} ({id})")

    def as_dict(self) -> Dict[str, Any]:
        logger.debug("📋 Exporting context as dict")
        return {
            "interfaces": self.interfaces,
            "devices": self.devices,
            "credentials": self.credentials,
            "metadata": self.metadata,
            "store": dict(self._store),
            "event_log": list(self.event_log),
        }
