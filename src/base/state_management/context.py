# core/state_management/context.py
"""
context.py — Runtime Operational Context
Encapsulates short-lived metadata and execution state per CLI run or plugin task.
"""

from __future__ import annotations
from threading import RLock
from typing import Any, Dict

# IMPORT THE REAL APPSTATE SINGLETON HERE
from .state import get_state, AppState as GlobalAppState # <--- CRITICAL CHANGE: Alias AppState


class CapGateContext:
    """
    Task-scoped operational context for runtime execution.

    Attributes:
        runtime_meta (Dict[str, Any]): Per-run metadata (e.g., current plugin, interface, flags).
        state (GlobalAppState): Reference to shared *global* application state.
    """
    def __init__(self):
        self.runtime_meta: Dict[str, Any] = {}
        self.state: GlobalAppState = get_state() # <--- CRITICAL CHANGE: Get the singleton AppState
        self._lock: RLock = RLock()

    def set(self, key: str, value: Any) -> None:
        """Thread-safe context setter (for runtime_meta)."""
        with self._lock:
            self.runtime_meta[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Thread-safe context getter (for runtime_meta)."""
        with self._lock:
            return self.runtime_meta.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Export runtime context's metadata as a dictionary."""
        with self._lock:
            return dict(self.runtime_meta)


# Singleton accessor
_context_instance = CapGateContext()

def get_context() -> CapGateContext:
    """Returns the singleton CapGateContext instance."""
    return _context_instance
