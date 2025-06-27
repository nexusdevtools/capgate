# src/paths.py

from pathlib import Path
import os # For os.access and os.W_OK
import sys # For sys.stderr

# Resolve to the directory containing this 'paths.py' file (which is 'src/')
THIS_DIR = Path(__file__).resolve().parent

# If paths.py is directly in 'src/', then the project root is one level up.
PROJECT_ROOT = THIS_DIR.parent # <--- CRITICAL FIX: Changed to .parent, which is `/home/nexus/capgate`

# Global Directories, relative to PROJECT_ROOT
PLUGIN_DIR = PROJECT_ROOT / "src" / "plugins"
PLUGIN_METADATA_CACHE = PLUGIN_DIR / ".plugin_metadata.json"
PLUGIN_TEMPLATE_DIR = PROJECT_ROOT / "src" / "plugin_template" / "my_new_plugin"

# Logging
LOG_DIR = PROJECT_ROOT / "logs"
DEFAULT_LOG_FILE = LOG_DIR / "capgate.log"

# Configuration Directory (for external configs like dnsmasq.conf)
CAPGATE_CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_CONFIG_FILE = CAPGATE_CONFIG_DIR / "capgate_config.yaml"

# Data Directory (for captures, topology, other persistent data)
CAPGATE_DATA_DIR = PROJECT_ROOT / "data"

# Captures (now a subdirectory of CAPGATE_DATA_DIR)
CAPTURE_DIR = CAPGATE_DATA_DIR / "captures"

# Temporary runtime files (still separate from captures/data unless you want them under data/tmp)
TMP_DIR = PROJECT_ROOT / "tmp"

# Output directory for plugin artifacts (now a subdirectory of CAPGATE_DATA_DIR)
OUTPUT_DIR = CAPGATE_DATA_DIR / "output"

# The wordlists directory is also a direct child of src
WORDLISTS_DIR = PROJECT_ROOT / "src" / "wordlists" # Added for direct access


REQUIRED_DIRS = [
    PLUGIN_DIR,
    LOG_DIR,
    CAPGATE_CONFIG_DIR,
    CAPGATE_DATA_DIR,
    CAPTURE_DIR,
    TMP_DIR,
    OUTPUT_DIR,
    WORDLISTS_DIR, # Ensure wordlists directory is created
]

def ensure_directories():
    """Ensures all required application directories exist."""
    for path in REQUIRED_DIRS:
        path.mkdir(parents=True, exist_ok=True)
        if not os.access(path, os.W_OK):
            print(f"WARNING: Directory '{path}' is not writable by current user. Operations may fail without sudo.", file=sys.stderr)

ensure_directories()
