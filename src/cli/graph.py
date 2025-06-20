# capgate/cli/graphs.py

import typer
from pathlib import Path
import json
from rich.console import Console

from core.graphs.topology import TopologyGraph
from core.context import AppContext

app = typer.Typer(help="🧠 Network topology graph commands")
console = Console()

DEFAULT_DISCOVERY_PATHS = [
    Path("data/topology/discovery.json"),
    Path("capgate/data/topology/discovery.json"),
    Path("src/data/topology/discovery.json"),
    Path("/home/nexus/capgate/data/topology/discovery.json"),
]

def find_discovery_file(custom_path: str = None) -> Path:
    if custom_path:
        path = Path(custom_path)
        if path.exists():
            return path.resolve()
        else:
            console.print(f"[red]❌ Specified discovery file not found: {custom_path}[/red]")
            raise typer.Exit(1)
    for path in DEFAULT_DISCOVERY_PATHS:
        if path.exists():
            return path.resolve()
    console.print("[red]❌ discovery.json not found in default locations.[/red]")
    raise typer.Exit(1)

def print_ascii_graph(data: dict):
    nodes = {node["id"]: node.get("label", node["id"]) for node in data.get("nodes", [])}
    edges = data.get("edges", [])

    console.print("[green]📡 ASCII Network Topology Graph:[/green]\n")
    for node_id, label in nodes.items():
        console.print(f"• {label} ({node_id})")
    console.print("\n[blue]🔗 Connections:[/blue]")
    for edge in edges:
        src_label = nodes.get(edge["source"], edge["source"])
        tgt_label = nodes.get(edge["target"], edge["target"])
        console.print(f"{src_label} --> {tgt_label}")

@app.command("show")
def show_discovery_file(
    ascii: bool = typer.Option(False, "--ascii", help="Print ASCII topology"),
    png: bool = typer.Option(False, "--png", help="Export PNG"),
    discovery: str = typer.Option(None, "--discovery", "-d", help="Path to discovery.json"),
):
    """
    📂 Show or export a saved network topology discovery file.
    """
    discovery_file = find_discovery_file(discovery)
    console.print(f"[green]Using:[/green] {discovery_file}")

    with open(discovery_file, "r") as f:
        data = json.load(f)

    if ascii:
        print_ascii_graph(data)

    if png:
        topo = TopologyGraph(discovery_file)
        topo.export_png()

    if not ascii and not png:
        console.print("[yellow]⚠️ No output specified. Use --ascii or --png.[/yellow]")

@app.command("live")
def live_topology(
    export: bool = typer.Option(True, "--export", help="Export PNG to file"),
    ascii: bool = typer.Option(True, "--ascii", help="Print live topology tree"),
):
    """
    🧠 Generate topology from live AppContext and optionally export/print.
    """
    console.print("[cyan]⏳ Building live topology from AppContext...[/cyan]")
    topo = TopologyGraph.build_from_context()

    if ascii:
        topo.print_ascii()

    if export:
        topo.export_png()
        console.print("[green]✅ PNG export complete.[/green]")

if __name__ == "__main__":
    app()
# Run the CLI app
    typer.run(app)
# This allows the script to be run directly from the command line.
# It will invoke the Typer CLI application defined above.
# If you want to run this as a module, you can use:
# python -m src.cli.graph
# or simply:
# python src/cli/graph.py
# This will execute the Typer app and allow you to use the defined commands.
