# src/cli/capgate_cli.py
# This file now serves as a stub for global CLI-related helpers.
# All CLI commands have been moved to src/nexus/cmds/

from base.logger import logger
from typer import Typer # Needed for TyperType hint in set_global_runner
from rich.console import Console # For the console object
from typing import Optional # For Optional type hint
from runner import CapGateRunner # For CapGateRunner type hint

logger = logging.getLogger(__name__)
console = Console() # Global console instance

# Global variable to hold the single CapGateRunner instance, set by capgate.py
_runner_instance: Optional[CapGateRunner] = None

# --- Function to set the global runner instance (called by root capgate.py) ---
def set_global_runner(runner: CapGateRunner):
    """Sets the globally managed CapGateRunner instance for CLI-wide access."""
    global _runner_instance
    _runner_instance = runner
    logger.info("CapGateRunner instance injected into global CLI context.")

# The `app` Typer instance that previously lived here is now `nexus_app` in src/nexus/index.py.
# All commands previously defined here have been or will be moved to src/nexus/cmds/.

# You can remove all other commands (boot, version, interfaces, plugins, run, create-plugin,
# agent-ask, agent-interactive, agent-index, docs_app) from this file.