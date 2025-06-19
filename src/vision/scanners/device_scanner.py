# capgate/vision/scanners/device_scan.py

import time
import subprocess
from typing import List, Tuple
from core.context import AppContext
from core.logger import logger
from db.schemas.device import Device


def parse_arp_table() -> List[Tuple[str, str]]:
    """
    Uses `arp -an` to get IP/MAC pairs seen by the host.
    """
    result = subprocess.run(["arp", "-an"], capture_output=True, text=True)
    devices = []
    for line in result.stdout.strip().splitlines():
        if "incomplete" in line.lower():
            continue
        parts = line.split()
        if len(parts) >= 4:
            ip = parts[1].strip("()")
            mac = parts[3]
            devices.append((mac, ip))
    return devices


def scan_devices():
    ctx = AppContext()
    entries = parse_arp_table()

    for mac, ip in entries:
        if mac == "00:00:00:00:00:00":
            continue

        device = Device(
            mac=mac,
            vendor=None,  # TODO: Lookup via MAC DB
            signal_strength=None,
            is_router=False,
            last_seen=time.time(),
        )
        ctx.update("device", mac, device.dict())
        logger.info(f"[device_scan] Detected device: {mac} ({ip})")


if __name__ == "__main__":
    scan_devices()
