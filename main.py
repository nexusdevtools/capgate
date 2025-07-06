# capgate/main.py

import os
import sys
import logging
from pathlib import Path
import argparse
import typer

# --- Set up basic logging for the entire application ---
# This logger will catch messages from main.py, cli.py, runner.py, and agent modules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CapGateRoot") # Specific logger for the root
logger.setLevel(logging.INFO) # Set default level for the root logger

# --- Ensure CapGate's src directory is in the Python Path ---
# This allows importing modules like 'cli.capgate_cli' and 'agent.mod_coor'
# directly by their module name, without needing 'src.' prefix.
CAPGATE_ROOT_DIR = Path(__file__).parent.resolve() # Get absolute path of the directory containing this script
SRC_DIR = CAPGATE_ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
    logger.info(f"Added '{SRC_DIR}' to Python path.")


# --- Import CapGate Core Components ---
# These imports now rely on `src/` being in sys.path, so they are direct module imports
from cli.capgate_cli import app as capgate_cli_app, set_global_runner # Corrected import from cli.capgate_cli
from runner import CapGateRunner # Corrected import for runner

# Import agent sub-applications/modules and the specific Typer apps to merge
from agent.mod_coor import initialize_capgate_agent, index_capgate_knowledge
from cli.graph import app as graph_app # Import graph app directly
from cli.commands.debug_commands import debug_cli # Import debug app directly


# --- Global Runner Instance ---
_runner_instance: CapGateRunner = None

# --- Main CapGate Application Initialization and Orchestration ---
def initialize_capgate_application(cli_mock_mode: bool = False, cli_auto_select: bool = False):
    """
    Initializes the core CapGate application components, including the runner.
    """
    global _runner_instance
    
    logger.info("CapGate Root: Initializing core application components...")
    
    # CapGateRunner's __init__ method will call ensure_directories_for_capgate_startup() from src.paths
    _runner_instance = CapGateRunner(cli_state={
        "mock_mode": cli_mock_mode,
        "auto_select": cli_auto_select
    })
    
    # Inject the runner instance into the CLI module
    set_global_runner(_runner_instance)
    logger.info("CapGate Root: CapGateRunner initialized and injected into CLI.")


def initialize_mcp_agent(force_index: bool = False):
    """
    Initializes the MCP AI Agent.
    """
    logger.info("CapGate Root: Attempting to initialize MCP Agent...")
    
    # The paths in agent.tools and agent.mod_coor are now directly imported from src.paths,
    # which uses the globally defined PROJECT_ROOT based on main.py's location.
    # No explicit `set_capgate_root_dirs` call is needed here for the agent's path setup.

    try:
        initialize_capgate_agent() # This initializes LLM, embedding, and loads KB
        if force_index:
            logger.info("CapGate Root: Agent initialization complete. Forcing knowledge re-indexing as requested.")
            index_capgate_knowledge() # Call the index function from agent.mod_coor
        logger.info("CapGate Root: MCP Agent ready to assist.")
    except Exception as e:
        logger.error(f"CapGate Root: Failed to initialize MCP Agent: {e}. AI assistance will be unavailable.")
        # Optionally, clear agent instance here if its presence could cause issues
        # from agent.mod_coor import capgate_agent_instance # If needed to set to None. Better to check if None when used.


# --- Main Typer CLI App for Root ---
root_app = typer.Typer(
    help="""CapGate - The Wireless Network Intelligence Toolkit (Root Orchestrator)
This is the main entry point for CapGate, managing core application, CLI, and AI Agent.
""",
    invoke_without_command=True
)

# Merge the top-level commands from capgate_cli_app into root_app.
for command_info in capgate_cli_app.registered_commands: # Iterate over CommandInfo objects
    root_app.command(name=command_info.name, help=command_info.help)(command_info.callback) # FIX: Use .callback

