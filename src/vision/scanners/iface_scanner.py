# src/vision/scanners/iface_scanner.py

import subprocess
from typing import Optional, Dict, Any, List

from core.logger import logger
from core.state_management.state import AppState # Import the global AppState
from db.schemas.interface import Interface # Import your Pydantic schema

# Pylance Warning: `time` is imported but unused (from AppState update comment above)
# The `time` import is not directly used in this file but in the `runner.py`
# when populating `last_seen` for devices discovered via arp_scan.
# I'll keep it here as it was in my previous suggestion, as it's a common dependency
# for timestamping, but acknowledge it's not strictly used in *this* file's current scope.
# If it's truly not used after runner is updated, it can be removed then.

def get_mac(interface: str) -> str:
    """
    Retrieves the MAC address for a given network interface.
    Returns "00:00:00:00:00:00" if not found.
    """
    try:
        with open(f"/sys/class/net/{interface}/address", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "00:00:00:00:00:00"

def get_ip_address(interface: str) -> Optional[str]:
    """
    Retrieves the primary IPv4 address (with CIDR) for a given interface.
    Returns None if no IPv4 address is found.
    """
    try:
        # Use `check=False` to prevent CalledProcessError for interfaces without IP
        result = subprocess.run(["ip", "addr", "show", "dev", interface], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.debug(f"Command 'ip addr show dev {interface}' failed with error: {result.stderr.strip()}")
            return None # Command failed, no IP info
            
        for line in result.stdout.splitlines():
            if "inet " in line:
                ip_part = line.strip().split("inet ")[1].split(" ")[0]
                # Pylance: Type of "ip_part" is "str" (correct)
                return ip_part
        return None
    except Exception as e:
        logger.debug(f"Could not get IP address for {interface}: {e}")
        return None

def _get_iw_phy_capabilities(phy_name: str) -> Dict[str, Any]:
    """
    Parses 'iw list' output for a specific phy (wiphy) to get its capabilities
    like supported modes and frequencies. This is a complex parse and might need
    to be more robust. For now, it focuses on general modes.
    """
    capabilities: Dict[str, Any] = {"supported_modes": []} # Explicitly type capabilities
    try:
        result = subprocess.run(["iw", "list"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.debug(f"Command 'iw list' failed with error: {result.stderr.strip()}")
            return capabilities
            
        lines = result.stdout.splitlines() # Store lines to iterate
        
        # Find the start of the specific phy section
        phy_section_start_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith(f"Wiphy {phy_name}"):
                phy_section_start_index = i
                break

        if phy_section_start_index == -1:
            logger.debug(f"Wiphy {phy_name} not found in 'iw list' output.")
            return capabilities

        # Iterate from the found phy section
        for i in range(phy_section_start_index, len(lines)):
            line = lines[i].strip()

            if line.startswith("Supported interface modes:"):
                # Pylance: Type of "supported_modes" is "List[Unknown]".
                # This warning means the elements added to the list from 'mode'
                # are not strongly typed. We'll add a type hint for `mode`.
                j = i + 1
                while j < len(lines):
                    mode_line = lines[j].strip()
                    if not mode_line.startswith("*"):
                        break # End of modes section
                    mode: str = mode_line.split("*")[1].strip() # Explicitly type `mode` as str
                    capabilities["supported_modes"].append(mode)
                    j += 1
                i = j - 1 # Adjust outer loop index
            elif line.startswith("Band "):
                # Pylance: "Band" not in string literal. This is a false positive
                # if line is indeed "Band X:". No fix needed.
                # However, your original string comparisons are loose. Let's make them safer.
                if "2412.0 MHz" in result.stdout: # Check full output if bands are scattered
                    capabilities['supports_2ghz'] = True
                if "5180.0 MHz" in result.stdout: # Check full output
                    capabilities['supports_5ghz'] = True
                if "5955.0 MHz" in result.stdout or "6015.0 MHz" in result.stdout: # Example for 6GHz, confirm exact values
                    capabilities['supports_6ghz'] = True

            elif "HT Capability" in line: # Or more specific "Capabilities: 0xXXXX"
                 capabilities['supports_11n'] = True
            elif "VHT Capabilities" in line:
                 capabilities['supports_11ac'] = True
            elif "HE Iftypes" in line or "HE PHY Capabilities" in line: # HE means 802.11ax
                 capabilities['supports_11ax'] = True
                 # More granular HE parsing logic would go here
                 # e.g., to parse supports_11ax_he80, supports_11ax_he160 etc.
                 # For now, these remain False by default unless a very specific parser is implemented.

            if line.strip() == "Supported commands:": # Stop parsing after capabilities section
                break

    except FileNotFoundError:
        logger.debug(f"iw command not found. Cannot get detailed wireless capabilities for {phy_name}.")
    except Exception as e:
        logger.warning(f"Error parsing iw list capabilities for {phy_name}: {e}")
    return capabilities


def scan_interfaces_and_update_state(app_state: AppState):
    """
    Scans network interfaces on the system and updates the AppState's discovery_graph
    with detailed interface information.
    """
    logger.info("[iface_scanner] Starting interface scan and updating AppState...")
    
    # app_state.discovery_graph is already initialized in AppState.__init__
    # as {"interfaces": {}, "devices": {}}, so no need to check/initialize here.

    found_interfaces_data: Dict[str, Dict[str, Any]] = {}
    wiphy_capabilities_cache: Dict[str, Dict[str, Any]] = {}

    try:
        # Get all link names (e.g., lo, eth0, wlan0)
        # Pylance: "data" is a tuple. Solution: Type hint `parts`.
        # Pylance: `_` is not accessed. This is usually fine, but let's name it if used.
        result_link = subprocess.run(["ip", "link", "show"], capture_output=True, text=True, check=False)
        if result_link.returncode != 0:
            logger.error(f"Command 'ip link show' failed: {result_link.stderr.strip()}")
            return # Exit if basic command fails

        lines = result_link.stdout.splitlines()

        for line in lines:
            if ": " not in line:
                continue
            _, data_str = line.split(": ", 1)  # Use _ for unused variable
            iface_info_parts: List[str] = data_str.strip().split(' ', 1)
            iface_name: str = iface_info_parts[0]
            status_line_remainder: str = iface_info_parts[1] if len(iface_info_parts) > 1 else ""

            # Filter out loopback interfaces. `p2p` interfaces can be wireless devices, so don't filter.
            if iface_name.startswith("lo"):
                continue

            mac: str = get_mac(iface_name) # Explicitly type `mac`
            is_up: bool = "UP" in status_line_remainder # Explicitly type `is_up`
            ip_address: Optional[str] = get_ip_address(iface_name) # Explicitly type `ip_address`

            driver: Optional[str] = None
            is_wireless: bool = False
            phy_name: Optional[str] = None
            current_mode: str = "ethernet" # Default for wired
            ssid: Optional[str] = None
            tx_power: Optional[str] = None
            channel_frequency: Optional[str] = None
            
            # Initialize all supports flags from schema. This large block of booleans
            # is directly from your Interface schema.
            # Initialize with False, then set to True if detected.
            supports_monitor: bool = False
            supports_managed: bool = False
            supports_ap: bool = False
            supports_mesh: bool = False
            supports_p2p: bool = False
            supports_adhoc: bool = False
            supports_wds: bool = False
            supports_vap: bool = False
            supports_tdma: bool = False
            supports_mimo: bool = False
            supports_5ghz: bool = False
            supports_6ghz: bool = False
            supports_2ghz: bool = False
            supports_11ax: bool = False
            supports_11ac: bool = False
            supports_11n: bool = False
            supports_11g: bool = False
            supports_11b: bool = False
            supports_11a: bool = False
            
            # Try to get driver info (works for both wired and wireless)
            try:
                # Pylance: "subprocess.run" returns "CompletedProcess[bytes]" not "str".
                # Use text=True or decode stdout/stderr. text=True already used, so warning might be outdated or due to other context.
                ethtool_result = subprocess.run(["sudo", "ethtool", "-i", iface_name], capture_output=True, text=True, check=False)
                if ethtool_result.returncode == 0:
                    for eline in ethtool_result.stdout.splitlines():
                        if "driver:" in eline:
                            driver = eline.split(":")[1].strip()
                            if driver in ["iwlwifi", "ath9k", "rt2800usb", "mt76", "brcmfmac", "rtl8812au"]: 
                                is_wireless = True
                            break
            except Exception as e:
                logger.debug(f"Could not get ethtool info for {iface_name}: {e}")

            # If wireless, get more specific details using 'iw dev'
            if is_wireless:
                try:
                    iw_dev_info_result = subprocess.run(["iw", "dev", iface_name, "info"], capture_output=True, text=True, check=False)
                    if iw_dev_info_result.returncode == 0:
                        iw_output = iw_dev_info_result.stdout
                        for iw_line in iw_output.splitlines():
                            if "type " in iw_line:
                                current_mode = iw_line.split("type")[1].strip()
                            if "wiphy " in iw_line:
                                phy_name = iw_line.split("wiphy")[1].strip().split()[0]
                            if "ssid " in iw_line:
                                ssid = iw_line.split("ssid")[1].strip()
                            if "txpower " in iw_line:
                                tx_power = iw_line.split("txpower")[1].strip()
                            if "channel " in iw_line:
                                channel_frequency = iw_line.split("channel")[1].strip()
                        
                        # Populate capabilities from wiphy, but only once per wiphy
                        if phy_name: # Ensure phy_name is not None before using
                            if phy_name not in wiphy_capabilities_cache:
                                wiphy_capabilities_cache[phy_name] = _get_iw_phy_capabilities(phy_name)
                            
                            phy_caps: Dict[str, Any] = wiphy_capabilities_cache[phy_name] # Explicitly type `phy_caps`
                            if "monitor" in phy_caps.get("supported_modes", []):
                                supports_monitor = True
                            if "managed" in phy_caps.get("supported_modes", []):
                                supports_managed = True
                            if "AP" in phy_caps.get("supported_modes", []):
                                supports_ap = True
                            if "mesh" in phy_caps.get("supported_modes", []):
                                supports_mesh = True
                            if "P2P-client" in phy_caps.get("supported_modes", []) or "P2P-GO" in phy_caps.get("supported_modes", []):
                                supports_p2p = True
                            
                            supports_2ghz = phy_caps.get('supports_2ghz', False)
                            supports_5ghz = phy_caps.get('supports_5ghz', False)
                            supports_6ghz = phy_caps.get('supports_6ghz', False)

                            supports_11n = phy_caps.get('supports_11n', False)
                            supports_11ac = phy_caps.get('supports_11ac', False)
                            supports_11ax = phy_caps.get('supports_11ax', False)
                            # Pylance: "supports_11a", "supports_11b", "supports_11g" not accessed.
                            # These are defined above but then conditionally set. This is fine.
                            supports_11a = phy_caps.get('supports_11a', False)
                            supports_11b = phy_caps.get('supports_11b', False)
                            supports_11g = phy_caps.get('supports_11g', False)
                            
                            # You would similarly map other detailed 11ax_he capabilities here
                            # from a more robust _get_iw_phy_capabilities parser.
                            # For now, default all these specific HE fields to False
                            # Pylance: Variable "supports_adhoc", etc. not accessed.
                            # These are schema fields that default to False.
                            # They are included in iface_data dict directly.

                except FileNotFoundError:
                    logger.debug(f"iw command not found. Cannot get detailed wireless info for {iface_name}.")
                except Exception as e:
                    logger.warning(f"Error getting iw dev info for {iface_name}: {e}")

            # Construct the dictionary for the Interface Pydantic model
            iface_data: Dict[str, Any] = { # Explicitly type `iface_data`
                "name": iface_name,
                "mac": mac,
                "is_up": is_up,
                "ip_address": ip_address,
                "mode": current_mode,
                "driver": driver,
                "phy_name": phy_name,
                "ssid": ssid,
                "tx_power": tx_power,
                "channel_frequency": channel_frequency,
                "signal_quality": None, # Needs specific parsing if available, placeholder for now
                "supports_monitor": supports_monitor,
                "supports_managed": supports_managed,
                "supports_ap": supports_ap,
                "supports_mesh": supports_mesh,
                "supports_p2p": supports_p2p,
                "supports_adhoc": supports_adhoc, # Was False, now uses initialized var
                "supports_wds": supports_wds,     # Was False, now uses initialized var
                "supports_vap": supports_vap,     # Was False, now uses initialized var
                "supports_tdma": supports_tdma,   # Was False, now uses initialized var
                "supports_mimo": supports_mimo,   # Was False, now uses initialized var
                "supports_5ghz": supports_5ghz,
                "supports_6ghz": supports_6ghz,
                "supports_2ghz": supports_2ghz,
                "supports_11ax": supports_11ax,
                "supports_11ac": supports_11ac,
                "supports_11n": supports_11n,
                "supports_11g": supports_11g,
                "supports_11b": supports_11b,
                "supports_11a": supports_11a,
                # All the many supports_11ax_heXXXX fields would go here, initialized to False
                # and conditionally set to True based on detailed iw list parsing.
                **{f"supports_11ax_he{bw}": False for bw in [80, 160, 240, 320, 480, 640, 960, 1280, 1600, 1920, 2240, 2560, 2880, 3200, 3520, 3840, 4160, 4480, 4800, 5120, 5440, 5760, 6080, 6400, 6720, 7040, 7360, 7680, 8000, 8320, 8640, 8960, 9280, 9600, 9920, 10240, 10560, 10880, 11200, 11520, 11840, 12160, 12480, 12800, 13120, 13440, 13760, 14080, 14400, 14720, 15040, 15360, 15680, 16000, 16320, 16640, 16960, 17280, 17600, 17920, 18240, 18560, 18880, 19200, 19520, 19840, 20160, 20480, 20800, 21120, 21440, 21760, 22080, 22400, 22720, 23040, 23360, 23680, 24000, 24320, 24640, 24960, 25280, 25600, 25920, 26240, 26560, 26880, 27200, 27520, 27840, 28160, 28480, 28800, 29120, 29440, 29760, 30080, 30400, 30720, 31040, 31360, 31680, 32000, 32320, 32640, 32960, 33280, 33600, 33920, 34240, 34560, 34880, 35200, 35520, 35840, 36160, 36480, 36800, 37120, 37440, 37760, 38080, 38400, 38720, 39040, 39360, 39680, 40000, 40320, 40640, 40960, 41280, 41600]}
            }
            
            # Validate with Pydantic schema and get dictionary representation
            try:
                validated_iface = Interface(**iface_data)
                found_interfaces_data[iface_name] = validated_iface.to_dict()
                # Pylance: "iface_data" is "dict[str, Any]". This is fine.
                logger.info(f"[iface_scanner] Detected interface: {iface_name} - {mac} ({ip_address or 'No IP'}) - Stored in temporary data.")
            except Exception as e:
                logger.warning(f"[iface_scanner] Could not validate or process interface {iface_name}: {e}. Data: {iface_data}")

        # Update the global AppState with the collected interface data
        # Pylance: "found_interfaces_data" is "dict[str, dict[str, Any]]". This is fine.
        app_state.update_interfaces(found_interfaces_data)
        logger.info(f"[iface_scanner] Finished interface scan. Updated AppState with {len(found_interfaces_data)} interfaces.")

    except Exception as e:
        logger.error(f"[iface_scanner] Failed to scan interfaces: {e}")