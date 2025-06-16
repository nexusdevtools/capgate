import typer
from pathlib import Path
import json
from rich.console import Console

app = typer.Typer(help="Network topology graph commands")
console = Console()

# Your discovery file fallback paths (relative to where CLI is run)
DEFAULT_DISCOVERY_PATHS = [
    Path("data/topology/discovery.json"),
    Path("capgate/data/topology/discovery.json"),
    Path("src/data/topology/discovery.json"),
    Path("/home/nexus/capgate/data/topology/discovery.json"),  # Absolute fallback
]

def find_discovery_file(custom_path: str = None) -> Path:
    if custom_path:
        path = Path(custom_path)
        if path.exists():
            return path.resolve()
        else:
            console.print(f"[red]Specified discovery file not found: {custom_path}[/red]")
            raise typer.Exit(1)
    for path in DEFAULT_DISCOVERY_PATHS:
        if path.exists():
            return path.resolve()
    console.print("[red]discovery.json not found in default locations.[/red]")
    raise typer.Exit(1)

def print_ascii_graph(data: dict):
    """
    Simple ASCII graph rendering for discovery data with nodes and edges.
    """
    nodes = {node["id"]: node.get("label", node["id"]) for node in data.get("nodes", [])}
    edges = data.get("edges", [])

    console.print("[green]ASCII Network Topology Graph:[/green]\n")
    # Print nodes
    for node_id, label in nodes.items():
        console.print(f"• {label} ({node_id})")
    console.print("\n[blue]Connections:[/blue]")
    # Print edges
    for edge in edges:
        src_label = nodes.get(edge["source"], edge["source"])
        tgt_label = nodes.get(edge["target"], edge["target"])
        console.print(f"{src_label} --> {tgt_label}")

@app.command()
def show(
    ascii: bool = typer.Option(False, "--ascii", help="Show ASCII graph"),
    png: bool = typer.Option(False, "--png", help="Export graph as PNG"),
    discovery: str = typer.Option(None, "--discovery", "-d", help="Path to discovery.json"),
):
    """
    Show or export the network topology graph.
    """
    discovery_file = find_discovery_file(discovery)
    console.print(f"[green]Using discovery file:[/green] {discovery_file}")

    with open(discovery_file, "r") as f:
        data = json.load(f)

    if ascii:
        print_ascii_graph(data)

    if png:
        console.print("[yellow]PNG export is not implemented yet.[/yellow]")

    if not ascii and not png:
        console.print("[yellow]No output option specified. Use --ascii or --png.[/yellow]")

if __name__ == "__main__":
    app()
