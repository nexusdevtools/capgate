# capgate/src/cli/capgate_cli.py

import sys
from typing import List, Optional, Dict, Any, Tuple
import logging
import subprocess
from pathlib import Path

from typer import Typer, Option, Argument, Context
from typer import Typer as TyperType

from rich.console import Console
from rich.table import Table
import typer

from paths import PROJECT_ROOT # Ensure PROJECT_ROOT is imported


# Import commands/apps - these are relative imports within src/cli/
from .commands.boot import boot_sequence
from .graph import app as graph_app
from .commands.debug_commands import debug_cli

# Imports for types and core functionality - these are relative to src/
from core.plugin_creator import create_plugin
from runner import CapGateRunner
from db.schemas.interface import Interface

# Set up logger for this module
logger = logging.getLogger(__name__)


app: TyperType = typer.Typer(
    help="""CapGate — Wireless Network Intelligence Toolkit
⚡ The network that maps itself.
""",
    invoke_without_command=True
)

console = Console()

# Global variables for mock_mode and auto_select, initialized to False
_mock_mode: bool = False
_auto_select: bool = False

# Global variable to hold the single CapGateRunner instance, set by main.py
_runner_instance: Optional[CapGateRunner] = None

# --- Function to set the global runner instance (called by root main.py) ---
def set_global_runner(runner: CapGateRunner):
    """Sets the globally managed CapGateRunner instance for the CLI."""
    global _runner_instance
    _runner_instance = runner
    logger.info("CapGateRunner instance injected into CLI.")

# --- Helper to get the runner instance ---
def get_global_runner() -> CapGateRunner:
    """Returns the globally managed CapGateRunner instance."""
    global _runner_instance
    if _runner_instance is None:
        logger.error("CapGateRunner instance not initialized in CLI. Please run CapGate via its root main.py.")
        raise RuntimeError("CapGateRunner not initialized. Critical CLI operations cannot proceed.")
    return _runner_instance


# Register graph and debug subcommands
app.add_typer(graph_app, name="graph")
app.add_typer(debug_cli, name="debug")


@app.callback(invoke_without_command=True)
def main_callback(ctx: Context,
                  mock: bool = Option(False, "--mock", help="Enable mock mode"),
                  auto: bool = Option(False, "--auto", help="Auto-select plugin options")):
    """
    Main CLI entrypoint. Initializes global CLI options.
    The CapGateRunner is now initialized by the root main.py and injected via set_global_runner.
    """
    global _mock_mode, _auto_select
    _mock_mode = mock
    _auto_select = auto

    runner = get_global_runner()
    runner.cli_state.update({
        "mock_mode": _mock_mode,
        "auto_select": _auto_select
    })
    logger.info(f"CLI options applied to runner: mock={_mock_mode}, auto={_auto_select}")


    if ctx.invoked_subcommand is None:
        boot_sequence()

@app.command()
def boot():
    """Launch the animated CapGate boot sequence."""
    boot_sequence()

@app.command()
def version():
    """Display the current current version of CapGate."""
    typer.echo("CapGate v0.1.0")

