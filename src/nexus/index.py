# src/nexus/index.py
# The new central orchestrator for all CapGate commands

from base.logger import logger
import typer
from typer import Typer # Explicit import for TyperType
from typing import Optional # For runner instance type hint

# Import global runner setter from cli.capgate_cli (it still holds the global runner reference)
from cli.capgate_cli import set_global_runner, console as cli_console # console for dev mode printing

# Import the actual CapGateRunner class for type hinting
from runner import CapGateRunner 

# --- Import Core Command Modules (from src/nexus/cmds/core/) ---
from .cmds.core.boot import boot as core_boot_cmd # Import the 'boot' command function
from .cmds.core.version import version as core_version_cmd # Import the 'version' command function
from .cmds.core.dev import dev as core_dev_cmd # Import the 'dev' command function
from .cmds.core.orchestrate import orchestrate_network_audit as core_orchestrate_cmd # Import the 'orchestrate' command function

logger = logging.getLogger(__name__)

# --- The main Typer App for Nexus ---
nexus_app = Typer(
    help="""Nexus Command Center — The core brain for CapGate operations.
All CapGate commands are accessible through Nexus.
""",
    invoke_without_command=True
)

# --- Define Global Runner Get/Set (for use within Nexus and passed to commands) ---
_nexus_runner_instance: Optional[CapGateRunner] = None

def set_nexus_runner(runner: CapGateRunner):
    """Sets the global CapGateRunner instance for the Nexus orchestrator."""
    global _nexus_runner_instance
    _nexus_runner_instance = runner
    set_global_runner(runner) # Also ensure the old global CLI reference is updated
    logger.info("Nexus: CapGateRunner instance set for central orchestration.")

def get_nexus_runner() -> CapGateRunner:
    """Returns the globally managed CapGateRunner instance for Nexus."""
    if _nexus_runner_instance is None:
        logger.error("Nexus: CapGateRunner instance not initialized. Cannot proceed with command execution.")
        raise RuntimeError("CapGateRunner not initialized for Nexus. Run CapGate via its root capgate.py.")
    return _nexus_runner_instance


# --- Register Core Commands to Nexus App ---
nexus_app.command("boot", help=core_boot_cmd.__doc__)(core_boot_cmd) # Register 'boot'
nexus_app.command("version", help=core_version_cmd.__doc__)(core_version_cmd) # Register 'version'
nexus_app.command("dev", help=core_dev_cmd.__doc__)(core_dev_cmd) # Register 'dev'
nexus_app.command("orchestrate-network-audit", help=core_orchestrate_cmd.__doc__)(core_orchestrate_cmd) # Register 'orchestrate'


# --- Initial Callback for Nexus App ---
@nexus_app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    Nexus Command Center main callback.
    Initializes core components if no specific command is given, or prepares for command.
    """
    logger.info("Nexus: Main callback initiated.")
    
    if ctx.invoked_subcommand is None:
        logger.info("Nexus: No subcommand invoked. Showing help for Nexus commands.")
        # nexus_app help is automatically shown by Typer because invoke_without_command=True.
        # You can add custom welcome messages here if desired:
        # cli_console.print("\n[bold green]Welcome to Nexus Command Center![/bold green]")
        # cli_console.print("Type 'capgate help' for a list of commands.")