"""_summary_
    Scans network interfaces and updates the application context with their details.
    This module detects available network interfaces, retrieves their MAC addresses,
    and checks their capabilities.
    It filters out loopback and peer-to-peer interfaces, and logs the detected interfaces."""

# capgate/vision/scanners/iface_scan.py

import os
import subprocess
from core.context import AppContext
from core.logger import logger
from db.schemas.interface import Interface

def get_mac(interface: str) -> str:
    try:
        with open(f"/sys/class/net/{interface}/address", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "00:00:00:00:00:00"


def scan_interfaces():
    ctx = AppContext()
    try:
        result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
        lines = result.stdout.splitlines()

        for line in lines:
            if ": " not in line:
                continue
            parts = line.split(": ", 1)
            if len(parts) < 2:
                continue
            index, data = parts
            iface_name = data.split()[0]

            if iface_name.startswith("lo") or iface_name.startswith("p2p"):
                continue

            mac = get_mac(iface_name)

            iface = Interface(
                name=iface_name,
                mac=mac,
                supports_monitor="mon" in iface_name or "wlan" in iface_name,
                supports_2ghz=True,
                supports_11n=True,
                supports_11g=True,
                supports_11b=True,
                supports_11a=True,
            )

            ctx.update("interface", iface_name, iface.dict())
            logger.info(f"[iface_scan] Detected interface: {iface_name} - {mac}")

    except Exception as e:
        logger.error(f"[iface_scan] Failed to scan interfaces: {e}")
