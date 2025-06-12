# src/capgate/paths.py

from pathlib import Path

# Resolve to capgate/src/capgate
ROOT_DIR = Path(__file__).resolve().parent

# Plugin system
PLUGIN_DIR = ROOT_DIR / "plugins"
PLUGIN_METADATA_CACHE = PLUGIN_DIR / ".plugin_metadata.json"
PLUGIN_TEMPLATE_DIR = ROOT_DIR / "plugin_template" / "my_new_plugin"

# Logging
LOG_DIR = ROOT_DIR / "logs"
DEFAULT_LOG_FILE = LOG_DIR / "capgate.log"

# Configuration
CONFIG_DIR = ROOT_DIR / "config"
DEFAULT_CONFIG_FILE = CONFIG_DIR / "capgate_config.yaml"

# Captures
CAPTURE_DIR = ROOT_DIR / "captures"

# Temporary runtime files
TMP_DIR = ROOT_DIR / "tmp"

# Output directory for plugin artifacts
OUTPUT_DIR = ROOT_DIR / "output"

REQUIRED_DIRS = [
    PLUGIN_DIR,
    LOG_DIR,
    CONFIG_DIR,
    CAPTURE_DIR,
    TMP_DIR,
    OUTPUT_DIR,
]

def ensure_directories():
    for path in REQUIRED_DIRS:
        path.mkdir(parents=True, exist_ok=True)

ensure_directories()
