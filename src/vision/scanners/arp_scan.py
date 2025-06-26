# src/vision/scanners/arp_scan.py

from typing import List, Dict, Optional
from scapy.layers.l2 import ARP, Ether
from scapy.all import srp # srp is the send-receive function in Scapy

# Assuming get_logger is replaced by direct logger instance from core.logger
from core.logger import logger # <--- Updated import for logger


def arp_scan(interface: str, target_range: str = "192.168.1.0/24") -> List[Dict[str, str]]:
    """
    Scans the given IP range for live devices using ARP.

    Args:
        interface (str): The network interface to use (e.g., "wlan0").
        target_range (str): The IP/CIDR range to scan (default is 192.168.1.0/24).

    Returns:
        List[Dict[str, str]]: A list of discovered device info dictionaries,
                               each with "ip" and "mac" keys.
    """
    logger.info(f"[arp_scan] Starting ARP scan on {target_range} via {interface}...")

    # Construct ARP request packet
    ether_packet = Ether(dst="ff:ff:ff:ff:ff:ff") # Explicitly type
    arp_packet = ARP(pdst=target_range) # Explicitly type
    packet = ether_packet / arp_packet

    try:
        # Send and receive ARP replies
        # result is a tuple: (answered_packets, unanswered_packets)
        # We only care about answered_packets here.
        answered_packets, _ = srp(packet, iface=interface, timeout=3, verbose=False) # Use _ for unanswered
        
        devices: List[Dict[str, str]] = [] # Explicitly type list content

        # Collect discovered devices
        # received is a Scapy packet object. psrc and hwsrc are string attributes.
        for _, received in answered_packets: # Ignore 'sent' as it is unused
            devices.append({
                "ip": str(received.psrc),  # Ensure string type
                "mac": str(received.hwsrc) # Ensure string type
            })

        logger.info(f"[arp_scan] Discovered {len(devices)} device(s) on {interface}.")
        return devices
    except PermissionError:
        logger.error(f"[arp_scan] Permission denied for Scapy on {interface}. Try running as root or with appropriate capabilities.")
        return []
    except Exception as e:
        logger.error(f"[arp_scan] Error during ARP scan on {interface} for range {target_range}: {e}")
        return []

def arp_scan_single_ip(interface: str, target_ip: str) -> Dict[str, Optional[str]]:
    """
    Scans a single IP address for its MAC address using ARP.
    Args:
        interface (str): The network interface to use (e.g., "wlan0").
        target_ip (str): The target IP address to scan.
    Returns:
        Dict[str, Optional[str]]: A dictionary with the target IP and its MAC address (or None).
    """
    logger.info(f"[arp_scan] Scanning single IP {target_ip} via {interface}...")

    ether_packet = Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_packet = ARP(pdst=target_ip)
    packet = ether_packet / arp_packet

    try:
        answered_packets, _ = srp(packet, iface=interface, timeout=3, verbose=False)

        if answered_packets:
            # result[0][1] is the received packet
            received = answered_packets[0][1] 
            device_info: Dict[str, Optional[str]] = {
                "ip": str(received.psrc),
                "mac": str(received.hwsrc)
            }
            logger.info(f"[arp_scan] Discovered device: {device_info}")
            return device_info
        else:
            logger.warning(f"[arp_scan] No response from {target_ip} on {interface}.")
            return {"ip": target_ip, "mac": None}
    except PermissionError:
        logger.error(f"[arp_scan] Permission denied for Scapy on {interface}. Try running as root or with appropriate capabilities.")
        return {"ip": target_ip, "mac": None}
    except Exception as e:
        logger.error(f"[arp_scan] Error scanning single IP {target_ip} on {interface}: {e}")
        return {"ip": target_ip, "mac": None}


def arp_scan_multiple_ips(interface: str, target_ips: List[str]) -> List[Dict[str, Optional[str]]]:
    """
    Scans multiple IP addresses for their MAC addresses using ARP.
    
    Args:
        interface (str): The network interface to use (e.g., "wlan0").
        target_ips (List[str]): List of target IP addresses to scan.
        
    Returns:
        List[Dict[str, Optional[str]]]: A list of dictionaries with IP and MAC addresses.
    """
    logger.info(f"[arp_scan] Scanning multiple IPs {target_ips} via {interface}...")

    devices: List[Dict[str, Optional[str]]] = []

    for ip in target_ips:
        device_info = arp_scan_single_ip(interface, ip)
        if device_info: # Ensure device_info is not None/empty
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
        with open(file_path, 'r', encoding='utf-8') as f: # Added encoding
            target_ips = [line.strip() for line in f if line.strip()]
        
        devices = arp_scan_multiple_ips(interface, target_ips)
    except FileNotFoundError:
        logger.error(f"[arp_scan] File not found: {file_path}")
    except Exception as e:
        logger.error(f"[arp_scan] Error reading file {file_path}: {e}")

    return devices