# --- Explicitly add the sub-Typer apps from capgate_cli to root_app ---
# These are the apps that were added via `app.add_typer()` in capgate_cli.py
root_app.add_typer(graph_app, name="graph")
root_app.add_typer(debug_cli, name="debug")
# --- END EXPLICIT ADDITIONS ---

@root_app.callback(invoke_without_command=True)
def root_main_callback(ctx: typer.Context,
                       mock: bool = typer.Option(False, "--mock", help="Enable mock mode for runner."),
                       auto: bool = typer.Option(False, "--auto", help="Auto-select plugin options for runner."),
                       no_agent: bool = typer.Option(False, "--no-agent", help="Do not initialize the AI agent."),
                       index_agent: bool = typer.Option(False, "--index-agent", help="Force re-indexing of agent knowledge on startup.")):
    """
    Main callback for the root CapGate application.
    Initializes core components and the AI Agent.
    """
    logger.info("CapGate Root: Root callback initiated.")
    
    # Initialize core CapGateRunner based on root CLI options
    initialize_capgate_application(cli_mock_mode=mock, cli_auto_select=auto)

    # Initialize agent based on root CLI options
    if not no_agent:
        initialize_mcp_agent(force_index=index_agent)
    else:
        logger.info("CapGate Root: AI Agent initialization skipped as requested by --no-agent.")

    # If no specific command was invoked, and not just setting up core/agent, maybe show help
    if ctx.invoked_subcommand is None:
        logger.info("CapGate Root: No subcommand invoked. Showing help for main commands.")
        # This will show help for the root_app, which now includes all commands from src/cli/capgate_cli.py
        typer.echo(root_app.info.help)


# --- Example: Add a new root-level command that uses both runner and agent (hypothetically) ---
@root_app.command("orchestrate-network-audit", help="Orchestrates a comprehensive network audit using agent guidance.")
def orchestrate_network_audit_command(
    interface_name: str = typer.Argument(..., help="Network interface to use for the audit.")
):
    """
    A hypothetical command showing how the root orchestrator could combine runner and agent capabilities.
    """
    logger.info(f"Root Orchestrator: Starting comprehensive network audit on {interface_name}...")
    
    # Example: Use runner to get interface details
    runner = _runner_instance
    if runner is None:
        logger.error("CapGateRunner not initialized for orchestration.")
        raise typer.Exit(code=1)

    interfaces = runner.get_interfaces(wireless_only=False, monitor_only=False, up_only=True)
    target_interface = next((i for i in interfaces if i.name == interface_name), None)

    if not target_interface:
        logger.error(f"Interface '{interface_name}' not found or not up.")
        raise typer.Exit(code=1)

    logger.info(f"CapGate Runner: Found interface details for {interface_name}: IP={target_interface.ip_address}")

    # Example: Use agent to get guidance
    # Ensure agent is initialized before asking
    # Corrected import path for agent.mod_coor
    from agent.mod_coor import capgate_agent_instance, ask_capgate_agent
    if capgate_agent_instance is None:
        logger.error("MCP Agent is not initialized. Cannot get audit guidance.")
        raise typer.Exit(code=1)

    agent_guidance_query = f"Given that I want to perform a comprehensive network audit on interface {interface_name} ({target_interface.ip_address}), what are the recommended CapGate plugins and steps, focusing on security best practices?"
    logger.info("Asking agent for audit guidance...")
    audit_guidance = ask_capgate_agent(agent_guidance_query)
    
    print("\n--- Agent's Audit Guidance ---")
    print(audit_guidance)
    print("------------------------------")

    logger.info("Root Orchestrator: Audit guidance received. Now you would proceed with executing plugins based on this.")
    # Here, you could programmatically call runner.run_plugin() based on agent's suggestions
    # E.g., if "nmap_scan_plugin" was suggested: runner.run_plugin("nmap_scan_plugin", interface_name)


# --- Main entry point for the root application ---
if __name__ == "__main__":
    # Typer handles parsing arguments and invoking the callback/commands
    root_app()