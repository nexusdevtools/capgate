# topology.py — CapGate Core Graph Engine

import json
import os
import networkx as nx
from rich.console import Console
from rich.tree import Tree
import matplotlib.pyplot as plt

from core.context import AppContext

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


    @classmethod
    def build_from_context(cls) -> "TopologyGraph":
        """
        Dynamically generate a topology graph based on current AppContext data.
        """
        ctx = AppContext()
        graph = cls.__new__(cls)  # Create uninitialized instance
        graph.console = Console()
        graph.graph = nx.Graph()
        graph.nodes = []
        graph.edges = []

        # Add interface nodes
        for name, iface in ctx.interfaces.items():
            graph.graph.add_node(name, label=f"Interface: {name}", **iface)
            graph.nodes.append({"id": name, "label": f"{name} ({iface.get('type', 'unknown')})"})

        # Add device nodes (TODO: this will expand with ARP or DHCP data)
        for device in ctx.devices:
            mac = device.get("mac")
            if not mac:
                continue
            if not isinstance(mac, str):
                mac = mac.hex()
            if not mac:
                continue
            if not mac.startswith("00:"):
                mac = ":".join(mac[i:i+2] for i in range(0, len(mac), 2))
            if not mac:
                continue
            if mac in graph.graph:
                continue
            # Use hostname or IP as label if available
            if not isinstance(device, dict):
                device = device.dict()
            if not isinstance(device, dict):
                device = device.__dict__
            if "hostname" not in device:
                device["hostname"] = None
            if "ip" not in device:
                device["ip"] = None
            if "vendor" not in device:
                device["vendor"] = None
            if "signal_strength" not in device:
                device["signal_strength"] = None
            if "is_router" not in device:
                device["is_router"] = False
            if "last_seen" not in device:
                device["last_seen"] = 0
            if "type" not in device:
                device["type"] = "unknown"
            if "name" not in device:
                device["name"] = f"Device {mac}"
            if "ip" in device and not isinstance(device["ip"], str):
                device["ip"] = device["ip"].split("/")[0]
            if "mac" not in device:
                device["mac"] = mac
            if "name" not in device:
                device["name"] = f"Device {mac}"
            if "label" not in device:
                device["label"] = f"Device {mac}"
            if "type" not in device:
                device["type"] = "unknown"
            if "last_seen" not in device:
                device["last_seen"] = 0
            label = device.get("hostname") or device.get("ip") or mac
            graph.graph.add_node(mac, label=f"Device: {label}", **device)
            graph.nodes.append({"id": mac, "label": label})

            # Link device to known interface if IP overlaps
            for iface in ctx.interfaces.values():
                if "ip" in iface and iface["ip"].split("/")[0] == device.get("ip"):
                    graph.graph.add_edge(iface["name"], mac)
                    graph.edges.append({"source": iface["name"], "target": mac})

        return graph