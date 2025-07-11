# src/paths.py

import os
from pathlib import Path
import sys # Keep sys import for error messages or if you use it globally

# --- CORE PROJECT ROOT ---
# This assumes paths.py is located at nexusdevtools/src/paths.py
# Path(__file__).parent is src/, .parent.parent is nexusdevtools/
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


# --- CapGate Core Directories ---
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
PLUGIN_DIR = PROJECT_ROOT / "src" / "plugins" # Plugin dir is still under src/plugins

# --- Renamed/New Root for existing elements ---
PLUGIN_METADATA_CACHE = PLUGIN_DIR / ".plugin_metadata.json"
PLUGIN_TEMPLATE_DIR = PROJECT_ROOT / "src" / "plugin_template" / "my_new_plugin" # Assuming this path from your previous config

DEFAULT_LOG_FILE = LOG_DIR / "capgate.log"

CAPGATE_CONFIG_DIR = PROJECT_ROOT / "config" # Redundant with CONFIG_DIR, but keeping for consistency if used elsewhere
DEFAULT_CONFIG_FILE = CAPGATE_CONFIG_DIR / "capgate_config.yaml"

CAPGATE_DATA_DIR = PROJECT_ROOT / "data" # Redundant with DATA_DIR, but keeping
CAPTURE_DIR = CAPGATE_DATA_DIR / "captures"
TMP_DIR = PROJECT_ROOT / "tmp"
OUTPUT_DIR = CAPGATE_DATA_DIR / "output"

WORDLISTS_DIR = PROJECT_ROOT / "src" / "wordlists"

CAPGATE_WEB_ASSETS_DIR = PROJECT_ROOT / "src" / "web_assets"
CAPGATE_WEB_TEMPLATES_DIR = CAPGATE_WEB_ASSETS_DIR / "templates"
CAPGATE_WEB_CGI_DIR = CAPGATE_WEB_ASSETS_DIR / "cgi-bin"
CAPGATE_CREDENTIALS_FILE = CAPGATE_DATA_DIR / "captured_credentials.jsonl"


# --- NEW: Nexus Brain and Commands Directories ---
NEXUS_DIR = PROJECT_ROOT / "src" / "nexus"
NEXUS_CMDS_DIR = NEXUS_DIR / "cmds"


# --- Agent Specific Directories (Still using these) ---
AGENT_DIR = PROJECT_ROOT / "src" / "agent"
AGENT_KNOWLEDGE_BASE_DIR = AGENT_DIR / "knowledge_base"

# --- External Tool Directories (e.g., nexusdevtools) ---
# This now refers to the project root itself, as per your rename request
NEXUSDEVTOOLS_ROOT_DIR = PROJECT_ROOT


# List of directories that need to be ensured at startup
REQUIRED_DIRS = [
    CONFIG_DIR,
    DATA_DIR,
    LOG_DIR,
    PLUGIN_DIR,
    CAPTURE_DIR,
    TMP_DIR,
    OUTPUT_DIR,
    WORDLISTS_DIR,
    CAPGATE_WEB_ASSETS_DIR,
    CAPGATE_WEB_TEMPLATES_DIR,
    CAPGATE_WEB_CGI_DIR, # Keep if needed
    AGENT_DIR,
    AGENT_KNOWLEDGE_BASE_DIR,
    NEXUS_DIR,        # NEW: Ensure the nexus brain directory
    NEXUS_CMDS_DIR,   # NEW: Ensure the nexus commands directory
]

# This function ensures all core directories exist and are writable
def ensure_directories_for_capgate_startup():
    """Ensures all core CapGate directories exist."""
    print("INFO: capgate.paths: Ensuring core CapGate directories exist...", file=sys.stderr)
    for path in REQUIRED_DIRS:
        try:
            path.mkdir(parents=True, exist_ok=True)
            if not os.access(path, os.W_OK):
                print(f"WARNING: Directory '{path}' is not writable by current user. Operations may fail without sudo.", file=sys.stderr)
        except OSError as e:
            print(f"ERROR: Failed to create directory '{path}': {e}", file=sys.stderr)
            sys.exit(1)


# Note: ensure_directories_for_capgate_startup() will be explicitly called by the CapGateRunner's __init__ method.