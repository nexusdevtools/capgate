# capgate/plugins/topology_discovery/main.py

from core.context import AppContext
from core.logger import logger
from core.graphs.topology import TopologyGraph
from db.schemas.device import Device
import subprocess
import re

class TopologyDiscovery:
    """
    Plugin: Topology Discovery
    --------------------------
    - Parses ARP table
    - Detects live hosts
    - Links them to current interfaces
    - Pushes live results to AppContext
    - Generates a real-time topology graph
    """

    def __init__(self):
        self.ctx = AppContext()

    def parse_arp(self):
        result = subprocess.run(["arp", "-an"], capture_output=True, text=True)
        discovered = []

        for line in result.stdout.splitlines():
            match = re.search(r"\((.*?)\) at ([\w:]+)", line)
            if match:
                ip, mac = match.groups()
                if mac != "00:00:00:00:00:00":
                    discovered.append((ip, mac))
        return discovered

    def inject_devices(self, pairs):
        for ip, mac in pairs:
            device = Device(
                mac=mac,
                ip=ip,
                hostname=None,
                vendor="Unknown",
                signal_strength=None,
                is_router=False,
                last_seen=None,
            )
            self.ctx.update("device", mac, device.dict())

    def run(self):
        logger.info("🌐 Running Topology Discovery Plugin...")
        arp_entries = self.parse_arp()
        self.inject_devices(arp_entries)
        TopologyGraph.build_from_context().export_png()
        logger.info("✅ Topology discovery completed and exported.")

# --- THIS IS THE REQUIRED ENTRY POINT ---
def run(*args, **kwargs):
    """
    Top-level entry point for the plugin system.
    """
    TopologyDiscovery().run()

if __name__ == "__main__":
    run()