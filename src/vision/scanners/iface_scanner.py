# src/vision/scanners/iface_scanner.py

import subprocess
from typing import Optional, Dict, Any
import re

from core.logger import logger
from core.state_management.state import AppState
from db.schemas.interface import Interface # Import the Pydantic schema


def get_mac(interface: str) -> str:
    """
    Retrieves the MAC address for a given network interface using 'ip link show'.
    Returns "00:00:00:00:00:00" if not found or on error.
    """
    try:
        result = subprocess.run(["ip", "link", "show", interface], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.debug(f"[{interface}] Command 'ip link show {interface}' failed: {result.stderr.strip()}")
            return "00:00:00:00:00:00"
            
        mac_match = re.search(r"link/\w+\s+((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})", result.stdout)
        if mac_match:
            return mac_match.group(1).upper()
        
        logger.debug(f"[{interface}] MAC address not found in 'ip link show' output for {interface}.")
        return "00:00:00:00:00:00"
    except Exception as e:
        logger.debug(f"[{interface}] Error getting MAC address for {interface}: {e}")
        return "00:00:00:00:00:00"

def get_ip_address(interface: str) -> Optional[str]:
    """
    Retrieves the primary IPv4 address (with CIDR) for a given interface.
    Returns None if no IPv4 address is found.
    """
    try:
        result = subprocess.run(["ip", "addr", "show", "dev", interface], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.debug(f"[{interface}] Command 'ip addr show dev {interface}' failed: {result.stderr.strip()}")
            return None
            
        for line in result.stdout.splitlines():
            if "inet " in line.strip() and not line.strip().startswith("inet6"): # Ensure it's IPv4
                ip_part = line.strip().split("inet ")[1].split(" ")[0]
                return ip_part
        return None
    except Exception as e:
        logger.debug(f"[{interface}] Could not get IP address for {interface}: {e}")
        return None

# MODIFIED: Improved Wiphy matching and general parsing for capabilities
def _get_iw_phy_capabilities(phy_full_name: str) -> Dict[str, Any]:
    """
    Parses 'iw list' output for a specific physical device (wiphy, e.g., 'phy0')
    to get its global capabilities like supported modes and frequencies.
    """
    capabilities: Dict[str, Any] = {
        "supported_modes": [],
        'supports_monitor': False,
        'supports_managed': False,
        'supports_ap': False,
        'supports_mesh': False,
        'supports_p2p': False,
        'supports_adhoc': False,
        'supports_wds': False,
        'supports_vap': False,
        'supports_tdma': False,
        'supports_mimo': False,
        'supports_5ghz': False,
        'supports_6ghz': False,
        'supports_2ghz': False,
        'supports_11ax': False,
        'supports_11ac': False,
        'supports_11n': False,
        'supports_11g': False,
        'supports_11b': False,
        'supports_11a': False,
    }
    # Add supports_11ax_he{bw} keys
    for bw in [
        80, 160, 240, 320, 480, 640, 960, 1280, 1600, 1920, 2240, 2560, 2880, 3200, 3520, 3840, 4160,
        4480, 4800, 5120, 5440, 5760, 6080, 6400, 6720, 7040, 7360, 7680, 8000, 8320, 8640, 8960, 9280,
        9600, 9920, 10240, 10560, 10880, 11200, 11520, 11840, 12160, 12480, 12800, 13120, 13440, 13760,
        14080, 14400, 14720, 15040, 15360, 15680, 16000, 16320, 16640, 16960, 17280, 17600, 17920, 18240,
        18560, 18880, 19200, 19520, 19840, 20160, 20480, 20800, 21120, 21440, 21760, 22080, 22400, 22720,
        23040, 23360, 23680, 24000, 24320, 24640, 24960, 25280, 25600, 25920, 26240, 26560, 26880, 27200,
        27520, 27840, 28160, 28480, 28800, 29120, 29440, 29760, 30080, 30400, 30720, 31040, 31360, 31680,
        32000, 32320, 32640, 32960, 33280, 33600, 33920, 34240, 34560, 34880, 35200, 35520, 35840, 36160,
        36480, 36800, 37120, 37440, 37760, 38080, 38400, 38720, 39040, 39360, 39680, 40000, 40320, 40640,
        40960, 41280, 41600
    ]:
        capabilities[f"supports_11ax_he{bw}"] = False

    try:
        result = subprocess.run(["iw", "list"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.debug(f"Command 'iw list' failed: {result.stderr.strip()}")
            return capabilities
            
        lines = result.stdout.splitlines()
        
        # Determine the start and end of the relevant wiphy section
        phy_start_index = -1
        phy_end_index = -1
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith(f"Wiphy {phy_full_name}"):
                phy_start_index = i
            elif phy_start_index != -1 and stripped_line.startswith("Wiphy phy") and stripped_line != f"Wiphy {phy_full_name}":
                phy_end_index = i
                break
            elif phy_start_index != -1 and stripped_line.startswith("Supported commands:"):
                phy_end_index = i # End of the capabilities list for a phy
                break
        
        if phy_start_index == -1:
            logger.debug(f"Wiphy {phy_full_name} not found in 'iw list' output.")
            return capabilities
        
        # Slice lines for just this wiphy's capabilities
        phy_lines = lines[phy_start_index:phy_end_index if phy_end_index != -1 else len(lines)]

        for i, line in enumerate(phy_lines):
            stripped_line = line.strip()

            if stripped_line.startswith("Supported interface modes:"):
                j = i + 1
                while j < len(phy_lines):
                    mode_line = phy_lines[j].strip()
                    if not mode_line.startswith("*"):
                        break
                    mode: str = mode_line.split("*")[1].strip()
                    capabilities["supported_modes"].append(mode)
                    # Update specific support flags directly from supported modes
                    if mode == "monitor": capabilities['supports_monitor'] = True
                    elif mode == "managed": capabilities['supports_managed'] = True
                    elif mode == "AP": capabilities['supports_ap'] = True
                    elif mode == "mesh point": capabilities['supports_mesh'] = True
                    elif "P2P" in mode: capabilities['supports_p2p'] = True
                    # Add other specific mode checks here if needed
                    j += 1
                continue

            # Band capabilities and Wi-Fi standards (more robust parsing via regex)
            if "Band 1:" in stripped_line: # Often indicates 2.4GHz
                capabilities['supports_2ghz'] = True
                # Look for 802.11b, g, n in this band's capabilities
                if "HT20/HT40" in phy_lines[i+1]: # HT usually means 802.11n
                    capabilities['supports_11n'] = True
                # 802.11g and b are typically supported if 2.4GHz exists
                capabilities['supports_11g'] = True
                capabilities['supports_11b'] = True

            elif "Band 2:" in stripped_line: # Often indicates 5GHz
                capabilities['supports_5ghz'] = True
                # Look for 802.11a, ac, ax in this band's capabilities
                if "VHT Capabilities" in phy_lines[i+1]: # VHT usually means 802.11ac
                    capabilities['supports_11ac'] = True
                if "HE Iftypes" in phy_lines[i+1]: # HE means 802.11ax
                    capabilities['supports_11ax'] = True
                capabilities['supports_11a'] = True # 802.11a is typically supported if 5GHz exists
            
            elif "Band 4:" in stripped_line: # Often indicates 6GHz
                capabilities['supports_6ghz'] = True
                # Look for 802.11ax in this band's capabilities
                if "HE Iftypes" in phy_lines[i+1]: # HE means 802.11ax
                    capabilities['supports_11ax'] = True

            # General HT/VHT/HE capabilities if not tied to a specific band parsing
            if "HT Capabilities" in stripped_line or re.search(r"HT Max RX data rate:", stripped_line):
                 capabilities['supports_11n'] = True
            if "VHT Capabilities" in stripped_line or re.search(r"VHT RX MCS set:", stripped_line):
                 capabilities['supports_11ac'] = True
            if "HE Iftypes" in stripped_line or "HE PHY Capabilities" in stripped_line or re.search(r"HE RX MCS and NSS set", stripped_line):
                 capabilities['supports_11ax'] = True
                 # Detailed 11ax_he parsing would involve complex regex to extract bandwidths
                 # For now, we only set the main supports_11ax flag.

    except FileNotFoundError:
        logger.debug(f"iw command not found. Cannot get detailed wireless capabilities for {phy_full_name}.")
    except Exception as e:
        logger.warning(f"Error parsing iw list capabilities for {phy_full_name}: {e}")
    return capabilities


def scan_interfaces_and_update_state(app_state: AppState):
    """
    Scans network interfaces on the system and updates the AppState's discovery_graph
    with detailed interface information.
    """
    logger.info("[iface_scanner] Starting interface scan and updating AppState...")
    
    found_interfaces_data: Dict[str, Dict[str, Any]] = {}
    wiphy_capabilities_cache: Dict[str, Dict[str, Any]] = {} # Cache for phy capabilities (e.g., 'phy0')

    try:
        # Get all link names (e.g., lo, eth0, wlan0)
        result_link = subprocess.run(["ip", "link", "show"], capture_output=True, text=True, check=False)
        if result_link.returncode != 0:
            logger.error(f"Command 'ip link show' failed: {result_link.stderr.strip()}")
            return # Exit if basic command fails

        lines = result_link.stdout.splitlines()

        for line_num, line in enumerate(lines):
            # Each interface definition starts with a number and a colon, e.g., "1: lo: <LOOPBACK..."
            match_iface_line = re.match(r"^\d+:\s+(\w+):.*", line.strip())
            if not match_iface_line:
                continue # Not an interface definition line
            
            iface_name = match_iface_line.group(1) # Extract just the name, e.g., "wlan0"

            if iface_name.startswith("lo"): # Skip loopback interface
                logger.debug(f"Skipping loopback interface: {iface_name}")
                continue

            # Check if the interface is actually up and has LOWER_UP for wired/wireless
            status_line = lines[line_num].strip()
            is_up = "UP" in status_line and "LOWER_UP" in status_line
            if not is_up: # Also check for <UP,BROADCAST,MULTICAST> in case LOWER_UP isn't present for UP state
                is_up = re.search(r"<\w*UP,\w*>", status_line) is not None

            mac = get_mac(iface_name)
            ip_address = get_ip_address(iface_name)

            driver = None
            is_wireless = False
            phy_name = None # This will be the number (e.g., "0")
            current_mode = "ethernet" # Default for wired
            
            # Initialize iface_data with schema defaults to ensure all fields are present
            # Creating a dummy instance and converting to dict is a neat trick for this
            default_iface_schema_dict = Interface(name="temp", mac="00:00:00:00:00:00").to_dict()
            iface_data: Dict[str, Any] = {
                k: v for k, v in default_iface_schema_dict.items() if k not in ["name", "mac"] # Exclude name/mac to set them explicitly
            }
            # Manually set the core identifying fields
            iface_data.update({
                "name": iface_name,
                "mac": mac,
                "is_up": is_up,
                "ip_address": ip_address,
            })

            # Try to get driver info (works for both wired and wireless)
            try:
                ethtool_result = subprocess.run(["sudo", "ethtool", "-i", iface_name], capture_output=True, text=True, check=False)
                if ethtool_result.returncode == 0:
                    for eline in ethtool_result.stdout.splitlines():
                        if "driver:" in eline:
                            driver = eline.split(":")[1].strip()
                            # Common wireless drivers indicate a wireless interface
                            if driver in ["iwlwifi", "ath9k", "rt2800usb", "mt76", "brcmfmac", "rtl8812au", "r8188eu"]: 
                                is_wireless = True
                            break
            except Exception as e:
                logger.debug(f"[{iface_name}] Could not get ethtool info: {e}")

            iface_data["driver"] = driver
            # The 'is_wireless' property in your schema is derived from 'driver' or 'phy_name'
            # (or implicitly from presence of iw dev info). Add this as a property in the schema,
            # or calculate it in the scanner for storage if it's a direct field.
            # Assuming 'is_wireless' is a direct bool field in your Interface schema
            iface_data["is_wireless"] = is_wireless 
            iface_data["mode"] = current_mode # Default to ethernet, update below for wireless

            # If wireless, get more specific details using 'iw dev'
            if is_wireless:
                try:
                    iw_dev_info_result = subprocess.run(["iw", "dev", iface_name, "info"], capture_output=True, text=True, check=False)
                    if iw_dev_info_result.returncode == 0:
                        iw_output = iw_dev_info_result.stdout
                        # Parse phy_name (e.g., "0")
                        phy_match_iw_dev = re.search(r"wiphy\s+(\d+)", iw_output)
                        if phy_match_iw_dev:
                            phy_name = phy_match_iw_dev.group(1) 
                            iface_data["phy_name"] = phy_name
                            
                            # Get global capabilities for this wiphy
                            # Use f"phy{phy_name}" as the argument to _get_iw_phy_capabilities
                            full_phy_name = f"phy{phy_name}"
                            if full_phy_name not in wiphy_capabilities_cache:
                                wiphy_capabilities_cache[full_phy_name] = _get_iw_phy_capabilities(full_phy_name)
                            
                            phy_caps: Dict[str, Any] = wiphy_capabilities_cache[full_phy_name] 
                            
                            # Update supported flags based on wiphy capabilities obtained from _get_iw_phy_capabilities
                            for cap_key, cap_value in phy_caps.items():
                                # Only update iface_data fields that start with 'supports_' and are boolean in schema
                                if cap_key.startswith("supports_") and cap_key in iface_data and isinstance(cap_value, bool):
                                    iface_data[cap_key] = cap_value
                                elif cap_key == "supported_modes":
                                    iface_data["supported_modes"] = cap_value
                            
                        else:
                             logger.warning(f"[{iface_name}] Could not find wiphy for wireless interface in 'iw dev info' output.")

                        # Parse current interface mode and other details from 'iw dev info'
                        for iw_line in iw_output.splitlines():
                            stripped_iw_line = iw_line.strip()
                            if stripped_iw_line.startswith("type "):
                                iface_data["mode"] = stripped_iw_line.split("type")[1].strip()
                            elif stripped_iw_line.startswith("ssid "):
                                iface_data["ssid"] = stripped_iw_line.split("ssid")[1].strip()
                            elif stripped_iw_line.startswith("txpower "):
                                iface_data["tx_power"] = stripped_iw_line.split("txpower")[1].strip()
                            elif stripped_iw_line.startswith("channel "):
                                iface_data["channel_frequency"] = stripped_iw_line.split("channel")[1].strip()

                    else: # iw dev info failed for a wireless interface
                         logger.warning(f"[{iface_name}] Command 'iw dev {iface_name} info' failed for wireless interface: {iw_dev_info_result.stderr.strip()}")

                except FileNotFoundError:
                    logger.debug(f"[{iface_name}] iw command not found. Cannot get detailed wireless info.")
                except Exception as e:
                    logger.warning(f"[{iface_name}] Error getting iw dev info: {e}")
            else: # Wired or unknown interface
                if iface_name == "lo": # Loopback is already skipped, but this provides a fallback mode
                    iface_data["mode"] = "loopback"
                # Else mode remains "ethernet" or "unknown" as initialized

            # Validate with Pydantic schema and get dictionary representation
            try:
                validated_iface = Interface(**iface_data)
                found_interfaces_data[iface_name] = validated_iface.to_dict()
                logger.info(f"[iface_scanner] Detected interface: {iface_name} - {mac} ({ip_address or 'No IP'}) - Stored in temporary data.")
            except Exception as e:
                logger.warning(f"[iface_scanner] Could not validate or process interface {iface_name}: {e}. Data: {iface_data}")

        app_state.update_interfaces(found_interfaces_data)
        logger.info(f"[iface_scanner] Finished interface scan. Updated AppState with {len(found_interfaces_data)} interfaces.")

    except Exception as e:
        logger.error(f"[iface_scanner] Failed to scan interfaces: {e}")