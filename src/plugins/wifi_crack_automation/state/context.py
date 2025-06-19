# /home/nexus/capgate/src/plugins/wifi_crack_automation/state/context.py

context = {
    "app_context": None,            # To store the global AppContext if passed from main.py
    "mock_mode": False,             # Is the plugin running in mock_mode?
    "auto_select": False,           # Should interface/options be auto-selected?

    "interface": None,              # The originally selected physical interface (e.g., "wlan0")
    "original_interface_for_nm": None, # Stores the name of the interface whose NM management was changed
    "monitor_interface": None,      # The name of the interface in monitor mode (e.g., "wlan0" or "wlan0mon")
    "nm_was_set_unmanaged": False,  # Flag: True if NM was told to unmanage the original interface

    "target_bssid": None,
    "target_channel": None,
    "target_essid": None,
    "capture_dir": "handshakes",    # Default capture directory
    "capture_file": None,           # Path to the captured handshake file

    "crack_method": None,           # e.g., "dictionary", "bruteforce"
    "wordlist_path": None,          # Path to the wordlist for dictionary attacks
    "key_found": None,              # The cracked key, if successful
    "crack_results": None           # More detailed results from the cracking process
}

def reset_context():
    """Reset the context to its initial state."""
    global context
    # Ensure all keys are reset to their default initial values
    context = {
        "app_context": None,
        "mock_mode": False,
        "auto_select": False,
        "interface": None,
        "original_interface_for_nm": None,
        "monitor_interface": None,
        "nm_was_set_unmanaged": False,
        "target_bssid": None,
        "target_channel": None,
        "target_essid": None,
        "capture_dir": "handshakes",
        "capture_file": None,
        "crack_method": None,
        "wordlist_path": None,
        "key_found": None,
        "crack_results": None
    }

from typing import Any

def set_context(key: str, value: Any):
    """
    Set a value in the context.
    It's generally recommended for phases to modify the context dictionary
    passed to them directly. This function is here if a more controlled
    set operation is needed, but it will raise an error for undefined keys
    to enforce the context schema.
    """
    if key in context:
        context[key] = value
    else:
        # To allow dynamic keys, you would remove this check and just do:
        # context[key] = value
        # However, for a defined schema, pre-defining keys is better.
        raise KeyError(f"Context key '{key}' is not pre-defined in state.context.py. Add it to the initial 'context' dict if it's a valid key.")

def get_context(key: str, default: Any = None) -> Any:
    """Get a value from the context, returning default if not set."""
    return context.get(key, default)