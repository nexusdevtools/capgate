# capgate/cli/graphs.py — CLI interface for CapGate topology graph visualization

import typer
from pathlib import Path
import json
from rich.console import Console

from core.graphs.topology import TopologyGraph

# Initialize the CLI app and rich console
app = typer.Typer(help="🧠 CapGate Network Topology Graph Commands")
console = Console()

# Default discovery.json search paths (adjustable per environment)
DEFAULT_DISCOVERY_PATHS = [
    Path("data/topology/discovery.json"),
    Path("capgate/data/topology/discovery.json"),
    Path("src/data/topology/discovery.json"),
    Path("/home/nexus/capgate/data/topology/discovery.json"),
]

def find_discovery_file(custom_path: str = None) -> Path:
    """
    Search for discovery.json across common fallback paths or use a user-defined path.
    """
    if custom_path:
        path = Path(custom_path)
        if path.exists():
            return path.resolve()
        console.print(f"[red]❌ Specified discovery file not found: {custom_path}[/red]")
        raise typer.Exit(1)

    for path in DEFAULT_DISCOVERY_PATHS:
        if path.exists():
            return path.resolve()

    console.print("[red]❌ discovery.json not found in default locations.[/red]")
    raise typer.Exit(1)

def print_ascii_graph(data: dict):
    """
    Render a basic ASCII view of nodes and edges from topology JSON.
    """
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
    ascii: bool = typer.Option(False, "--ascii", help="Print topology in ASCII"),
    png: bool = typer.Option(False, "--png", help="Export topology as PNG image"),
    discovery: str = typer.Option(None, "--discovery", "-d", help="Path to discovery.json"),
):
    """
    📂 Show or export a saved discovery topology from JSON.
    """
    discovery_file = find_discovery_file(discovery)
    console.print(f"[green]✔ Using discovery file:[/green] {discovery_file}")

    with open(discovery_file, "r") as f:
        data = json.load(f)

    if ascii:
        print_ascii_graph(data)

    if png:
        topo = TopologyGraph(discovery_file)
        topo.export_png()

    if not ascii and not png:
        console.print("[yellow]⚠️ No output option specified. Use --ascii or --png.[/yellow]")

@app.command("live")
def live_topology(
    export: bool = typer.Option(True, "--export", help="Export PNG to file"),
    ascii: bool = typer.Option(True, "--ascii", help="Print live topology tree"),
):
    """
    🧠 Generate topology from live AppContext memory and optionally render/export it.
    """
    console.print("[cyan]⏳ Building topology from live memory...[/cyan]")
    topo = TopologyGraph.build_from_context()

    if ascii:
        topo.print_ascii()

    if export:
        topo.export_png()
        console.print("[green]✅ PNG export complete.[/green]")

if __name__ == "__main__":
    app()
