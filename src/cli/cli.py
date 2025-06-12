# /home/nexus/capgate/src/cli/cli.py
"""
cli.py — CapGate Command Line Interface using Typer

Entry point for all CLI interactions. This version uses on-demand initialization
to ensure that hardware-intensive operations are only run for commands that need them.
"""

from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table

# Core application imports
# These imports are now relative to the 'src' directory, assuming 'src' is on the PYTHONPATH.
from core.plugin_creator import create_plugin
from core.plugin_loader import PluginLoader # Import PluginLoader directly
from core.interface_manager import InterfaceInfo # For type hinting
from runner import CapGateRunner
from paths import ensure_directories

# --- Application Setup ---
app = typer.Typer(
    help="CapGate - A modular toolkit for network analysis and operations.",
    rich_markup_mode="markdown"
)
console = Console()


# --- CLI State Management ---
# This dictionary will hold state passed from the main callback to command functions.
# This avoids using global variables.
cli_state = {}


# --- Main CLI Callback ---
@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    mock_dev: bool = typer.Option(False, "--mock", help="Enable mock mode for development and testing."),
    auto: bool = typer.Option(False, "--auto", help="Enable auto-selection for options within plugins."),
):
    """
    Main entry point for the CapGate CLI.
    Initializes global options and displays help if no subcommand is provided.
    """
    # Store options in our state dictionary for other commands to access
    cli_state["mock_mode"] = mock_dev
    cli_state["auto_select"] = auto

    if ctx.invoked_subcommand is None:
        console.print("\n👋 Welcome to the [bold cyan]CapGate CLI[/bold cyan].")
        console.print("Use '--help' to see all available commands.")
        # The default Typer help is good, no need to raise an exit.


# --- Commands ---

@app.command()
def interfaces(
    wireless_only: bool = typer.Option(False, "--wireless", "-w", help="Show only wireless interfaces."),
    monitor_capable: bool = typer.Option(False, "--monitor", "-m", help="Show only monitor-capable interfaces."),
    up_only: bool = typer.Option(False, "--up", "-u", help="Show only interfaces that are currently UP.")
):
    """
    Detects and lists detailed information about system network interfaces.
    """
    console.print("\n[bold green]🔍 Detecting network interfaces...[/bold green] (This may take a moment)")
    
    # Initialize the runner ON-DEMAND for this command, as it needs hardware info.
    runner = CapGateRunner()
    
    # The runner's __init__ method now handles context setup.
    interface_objects: List[InterfaceInfo] = runner.get_interfaces(
        wireless_only=wireless_only,
        monitor_capable_only=monitor_capable,
        is_up_only=up_only
    )

    if not interface_objects:
        console.print("⚠️  No interfaces found matching the criteria.")
        raise typer.Exit()

    # Create a rich table for output
    table = Table(title="Detected Network Interfaces")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Mode", style="yellow")
    table.add_column("Driver", style="blue")
    table.add_column("Monitor Capable", justify="center")
    
    for iface in interface_objects:
        status = "[green]UP[/green]" if iface.is_up else "[red]DOWN[/red]"
        mon_capable = "✅" if iface.supports_monitor_mode() else "❌"
        iface_type = "Wireless" if iface.is_wireless else ("Loopback" if iface.name == "lo" else "Wired/Other")
        
        table.add_row(
            iface.name,
            iface_type,
            status,
            iface.current_mode or "N/A",
            iface.driver or "N/A",
            mon_capable
        )
    
    console.print(table)


@app.command()
def plugins():
    """
    Lists all available and properly configured plugins. **Does not scan for hardware.**
    """
    console.print("\n[bold green]🔍 Loading and listing available plugins...[/bold green]")
    
    # This command is lightweight. It instantiates PluginLoader directly
    # without the full CapGateRunner.
    try:
        ensure_directories() # Make sure the plugins directory exists
        plugin_loader = PluginLoader()
        loaded_plugins = plugin_loader.plugins
    except Exception as e:
        console.print(f"[bold red]Error loading plugins:[/bold red] {e}")
        raise typer.Exit()


    if not loaded_plugins:
        console.print("🚫 No plugins found or loaded.")
        raise typer.Exit()

    table = Table(title="Available CapGate Plugins")
    table.add_column("Plugin Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="magenta")
    table.add_column("Author", style="yellow")
    table.add_column("Description")

    for name, plugin in loaded_plugins.items():
        metadata = plugin.metadata
        table.add_row(
            name,
            metadata.get("version", "N/A"),
            metadata.get("author", "Unknown"),
            metadata.get("description", "No description provided.")
        )
    
    console.print(table)


@app.command()
def run(
    plugin_name: str = typer.Argument(..., help="The name of the plugin to run."),
    plugin_args: List[str] = typer.Argument(None, help="Optional arguments to pass to the plugin.")
):
    """
    Runs a specified plugin with optional arguments.
    """
    console.print(f"\n[bold green]🚀 Initializing runner to execute plugin: [cyan]{plugin_name}[/cyan][/bold green]")
    
    # Initialize the runner ON-DEMAND for this command
    runner = CapGateRunner(cli_state=cli_state) # Pass global CLI options to the runner
    
    # Ensure directories exist before running a plugin that might need them
    ensure_directories()
    
    runner.run_plugin(plugin_name, *plugin_args)
    console.print(f"\n[bold green]✅ Finished execution of plugin: [cyan]{plugin_name}[/cyan][/bold green]")


@app.command("create-plugin")
def create_plugin_command(
    name: str = typer.Argument(..., help="The name for the new plugin (e.g., 'port-scanner')."),
    author: str = typer.Option("Anonymous", "--author", "-a", help="The author's name for metadata.")
):
    """
    Creates a new plugin from a template. **Does not scan for hardware.**
    """
    console.print(f"\n[bold green]🛠️  Creating new plugin: [cyan]{name}[/cyan][/bold green]")
    
    # This command is now lightweight. It does NOT instantiate CapGateRunner.
    # It just calls the file creation utility directly.
    try:
        # Ensure the plugin housing exists
        ensure_directories()
        create_plugin(name, author)
        console.print(f"✅ Successfully created plugin files at [yellow]src/plugins/{name}[/yellow]")
    except FileExistsError as e:
        # Catch the specific error from the creator function for a better message
        console.print(f"[bold red]Error:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")


# --- Main Entrypoint ---
if __name__ == "__main__":
    # This makes the script runnable with `python -m cli.cli`
    app()
