# topology.py — CapGate Core Graph Engine

import json
import os
import networkx as nx
from rich import print
from rich.console import Console
from rich.tree import Tree
import matplotlib.pyplot as plt

class TopologyGraph:
    def __init__(self, json_file: str):
        self.console = Console()
        self.graph = nx.Graph()
        self.nodes = []
        self.edges = []
        self._load(json_file)

    def _load(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Graph source not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)
            self.nodes = data.get("nodes", [])
            self.edges = data.get("edges", [])

        for node in self.nodes:
            self.graph.add_node(node["id"], **node)
        for edge in self.edges:
            self.graph.add_edge(edge["source"], edge["target"], **edge)

    def print_ascii(self):
        tree = Tree("[bold cyan]CapGate Network Topology")
        for node in self.graph.nodes(data=True):
            tree.add(f"[green]{node[1].get('label', node[0])}")
        self.console.print(tree)

    def export_png(self, out_path="exports/topology.png"):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, with_labels=True, node_color="lightblue", edge_color="gray")
        plt.savefig(out_path)
        self.console.print(f"[bold green]Exported topology to:[/] {out_path}")

    def launch_tui(self):
        # Placeholder for future textual/urwid implementation
        self.console.print("[yellow]TUI mode not yet implemented — coming soon!")