@app.command()
def interfaces(wireless_only: bool = Option(False, "--wireless", "-w"),
               monitor_only: bool = Option(False, "--monitor", "-m"),
               up_only: bool = Option(False, "--up", "-u")):
    """
    List network interfaces, filtered by type or mode.
    """
    console.print("\n[bold green]🔍 Scanning for interfaces...[/bold green]")
    runner = get_global_runner()
    interfaces: List[Interface] = runner.get_interfaces(wireless_only, monitor_only, up_only)

    if not interfaces:
        console.print("[yellow]No matching interfaces found.[/yellow]")
        raise typer.Exit()

    table = Table(title="Available Interfaces")
    table.add_column("Name", style="cyan")
    table.add_column("MAC", style="white")
    table.add_column("IP Address", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Mode", style="yellow")
    table.add_column("Driver", style="blue")
    table.add_column("Monitor Capable", justify="center")

    for iface in interfaces:
        iface_type = "Wireless" if iface.driver and iface.mode != "ethernet" else "Wired/Other"
        mon_capable = "✅" if iface.supports_monitor else "❌"
        status = "[green]UP[/green]" if iface.is_up else "[red]DOWN[/red]"
        
        table.add_row(
            iface.name, 
            iface.mac, 
            iface.ip_address or "N/A", 
            status, 
            iface.mode or "N/A", 
            iface.driver or "N/A", 
            mon_capable
        )

    console.print(table)

@app.command("plugins")
def plugins():
    """
    List all available CapGate plugins.
    """
    runner = get_global_runner()
    plugins = runner.plugin_loader.plugins 

    if not plugins:
        console.print("[red]No plugins found.[/red]")
        raise typer.Exit()

    table = Table(title="CapGate Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Author", style="yellow")
    table.add_column("Description")

    for name, plugin in plugins.items():
        meta = plugin.metadata
        table.add_row(
            name,
            meta.get("version", "N/A"),
            meta.get("author", "Unknown"),
            meta.get("description", "No description.")
        )
    console.print(table)

@app.command("run")
def run_command(plugin_name: str, 
                plugin_args: Optional[List[str]] = Argument(None)):
    """
    Run a plugin with optional arguments.
    """
    console.print(f"[bold green]🚀 Running plugin:[/bold green] {plugin_name}")
    runner = get_global_runner()
    
    plugin_args = plugin_args or []

    runner.run_plugin(plugin_name, *plugin_args)

    console.print(f"[green]✅ Done.[/green]")


@app.command("create-plugin")
def create_plugin_command(name: str,
                          author: str = Option("Anonymous", "--author", "-a")):
    """
    Generate a plugin using the boilerplate template.
    """
    try:
        create_plugin(name, author) 
        console.print(f"✅ Plugin created at: [yellow]src/plugins/{name}[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error:[/red] {e}")


# --- New Typer commands for the Agent ---
from agent.mod_coor import ask_capgate_agent, start_capgate_agent_interactive_session, index_capgate_knowledge

@app.command("agent-ask", help="Ask the MCP AI Agent a question or give it a task.")
def agent_ask_command(query: str = Argument(..., help="The question or task for the AI agent.")):
    """
    Ask the MCP AI Agent a question or give it a task.
    """
    logger.info(f"CLI: Asking agent: {query}")
    print(f"\n--- Asking MCP Agent ---\n")
    response = ask_capgate_agent(query)
    print(f"\n--- MCP Agent Response ---\n{response}\n--------------------------")

@app.command("agent-interactive", help="Start an interactive chat session with the MCP AI Agent.")
def agent_interactive_command():
    """
    Start an interactive chat session with the MCP AI Agent.
    """
    logger.info("CLI: Starting agent interactive session.")
    start_capgate_agent_interactive_session()

@app.command("agent-index", help="Rebuild the MCP AI Agent's knowledge base.")
def agent_index_command():
    """
    Rebuild the MCP AI Agent's knowledge base.
    """
    logger.info("CLI: Requesting agent knowledge re-indexing.")
    print("\n--- Rebuilding Agent Knowledge Base ---")
    index_capgate_knowledge()
    print("--- Agent Knowledge Base Rebuilding Initiated. Check logs. ---")


# --- NEW: Docs Generation Typer Sub-app ---
docs_app = Typer(
    help="Commands for managing CapGate documentation.",
    invoke_without_command=False # Ensure a subcommand is always invoked
)

@docs_app.command("build")
def docs_build_command(
    output_dir: Path = Option(
        PROJECT_ROOT / "docs" / "pdoc_output", # Default output path
        "--output", "-o", help="Directory to save the generated documentation."
    ),
    # REMOVED: format: str = Option(...) because pdoc v13+ doesn't use --format for markdown
    module_path: Path = Option(
        PROJECT_ROOT / "src", # Default module path (CapGate's source)
        "--module", "-m", help="Path to the module/package to document."
    )
):
    """
    Builds documentation for CapGate's source code using pdoc.
    (Outputs HTML by default with pdoc v13+).
    """
    # REMOVED: format validation if format option is removed.

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Construct the pdoc command for pdoc v13+
    # pdoc uses the module path relative to where it's run, or it needs the Python path set correctly.
    # It's safer to provide the full path to the module.
    pdoc_command = [
        sys.executable, "-m", "pdoc", # Use python -m pdoc for venv compatibility
        str(module_path), # Path to the module/package (e.g., 'src/')
        "--output-directory", str(output_dir), # Correct argument for output directory
        # REMOVED: "--overwrite" because it's no longer a valid argument and is default behavior
    ]
    
    console.print(f"[bold green]📚 Building documentation with pdoc...[/bold green]")
    console.print(f"  Source: [yellow]{module_path}[/yellow]")
    console.print(f"  Output: [yellow]{output_dir} (HTML)[/yellow]") # Clarify output is HTML
    logger.info(f"Running pdoc command: {' '.join(pdoc_command)}")

    try:
        process = subprocess.run(pdoc_command, capture_output=True, text=True, check=True)
        console.print("[green]✅ Documentation built successfully.[/green]")
        if process.stdout:
            logger.debug(f"pdoc stdout:\n{process.stdout}")
        if process.stderr:
            logger.warning(f"pdoc stderr:\n{process.stderr}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error building documentation:[/red] {e.stderr}")
        logger.error(f"pdoc command failed: {e.cmd}\n{e.stderr}")
        raise typer.Exit(code=1)
    except FileNotFoundError:
        console.print("[red]❌ Error:[/red] `pdoc` command not found. Ensure `pdoc` is installed in your virtual environment (`pip install pdoc`).")
        logger.error("pdoc command not found.")
        raise typer.Exit(code=1)

# Add the new docs_app as a subcommand to the main app
app.add_typer(docs_app, name="docs")

@app.command("dev", hidden=True)
def dev():
    """
    Development helper function to run the CLI app.
    This is for development convenience only.
    """
    # This function is not intended to be used in production.
    # It is here to allow running the CLI directly during development.
    app()


# REMOVE the if __name__ == "__main__": app() block from this file.
# This file will no longer be the direct entry point.