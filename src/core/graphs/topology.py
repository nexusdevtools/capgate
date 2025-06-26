# capgate/core/graphs/topology.py — CapGate Core Graph Engine
"""
Builds and manages CapGate’s internal network topology graphs.
Supports JSON import/export, in-memory graphing from AppContext,
and ASCII or PNG output for terminal or GUI clients.
"""

import json
import os
import ipaddress
from typing import List, Dict, Any

import networkx as nx
import matplotlib.pyplot as plt
from rich.console import Console
from rich.tree import Tree

from networkx import Graph  # Add this import for type hinting

from core.state_management.context import get_context
from core.debug_tools import dump_context, print_exception
class TopologyGraph:
    """Class for managing CapGate network topologies."""

    def __init__(self, json_file: str):
        self.console: Console = Console()
        self.graph: nx.Graph = nx.Graph()  # Use explicit Graph type for type checker
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, str]] = []
        self._load(json_file)
        self.edges: List[Dict[str, str]] = []
        self._load(json_file)

    def _load(self, path: str) -> None:
        """Load topology from JSON file and populate graph."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Graph source not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.nodes = data.get("nodes", [])
            self.edges = data.get("edges", [])

        for node in self.nodes:
            node_id = node["id"]
            node_attrs = {k: v for k, v in node.items() if k != "id"}
            print(f"🔧 Adding node: id={node_id}, attrs={node_attrs}")
            print(f"🔎 self.graph is instance of: {type(self.graph)}")
            self.graph.add_node(node_id, **node_attrs)

        for edge in self.edges:
            self.graph.add_edge(edge["source"], edge["target"], **edge)

    def print_ascii(self) -> None:
        """Print a basic tree representation of the topology."""
        tree = Tree("[bold cyan]CapGate Network Topology")
        for node_id, attrs in self.graph.nodes(data=True):
            label = attrs.get("label", node_id)
            tree.add(f"[green]{label}")
        self.console.print(tree)

    def export_png(self, out_path: str = "exports/topology.png") -> None:
        """Export the current graph to a PNG file."""
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        self.console.print(
            f"[blue]Exporting graph:[/] {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges"
        )

        if not self.graph.nodes:
            self.console.print("[red]❌ No nodes found in graph. Export aborted.[/red]")
            return

        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.graph, seed=42)

        labels = nx.get_node_attributes(self.graph, 'label')
        nx.draw_networkx(
            self.graph,
            pos,
            labels=labels,
            node_color="skyblue",
            edge_color="gray",
            node_size=2000,
            font_size=10
        )
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(out_path)
        self.console.print(f"[bold green]✅ Exported topology PNG to:[/] {out_path}")

    @classmethod
    def build_from_context(cls) -> "TopologyGraph":
        """
        Build a TopologyGraph from live CapGateContext memory.
        Pulls interface and device data from shared context state.
        Returns:
            TopologyGraph: An instance of the graph built from context.
        """
        console = Console()
        try:
            ctx = get_context()
            dump_context(ctx, "CapGateContext (build_from_context)")

            graph = cls.__new__(cls)
            graph.console = console
            graph.graph = nx.Graph()
            graph.nodes = []
            graph.edges = []

            interfaces: List[Dict[str, Any]] = ctx.get("interfaces", [])
            console.print(f"[blue]🧪 Found {len(interfaces)} interfaces in context.[/blue]")

            # FIXED: Access AppState variables safely via __dict__
            devices: List[Dict[str, Any]] = [
                val for key, val in ctx.state.__dict__.items()
                if isinstance(key, str)
                and key.startswith("device:")
                and isinstance(val, dict)
                and "mac" in val
                and "ip" in val
            ]
            console.print(f"[blue]🧪 Found {len(devices)} devices in context.[/blue]")

            # Add interfaces as nodes
            for iface in interfaces:
                name = iface.get("name")
                if not name:
                    continue
                label = f"{name} ({iface.get('type', 'unknown')})"
                graph.graph.add_node(name, label=label, **iface)
                graph.nodes.append({"id": name, "label": label})

            # Add devices and connect to interfaces if IPs match
            for dev in devices:
                mac = dev.get("mac")
                if not mac:
                    continue
                label = dev.get("hostname") or dev.get("ip") or mac
                graph.graph.add_node(mac, label=f"Device: {label}", **dev)
                graph.nodes.append({"id": mac, "label": f"Device: {label}"})

                dev_ip = dev.get("ip")
                if not dev_ip:
                    continue

                for iface in interfaces:
                    iface_ip = iface.get("ip")
                    try:
                        if iface_ip and ipaddress.ip_address(dev_ip) in ipaddress.ip_network(iface_ip, strict=False):
                            graph.graph.add_edge(iface["name"], mac)
                            graph.edges.append({"source": iface["name"], "target": mac})
                    except Exception:
                        continue  # Ignore bad IP formats

            if not graph.nodes:
                console.print("[red]⚠ No nodes found in context. Nothing to draw.[/red]")
            elif not graph.edges:
                console.print("[yellow]⚠ Nodes exist, but no edges — check device-interface links.[/yellow]")

            return graph

        except Exception as e:
            print_exception(e)
            raise

        finally:
            console.print("[bold blue]Topology graph built from context.[/bold blue]")
            console.print(f"[blue]Nodes:[/] {len(graph.nodes)}, [blue]Edges:[/] {len(graph.edges)}")
            console.print("[bold blue]Ready to use in-memory topology graph.[/bold blue]")
            dump_context(ctx, "CapGateContext (build_from_context) - end")
