# src/vision/scanners/device_scanner.py

import time
import subprocess
from typing import List, Tuple

from core.logger import logger
from core.state_management.state import AppState # <--- CRITICAL CHANGE: Import AppState
from db.schemas.device import Device # Import your Pydantic schema

def parse_arp_table() -> List[Tuple[str, str]]:
    """
    Uses `arp -an` to get IP/MAC pairs seen by the host.
    Returns a list of (MAC, IP) tuples.
    """
    try:
        result = subprocess.run(["arp", "-an"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.debug("Command 'arp -an' failed with error: %s", result.stderr.strip())
            return []
            
        devices: List[Tuple[str, str]] = [] # Explicitly type
        for line in result.stdout.strip().splitlines():
            if "incomplete" in line.lower():
                continue
            parts = line.split()
            if len(parts) >= 4:
                ip: str = parts[1].strip("()") # Explicitly type
                mac: str = parts[3] # Explicitly type
                devices.append((mac, ip))
        return devices
    except FileNotFoundError:
        logger.warning("ARP command not found. Cannot parse ARP table.")
        return []
    except Exception as e:
        logger.error(f"Error parsing ARP table: {e}")
        return []

# <--- CRITICAL CHANGE: Renamed function and added app_state parameter
def scan_devices_from_arp_table_and_update_state(app_state: AppState):
    """
    Scans devices from the local ARP table and updates the AppState's discovery_graph.
    """
    logger.info("[device_scanner] Scanning devices from ARP table and updating AppState...")
    entries = parse_arp_table()

    # discovery_graph is always initialized in AppState.__init__, so no need to check for None

    for mac, ip in entries:
        if mac == "00:00:00:00:00:00": # Filter out zero MAC addresses
            continue

        # Create Device Pydantic model instance
        # Include IP directly from ARP table
        device_data = Device(
            mac=mac,
            ip=ip, # <--- IMPORTANT: Pass IP from ARP table
            vendor=None, # TODO: Lookup via MAC DB
            signal_strength=None, # Not available from ARP
            is_router=False, # Needs further checks beyond ARP
            last_seen=time.time(), # Timestamp when device was seen
        ).to_dict() # Convert to dict for storage in AppState

        # Update the global AppState with the device data
        # app_state.update_devices is a method in AppState to safely update its internal data
        app_state.update_devices({mac: device_data}) # Pass a dictionary of {mac: device_data}
        
        logger.info(f"[device_scanner] Detected device from ARP: {mac} ({ip}) - Stored in AppState")

    logger.info(f"[device_scanner] Finished ARP table device scan. Updated AppState with {len(app_state.discovery_graph.get('devices', {}))} devices.")


# <--- CRITICAL CHANGE: Updated __main__ block for standalone testing
if __name__ == "__main__":
    # In a standalone run, get the AppState singleton
    from core.state_management.state import get_state
    from core.debug_tools import dump_app_state # Assuming dump_app_state is in debug_tools

    test_app_state = get_state()
    scan_devices_from_arp_table_and_update_state(test_app_state)
    dump_app_state(test_app_state, title="AppState after device_scanner.py standalone run")