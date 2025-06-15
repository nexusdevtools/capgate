# capgate/vision/scanners/arp_scan.py

from typing import List, Dict
from scapy.layers.l2 import ARP, Ether
from scapy.all import srp

from core.logger import get_logger

logger = get_logger("vision.scanners.arp_scan")


def arp_scan(interface: str, target_range: str = "192.168.1.0/24") -> List[Dict[str, str]]:
    """
    Scans the given IP range for live devices using ARP.

    Args:
        interface (str): The network interface to use (e.g., "wlan0").
        target_range (str): The IP/CIDR range to scan (default is 192.168.1.0/24).

    Returns:
        List[Dict[str, str]]: A list of discovered device info dictionaries.
    """
    logger.info(f"Starting ARP scan on {target_range} via {interface}...")

    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    arp = ARP(pdst=target_range)
    packet = ether / arp

    result = srp(packet, iface=interface, timeout=3, verbose=False)[0]

    devices = []
    for sent, received in result:
        devices.append({
            "ip": received.psrc,
            "mac": received.hwsrc
        })

    logger.info(f"Discovered {len(devices)} device(s)")
    return devices
