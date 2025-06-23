# 🧠 CapGate Runtime Context — `CapGateContext`

## Module: `core/state_management/context.py`

### Purpose

Encapsulates transient, runtime-specific metadata for the current CLI session or plugin execution context. Provides thread-safe methods for temporarily storing operational metadata while maintaining a link to the shared application state.

---

## 📐 Structure

### Class: `CapGateContext`

A singleton object accessed via `get_context()`.

#### Attributes

| Name           | Type             | Description                                        |
| -------------- | ---------------- | -------------------------------------------------- |
| `runtime_meta` | `Dict[str, Any]` | In-memory metadata about the current task/session. |
| `state`        | `AppState`       | Shared reference to global application state.      |
| `_lock`        | `RLock`          | Thread-safety mechanism for concurrent access.     |

#### Methods

| Name        | Returns          | Description                                    |
| ----------- | ---------------- | ---------------------------------------------- |
| `set()`     | `None`           | Safely assigns a value to `runtime_meta`.      |
| `get()`     | `Any`            | Retrieves a value from `runtime_meta`.         |
| `to_dict()` | `Dict[str, Any]` | Export the current context metadata as a dict. |

#### Accessor

```python
from capgate.core.state_management.context import get_context
context = get_context()
```

---

## 🔄 Usage Cycle

```mermaid
flowchart TD
    CLI -->|sets current plugin| CapGateContext.set("current_plugin", "wifi_scan")
    Plugin -->|reads interface| CapGateContext.get("interface")
    Debugger -->|dumps runtime| CapGateContext.to_dict()
```

---

## ✅ Developer Notes

* Context is scoped to runtime logic (e.g. active plugin, selected interface).
* Thread-safe via internal locking (useful for async plugins or threaded tools).
* Always use `get_context()` to access the singleton.
* Can evolve into a transactional context manager (future roadmap).

---

## 🔗 Related Modules

* `core/state_management/state.py` — shared persistent state backend
* `cli.py` — injects CLI args into `runtime_meta`
* `plugin_runner.py` — accesses context during execution
