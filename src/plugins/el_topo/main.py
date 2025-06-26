import subprocess
import re
from typing import List, Tuple
import time
from core.debug_tools import debug_var, dump_context, print_exception
from core.context import AppContext
from core.logger import logger
from core.graphs.topology import TopologyGraph
from db.schemas.device import Device


def parse_arp_table() -> List[Tuple[str, str]]:
    """
    Uses `arp -an` to parse IP-MAC pairs from local ARP table.
    Returns:
        List of (ip, mac) tuples for discovered devices.
    """
    result = subprocess.run(["arp", "-an"], capture_output=True, text=True)
    discovered: List[Tuple[str, str]] = []

    for line in result.stdout.splitlines():
        match = re.search(r"\((.*?)\) at ([\w:]+)", line)
        if match:
            ip, mac = match.groups()
            if mac != "00:00:00:00:00:00":
                discovered.append((ip, mac))
    return discovered


def inject_devices_into_context(ctx: AppContext, pairs: list[tuple[str, str]]):
    """
    Takes a list of IP-MAC pairs and injects them into AppContext.
    """
    for ip, mac in pairs:
        try:
            device = Device(
                mac=mac,
                ip=ip,
                hostname=None,
                vendor="Unknown",
                signal_strength=None,
                is_router=False,
                last_seen=None,
            )
            ctx.update("device", mac, device.model_dump())
            ctx.set(f"device:{mac}", device.model_dump())
            ctx.set(f"device:{mac}:ip", ip)
            ctx.set(f"device:{mac}:hostname", None)
            ctx.set(f"device:{mac}:vendor", "Unknown")
            ctx.set(f"device:{mac}:signal_strength", None)
            ctx.set(f"device:{mac}:is_router", False)
            ctx.set(f"device:{mac}:last_seen", time.time()) 
            logger.debug(f"[el_topo] Added device to context: {mac} ({ip})")
        except Exception as e:
            logger.warning(f"[el_topo] Failed to inject device {mac}: {e}")


# --- MAIN ENTRY POINT ---
def run(app_context: AppContext, *plugin_args: str):
    """
    Plugin entry point. Follows CapGate plugin structure convention.
    Args:
        app_context (AppContext): Global context shared across CapGate
        plugin_args (tuple[str]): Optional CLI args passed to the plugin
    """
    try:
        logger.info("🌐 Running el_topo: Topology Discovery Plugin...")

        debug_var(app_context, "app_context")
        debug_var(plugin_args, "plugin_args")
        dump_context(app_context)

        arp_entries = parse_arp_table()
        inject_devices_into_context(app_context, arp_entries)

        topo = TopologyGraph.build_from_context()
        topo.export_png()

        logger.info("✅ el_topo: Topology discovery completed and exported.")
    except Exception as e:
        print_exception(e)
        logger.error(f"❌ el_topo: An error occurred during execution: {e}")
        return False
    return True
# --- END OF MAIN ENTRY POINT ---
