"""
exceptions.py — Custom exception hierarchy for CapGate.
Defines structured, meaningful errors used across the core system and plugins.
"""

class CapGateError(Exception):
    """Base exception for all CapGate-related errors."""
    pass


class PluginLoadError(CapGateError):
    """Raised when a plugin fails to load properly."""
    def __init__(self, plugin_name: str, message: str):
        super().__init__(f"Plugin '{plugin_name}' failed to load: {message}")
        self.plugin_name = plugin_name


class PluginExecutionError(CapGateError):
    """Raised when a plugin throws an error during execution."""
    def __init__(self, plugin_name: str, message: str):
        super().__init__(f"Plugin '{plugin_name}' execution failed: {message}")
        self.plugin_name = plugin_name


class InterfaceDetectionError(CapGateError):
    """Raised when there is a failure in detecting or parsing interfaces."""
    def __init__(self, message: str):
        super().__init__(f"Interface detection failed: {message}")
