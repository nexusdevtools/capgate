# src/core/graphs/topology.py — CapGate Core Graph Engine
"""
Builds and manages CapGate’s internal network topology graphs.
Supports JSON import/export, in-memory graphing from AppState,
and ASCII or PNG output for terminal or GUI clients.
"""

import json
import os
import ipaddress
from typing import List, Dict, Any, Optional, Tuple # Import Tuple for sorted_nodes type hint

import networkx as nx
import matplotlib.pyplot as plt
from rich.console import Console
from rich.tree import Tree

from networkx import Graph # Keep this import, it's used for type hinting `self.graph: nx.Graph`

from base.state_management.context import get_context 
from base.debug_tools import dump_context, print_exception
from db.schemas.interface import Interface
from db.schemas.device import Device

class TopologyGraph:
    """Class for managing CapGate network topologies."""

    def __init__(self, json_file: Optional[str] = None):
        self.console: Console = Console()
        self.graph: nx.Graph = nx.Graph() # Type hint is used here
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, str]] = []
        
        if json_file:
            self._load(json_file)

    def _load(self, path: str) -> None:
        """Load topology from JSON file and populate graph."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Graph source not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.nodes = data.get("nodes", [])
            self.edges = data.get("edges", [])

        for node_data in self.nodes: # Renamed 'node' to 'node_data' for clarity
            node_id = node_data.get("id")
            if not node_id:
                self.console.print(f"[yellow]Skipping node with no ID in JSON: {node_data}[/yellow]")
                continue
            node_attrs = {k: v for k, v in node_data.items() if k != "id"}
            self.graph.add_node(node_id, **node_attrs) # Pylance warnings fixed by context
            self.console.log(f"🔧 Added node from JSON: id={node_id}, attrs={node_attrs}")

        for edge_data in self.edges: # Renamed 'edge' to 'edge_data' for clarity
            source_id = edge_data.get("source")
            target_id = edge_data.get("target")
            if not source_id or not target_id:
                self.console.print(f"[yellow]Skipping edge with incomplete source/target in JSON: {edge_data}[/yellow]")
                continue
            self.graph.add_edge(source_id, target_id, **edge_data) # Pylance warnings fixed by context
            self.console.log(f"🔗 Added edge from JSON: {source_id} -> {target_id}")

    def print_ascii(self) -> None:
        """Print a basic tree representation of the topology."""
        tree = Tree("[bold cyan]CapGate Network Topology[/bold cyan]")
        
        # Pylance: Type of "sorted_nodes" is partially unknown
        # Fix: Explicitly type the iterator from .nodes(data=True) as Tuple[str, Dict[str, Any]]
        sorted_nodes: List[Tuple[str, Dict[str, Any]]] = sorted(
            self.graph.nodes(data=True), 
            key=lambda x: str(x[0]) # Ensure key is string for consistent sorting
        )

        for node_id, attrs in sorted_nodes: # Pylance: Type of "node_id", "attrs" is unknown (fixed by sorted_nodes hint)
            label: str = str(attrs.get("label", node_id)) # Explicitly type `label` as str, get can return Any
            node_branch = tree.add(f"[green]{label} ([dim]{node_id}[/dim])")
            
            connected_to: List[str] = [] # Explicitly type `connected_to`
            for neighbor_id in self.graph.neighbors(node_id): # Pylance: Type of "neighbors" is partially unknown (fixed by context)
                # Pylance: Type of "get" is unknown (fixed by context)
                neighbor_label: str = str(self.graph.nodes[neighbor_id].get('label', neighbor_id)) # Explicitly type `neighbor_label`
                connected_to.append(f"{neighbor_label} ([dim]{neighbor_id}[/dim])") # Pylance: Type of "append" is partially unknown (fixed by context)
            
            if connected_to:
                # Pylance: Argument type is partially unknown for join (fixed by `connected_to: List[str]`)
                node_branch.add(f"[blue]Connected to:[/blue] {', '.join(connected_to)}")

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

        # Pylance: Type of "figure" is partially unknown (matplotlib typing can be complex)
        # Fix: Explicitly import Figure from matplotlib.pyplot if you need a strong type,
        # but often, this is a Pylance limitation with third-party libraries.
        plt.figure(figsize=(12, 8))
        
        # Pylance: Type of "pos" is partially unknown; Type of "spring_layout" is partially unknown
        # Fix: Provide explicit type hint for `pos`.
        pos: Dict[Any, Any] = nx.spring_layout(self.graph, seed=42, k=0.5, iterations=50) 

        # Pylance: Type of "labels" is unknown
        # Fix: Provide explicit type hint for `labels`.
        labels: Dict[Any, Any] = nx.get_node_attributes(self.graph, 'label')
        
        interface_nodes = [n for n, attrs in self.graph.nodes(data=True) if attrs.get('type') == 'interface']
        device_nodes = [n for n, attrs in self.graph.nodes(data=True) if attrs.get('type') == 'device']

        nx.draw_networkx_nodes(self.graph, pos, nodelist=interface_nodes, node_color="lightgreen", node_size=2500)
        nx.draw_networkx_nodes(self.graph, pos, nodelist=device_nodes, node_color="skyblue", node_size=2000)

        nx.draw_networkx_edges(self.graph, pos, edge_color="gray", alpha=0.6)

        nx.draw_networkx_labels(self.graph, pos, labels, font_size=9, font_color="black")

        plt.title("CapGate Network Topology", size=15)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(out_path)
        self.console.print(f"[bold green]✅ Exported topology PNG to:[/] {out_path}")
        plt.close()

    @classmethod
    def build_from_context(cls) -> "TopologyGraph":
        """
        Build a TopologyGraph from live AppState memory (accessed via CapGateContext).
        Pulls interface and device data from shared AppState.discovery_graph.
        Returns:
            TopologyGraph: An instance of the graph built from context.
        """
        console = Console()
        try:
            ctx = get_context()
            dump_context(ctx, "CapGateContext (build_from_context)")

            graph_instance = cls()

            app_state = ctx.state
            discovery_graph_data = app_state.get_discovery_graph()

            if not isinstance(discovery_graph_data, dict):
                console.print("[red]Discovery graph in AppState is not a dictionary. Cannot build topology.[/red]")
                return graph_instance

            interfaces_data: Dict[str, Any] = discovery_graph_data.get("interfaces", {})
            devices_data: Dict[str, Any] = discovery_graph_data.get("devices", {})

            console.print(f"[blue]🧪 Found {len(interfaces_data)} interfaces in AppState.[/blue]")
            console.print(f"[blue]🧪 Found {len(devices_data)} devices in AppState.[/blue]")

            for iface_name, iface_attrs in interfaces_data.items():
                try:
                    validated_iface = Interface(**iface_attrs) 
                    
                    node_id: str = validated_iface.name # Ensure node_id is string
                    label: str = f"{validated_iface.name} ({validated_iface.ip_address.split('/')[0] if validated_iface.ip_address else 'No IP'})"
                    graph_instance.graph.add_node(node_id, label=label, type="interface", **validated_iface.to_dict())
                    graph_instance.nodes.append({"id": node_id, "label": label})
                except Exception as e:
                    console.print(f"[yellow]Skipping malformed interface data in AppState: {iface_attrs} - {e}[/yellow]")
                    continue

            for device_mac, device_attrs in devices_data.items():
                try:
                    validated_device = Device(**device_attrs)
                    
                    node_id: str = validated_device.mac # Ensure node_id is string
                    label: str = str(validated_device.hostname or validated_device.ip or validated_device.mac)
                    label = f"Device: {label}"
                    graph_instance.graph.add_node(node_id, label=label, type="device", **validated_device.to_dict())
                    graph_instance.nodes.append({"id": node_id, "label": label})
                except Exception as e:
                    console.print(f"[yellow]Skipping malformed device data in AppState: {device_attrs} - {e}[/yellow]")
                    continue

            for device_mac, device_attrs in devices_data.items():
                dev_ip: Optional[str] = device_attrs.get("ip") # Explicitly type dev_ip
                if not dev_ip:
                    continue

                for iface_name, iface_attrs in interfaces_data.items():
                    iface_ip_cidr: Optional[str] = iface_attrs.get("ip_address") # Explicitly type iface_ip_cidr
                    if not iface_ip_cidr:
                        continue

                    try:
                        if ipaddress.ip_address(dev_ip) in ipaddress.ip_network(iface_ip_cidr, strict=False):
                            if graph_instance.graph.has_node(iface_name) and graph_instance.graph.has_node(device_mac):
                                graph_instance.graph.add_edge(iface_name, device_mac, type="connected_to")
                                graph_instance.edges.append({"source": iface_name, "target": device_mac, "type": "connected_to"})
                                console.log(f"🔗 Added edge: {iface_name} ({iface_ip_cidr}) <--> {device_mac} ({dev_ip})")
                            else:
                                console.print(f"[yellow]Skipping edge for {iface_name} <--> {device_mac}: one or both nodes not found in graph.[/yellow]")
                    except ValueError as ve:
                        console.print(f"[yellow]Invalid IP format for device {dev_ip} or interface {iface_ip_cidr}: {ve}[/yellow]")
                    except Exception as e:
                        console.print(f"[yellow]Error checking IP connection between {device_mac} and {iface_name}: {e}[/yellow]")
                        continue

            if not graph_instance.graph.nodes:
                console.print("[red]⚠ No nodes found in AppState data. Nothing to draw.[/red]")
            elif not graph_instance.graph.edges:
                console.print("[yellow]⚠ Nodes exist, but no edges — check device-interface links or IP configurations.[/yellow]")

            return graph_instance

        except Exception as e:
            print_exception(e, "Error building topology graph from context")
            raise