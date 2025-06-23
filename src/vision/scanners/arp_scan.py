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

    # Construct ARP request packet
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    arp = ARP(pdst=target_range)
    packet = ether / arp

    # Send and receive ARP replies
    result = srp(packet, iface=interface, timeout=3, verbose=False)[0]
    devices: List[Dict[str, str]] = []  # Ensure this is a list, not mistakenly used elsewhere

    # Collect discovered devices
    for _, received in result:
        devices.append({
            "ip": received.psrc,
            "mac": received.hwsrc
        })

    logger.info(f"Discovered {len(devices)} device(s)")
    return devices
from typing import Optional

def arp_scan_single_ip(interface: str, target_ip: str) -> Dict[str, Optional[str]]:
    """
    Scans a single IP address for its MAC address using ARP.
    Args:
        interface (str): The network interface to use (e.g., "wlan0").
        target_ip (str): The target IP address to scan.
    Returns:
        Dict[str, Optional[str]]: A dictionary with the target IP and its MAC address.
    """
    logger.info(f"Scanning single IP {target_ip} via {interface}...")

    # Construct ARP request packet
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    arp = ARP(pdst=target_ip)
    packet = ether / arp

    # Send and receive ARP reply
    result = srp(packet, iface=interface, timeout=3, verbose=False)[0]

    if result:
        received = result[0][1]
        device_info = {
            "ip": received.psrc,
            "mac": received.hwsrc
        }
        logger.info(f"Discovered device: {device_info}")
        return device_info
    else:
        logger.warning(f"No response from {target_ip}")
        return {"ip": target_ip, "mac": None}
from typing import Optional

def arp_scan_multiple_ips(interface: str, target_ips: List[str]) -> List[Dict[str, Optional[str]]]:
    """
    Scans multiple IP addresses for their MAC addresses using ARP.
    
    Args:
        interface (str): The network interface to use (e.g., "wlan0").
        target_ips (List[str]): List of target IP addresses to scan.
        
    Returns:
        List[Dict[str, Optional[str]]]: A list of dictionaries with IP and MAC addresses.
    """
    logger.info(f"Scanning multiple IPs {target_ips} via {interface}...")

    devices: List[Dict[str, Optional[str]]] = []

    for ip in target_ips:
        device_info = arp_scan_single_ip(interface, ip)
        devices.append(device_info)

    return devices

def arp_scan_from_file(interface: str, file_path: str) -> List[Dict[str, Optional[str]]]:
    """
    Scans IP addresses listed in a file for their MAC addresses using ARP.
    Args:
        interface (str): The network interface to use (e.g., "wlan0").
        file_path (str): Path to the file containing IP addresses, one per line.
    Returns:
        List[Dict[str, Optional[str]]]: A list of dictionaries with IP and MAC addresses.
    """
    devices: List[Dict[str, Optional[str]]] = []

    try:
        with open(file_path, 'r') as f:
            target_ips = [line.strip() for line in f if line.strip()]
        
        devices = arp_scan_multiple_ips(interface, target_ips)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")

    return devices
