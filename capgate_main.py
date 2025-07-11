# capgate.py
# New Root Entry Point for CapGate (formerly main.py)

import os
import sys
from base.logger import logger
from pathlib import Path
from dotenv import load_dotenv

# --- Ensure running as root ---
if os.geteuid() != 0:
    print("This application must be run as root. Please use sudo or run as root user.")
    sys.exit(1)

# --- Load environment variables as early as possible ---
PROJECT_ROOT = Path(__file__).parent.resolve()
load_dotenv(dotenv_path=PROJECT_ROOT / '.env')

# --- Set up basic logging for the entire application ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CapGateRoot")
logger.setLevel(logging.INFO)

# --- Ensure CapGate's src directory is in the Python Path ---
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
    logger.info(f"Added '{SRC_DIR}' to Python path.")

# --- Import Nexus Brain and Core Components ---
# This import now points to the new central orchestrator
from nexus.index import nexus_app # The new central Typer app in src/nexus/index.py
from runner import CapGateRunner # Still need this type for global runner
from cli.commands.boot import boot_sequence # For the initial boot sequence


# --- Global Runner Instance ---
_runner_instance: CapGateRunner = None


# --- Core Initialization Helper ---
def _initialize_capgate_core_components():
    """
    Initializes the core CapGate application components (Runner, State, Context).
    This function will be called by nexus.index.py to set up the global runner.
    """
    global _runner_instance
    logger.info("CapGate Root: Initializing core application components (Runner, State, Context)...")

    # The CapGateRunner.__init__ method will handle ensure_directories_for_capgate_startup()
    _runner_instance = CapGateRunner(cli_state={
        "mock_mode": False,  # Default for initial startup
        "auto_select": False # Default for initial startup
    })
    
    # Inject the runner instance into the CLI module's global setter
    # Note: cli.capgate_cli will now import from nexus.index, which sets the runner
    # We provide a general setter here for any global runner needs.
    # The actual Typer CLI set_global_runner will be handled by nexus.index.
    logger.info("CapGate Root: Core components initialized.")


# --- Main Application Entry Point ---
if __name__ == "__main__":
    # The capgate wrapper script calls this file.
    # This file's primary role is to set up the environment and then launch the Nexus CLI.

    logger.info("CapGate Root: Starting application...")

    # Initial boot sequence animation and intro messages
    # This happens *before* any Typer commands are processed
    boot_sequence()
    
    logger.info("\nCapGate is ready. Launching Nexus Command Center...")
    logger.info("Type 'capgate --help' or 'capgate help' for available commands.")
    
    # Now, hand off control to the Nexus CLI (Typer app)
    # The Nexus CLI (nexus.index) will handle further initialization based on commands.
    
    # Ensure initial core components are initialized before nexus takes over,
    # as nexus commands will rely on the runner being present.
    _initialize_capgate_core_components()

    # Pass control to the nexus_app from src/nexus/index.py
    # This will process the actual command-line arguments passed to 'capgate'
    nexus_app()