# capgate/src/paths.py

from pathlib import Path
import os
import sys

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent

PLUGIN_DIR = PROJECT_ROOT / "src" / "plugins"
PLUGIN_METADATA_CACHE = PLUGIN_DIR / ".plugin_metadata.json"
PLUGIN_TEMPLATE_DIR = PROJECT_ROOT / "src" / "plugin_template" / "my_new_plugin"

LOG_DIR = PROJECT_ROOT /"src"/ "logs"
DEFAULT_LOG_FILE = LOG_DIR / "capgate.log"

CAPGATE_CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_CONFIG_FILE = CAPGATE_CONFIG_DIR / "capgate_config.yaml"

CAPGATE_DATA_DIR = PROJECT_ROOT / "data"
CAPTURE_DIR = CAPGATE_DATA_DIR / "captures"
TMP_DIR = PROJECT_ROOT / "tmp"
OUTPUT_DIR = CAPGATE_DATA_DIR / "output"

WORDLISTS_DIR = PROJECT_ROOT / "src" / "wordlists"

CAPGATE_WEB_ASSETS_DIR = PROJECT_ROOT / "src" / "web_assets"
CAPGATE_WEB_TEMPLATES_DIR = CAPGATE_WEB_ASSETS_DIR / "templates"
CAPGATE_WEB_CGI_DIR = CAPGATE_WEB_ASSETS_DIR / "cgi-bin" # This dir is no longer copied from, but good to ensure exists.
CAPGATE_CREDENTIALS_FILE = CAPGATE_DATA_DIR / "captured_credentials.jsonl"

# --- ADD THESE LINES FOR AGENT AND NEXUSDEVTOOLS PATHS ---
AGENT_DIR = PROJECT_ROOT / "src" / "agent"
AGENT_KNOWLEDGE_BASE_DIR = AGENT_DIR / "knowledge_base"
# Assuming nexusdevtools is a top-level directory directly within your CapGate project root
NEXUSDEVTOOLS_ROOT_DIR = PROJECT_ROOT / "nexusdevtools"
# --- END ADDITIONS ---


# List of directories that need to be ensured at startup
REQUIRED_DIRS = [
    PLUGIN_DIR,
    LOG_DIR,
    CAPGATE_CONFIG_DIR,
    CAPGATE_DATA_DIR,
    CAPTURE_DIR,
    TMP_DIR,
    OUTPUT_DIR,
    WORDLISTS_DIR,
    CAPGATE_WEB_ASSETS_DIR,
    CAPGATE_WEB_TEMPLATES_DIR,
    # CAPGATE_WEB_CGI_DIR, # This is now specific to web_server_manager's temp root.
    # --- ADD THESE LINES TO YOUR EXISTING REQUIRED_DIRS LIST ---
    AGENT_DIR,
    AGENT_KNOWLEDGE_BASE_DIR,
    # --- END ADDITIONS ---
]

# Make ensure_directories a direct function call
def ensure_directories_for_capgate_startup():
    """Ensures all core CapGate directories exist."""
    print("INFO: capgate.paths: Ensuring core CapGate directories exist...", file=sys.stderr) # Use print for early visibility
    for path in REQUIRED_DIRS:
        try:
            path.mkdir(parents=True, exist_ok=True)
            if not os.access(path, os.W_OK):
                print(f"WARNING: Directory '{path}' is not writable by current user. Operations may fail without sudo.", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: Failed to create directory '{path}': {e}", file=sys.stderr)
            sys.exit(1) # Critical failure if core dirs cannot be created
    print("INFO: capgate.paths: Core CapGate directories ensured.", file=sys.stderr)

# No longer call ensure_directories() directly at module import.
# It will be called explicitly by CapGateRunner.