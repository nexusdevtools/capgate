# cli.py — Entry point for CapGate CLI


from typing import List
import typer
from rich.console import Console
from rich.table import Table

from cli import graph  # your updated graph.py
from cli.boot import boot_sequence
from core.plugin_creator import create_plugin
from core.plugin_loader import PluginLoader
from runner import CapGateRunner
from paths import ensure_directories

app = typer.Typer(
    help="""CapGate — Wireless Network Intelligence Toolkit
⚡ The network that maps itself.
""",
    invoke_without_command=True
)

console = Console()
cli_state = {}
# Global CLI state dictionary to hold options like mock mode and auto-select
# Register graph subcommand here
app.add_typer(graph.app, name="graph")

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context,
                  mock_dev: bool = typer.Option(False, "--mock", help="Enable mock mode"),
                  auto: bool = typer.Option(False, "--auto", help="Auto-select plugin options")):
    """
    Main CLI entrypoint. Initializes CLI state and optionally displays the animated boot.
    """
    cli_state["mock_mode"] = mock_dev
    cli_state["auto_select"] = auto

    if ctx.invoked_subcommand is None:
        # Show animated CapGate intro
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
def interfaces(wireless_only: bool = typer.Option(False, "--wireless", "-w"),
               monitor_only: bool = typer.Option(False, "--monitor", "-m"),
               up_only: bool = typer.Option(False, "--up", "-u")):
    """
    List network interfaces, filtered by type or mode.
    """
    console.print("\n[bold green]🔍 Scanning for interfaces...[/bold green]")
    runner = CapGateRunner(cli_state=cli_state)
    interfaces = runner.get_interfaces(wireless_only, monitor_only, up_only)

    if not interfaces:
        console.print("[yellow]No matching interfaces found.[/yellow]")
        raise typer.Exit()

    table = Table(title="Available Interfaces")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Mode", style="yellow")
    table.add_column("Driver", style="blue")
    table.add_column("Monitor", justify="center")

    for iface in interfaces:
        iface_type = "Wireless" if iface.is_wireless else "Wired/Other"
        mon = "✅" if iface.supports_monitor_mode() else "❌"
        status = "[green]UP[/green]" if iface.is_up else "[red]DOWN[/red]"
        table.add_row(iface.name, iface_type, status, iface.current_mode or "N/A", iface.driver or "N/A", mon)

    console.print(table)

@app.command()
def plugins():
    """
    List all available CapGate plugins.
    """
    ensure_directories()
    loader = PluginLoader()
    plugins = loader.plugins

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

@app.command()
def run(plugin_name: str, plugin_args: List[str] = typer.Argument(None)):
    """
    Run a plugin with optional arguments.
    """
    console.print(f"[bold green]🚀 Running plugin:[/bold green] {plugin_name}")
    runner = CapGateRunner(cli_state=cli_state)
    ensure_directories()
    runner.run_plugin(plugin_name, *plugin_args)
    console.print(f"[green]✅ Done.[/green]")

@app.command("create-plugin")
def create_plugin_command(name: str,
                          author: str = typer.Option("Anonymous", "--author", "-a")):
    """
    Generate a plugin using the boilerplate template.
    """
    ensure_directories()
    try:
        create_plugin(name, author)
        console.print(f"✅ Plugin created at: [yellow]src/plugins/{name}[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error:[/red] {e}")

if __name__ == "__main__":
    app()
