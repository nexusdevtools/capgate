# src/cli/cli.py

import sys
# Removed json, pathlib, List, Optional, Dict, Any from here as they are imported where needed or from local types
from typing import List, Optional, Dict, Any # Keep these for now as used in function signatures

from typer import Typer, Option, Argument, Context # <--- No Depends import here
from typer import Typer as TyperType

from rich.console import Console
from rich.table import Table
import typer


# Import commands/apps
from cli.commands.boot import boot_sequence
from cli.graph import app as graph_app
from cli.commands.debug_commands import debug_cli
from core.plugin_creator import create_plugin
from core.plugin_loader import PluginLoader
from runner import CapGateRunner
from db.schemas.interface import Interface
from db.schemas.device import Device # Ensure Device is imported if used in other modules indirectly
app: TyperType = typer.Typer()
app: typer.Typer = typer.Typer()

app = Typer(
    help="""CapGate — Wireless Network Intelligence Toolkit
⚡ The network that maps itself.
""",
    invoke_without_command=True
)

console = Console()

# Global variables for mock_mode and auto_select, initialized to False
_mock_mode: bool = False
_auto_select: bool = False

# Global variable to hold the single CapGateRunner instance
_runner_instance: Optional[CapGateRunner] = None

# Register graph and debug subcommands
app.add_typer(graph_app, name="graph")
app.add_typer(debug_cli, name="debug")

# --- Helper to get the runner instance ---
def get_global_runner() -> CapGateRunner:
    """Returns the globally managed CapGateRunner instance."""
    global _runner_instance
    if _runner_instance is None:
        # This branch should ideally not be hit if main_callback always runs first
        # But it's a safeguard for direct command calls without a full Typer app run.
        # In a real app, you'd ensure main_callback always sets it.
        _runner_instance = CapGateRunner(cli_state={"mock_mode": _mock_mode, "auto_select": _auto_select})
    return _runner_instance
# --- End Helper ---


@app.callback(invoke_without_command=True)
def main_callback(ctx: Context,
                  mock: bool = Option(False, "--mock", help="Enable mock mode"),
                  auto: bool = Option(False, "--auto", help="Auto-select plugin options")):
    """
    Main CLI entrypoint. Initializes global CLI options and the CapGateRunner.
    """
    global _mock_mode, _auto_select, _runner_instance
    _mock_mode = mock
    _auto_select = auto

    # Initialize the single CapGateRunner instance here
    # This ensures AppState is set up and scanners run once at CLI startup
    _runner_instance = CapGateRunner(cli_state={
        "mock_mode": _mock_mode,
        "auto_select": _auto_select
    })

    if ctx.invoked_subcommand is None:
        boot_sequence()

@app.command()
def boot():
    """Launch the animated CapGate boot sequence."""
    boot_sequence()

@app.command()
def version():
    """Display the current version of CapGate."""
    typer.echo("CapGate v0.1.0")

@app.command()
def interfaces(wireless_only: bool = Option(False, "--wireless", "-w"),
               monitor_only: bool = Option(False, "--monitor", "-m"),
               up_only: bool = Option(False, "--up", "-u")):
    """
    List network interfaces, filtered by type or mode.
    """
    console.print("\n[bold green]🔍 Scanning for interfaces...[/bold green]")
    runner = get_global_runner() # Get the global runner instance
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

@app.command()
def plugins():
    """
    List all available CapGate plugins.
    """
    runner = get_global_runner() # Get the global runner instance
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
    runner = get_global_runner() # Get the global runner instance
    
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
        # This function might need CapGateRunner if it writes to config, etc.
        # But for now, assumes it just creates files.
        create_plugin(name, author) 
        console.print(f"✅ Plugin created at: [yellow]src/plugins/{name}[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error:[/red] {e}")

if __name__ == "__main__":
    app()