# /home/nexus/dev/projects/capgate/src/capgate/core/interface_manager.py

import json
import os
import re
import subprocess
from typing import List, Optional, Dict, Any

from core.logger import logger
from helpers import shelltools

class InterfaceInfo:
    """
    A data container for detailed network interface information.
    """
    def __init__(self,
                 name: str,
                 mac_address: Optional[str] = None,
                 is_up: bool = False,
                 ip_address: Optional[str] = None,
                 driver: Optional[str] = None,
                 is_wireless: bool = False,
                 phy_name: Optional[str] = None,
                 supported_modes: Optional[List[str]] = None,
                 current_mode: Optional[str] = None,
                 ssid: Optional[str] = None,
                 tx_power: Optional[str] = None,
                 channel_frequency: Optional[str] = None):
        self.name = name
        self.mac_address = mac_address
        self.is_up = is_up
        self.ip_address = ip_address
        self.driver = driver
        self.is_wireless = is_wireless
        self.phy_name = phy_name
        self.supported_modes: List[str] = supported_modes or []
        self.current_mode = current_mode
        self.ssid = ssid
        self.tx_power = tx_power
        self.channel_frequency = channel_frequency

    def supports_monitor_mode(self) -> bool:
        """Checks if 'monitor' is in the list of supported modes."""
        return any(mode.lower() == "monitor" for mode in self.supported_modes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mac_address": self.mac_address,
            "is_up": self.is_up,
            "ip_address": self.ip_address,
            "driver": self.driver,
            "is_wireless": self.is_wireless,
            "phy_name": self.phy_name,
            "supported_modes": self.supported_modes,
            "supports_monitor_mode": self.supports_monitor_mode(),
            "current_mode": self.current_mode,
            "ssid": self.ssid,
            "tx_power": self.tx_power,
            "channel_frequency": self.channel_frequency,
        }

    def __repr__(self) -> str:
        details = [f"Name: {self.name}"]
        if self.mac_address: details.append(f"MAC: {self.mac_address}")
        details.append(f"Status: {'UP' if self.is_up else 'DOWN'}")
        if self.ip_address: details.append(f"IP: {self.ip_address}")
        if self.driver: details.append(f"Driver: {self.driver}")
        type_str = "Wireless" if self.is_wireless else "Wired/Other"
        details.append(f"Type: {type_str}")
        if self.is_wireless:
            if self.phy_name: details.append(f"PHY: {self.phy_name}")
            if self.current_mode: details.append(f"Mode: {self.current_mode}")
            if self.ssid: details.append(f"SSID: {self.ssid}")
            if self.channel_frequency: details.append(f"Freq/Chan: {self.channel_frequency}")
            if self.tx_power: details.append(f"TxPwr: {self.tx_power}")
            details.append(f"Monitor Capable: {'Yes' if self.supports_monitor_mode() else 'No'}")
        return f"<InterfaceInfo({', '.join(details)})>"

class InterfaceManager:
    """
    Detects and manages detailed information about system network interfaces.
    """
    def __init__(self):
        self.interfaces_info: List[InterfaceInfo] = []
        self.phy_capabilities: Dict[str, Dict[str, Any]] = {}
        self._load_all_interface_data()

    def _parse_ip_addr_show(self, iface_name: str) -> Dict[str, Any]:
        data = {"mac_address": None, "ip_address": None, "is_up": False}
        try:
            output = shelltools.run_command(f"ip addr show dev {iface_name}", require_root=False, check=False)
            if not output:
                logger.debug(f"No output from 'ip addr show dev {iface_name}'.")
                return data
            mac_match = re.search(r"link/\w+\s+((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})", output)
            if mac_match:
                data["mac_address"] = mac_match.group(1)
            ip_match = re.search(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})", output)
            if ip_match:
                data["ip_address"] = ip_match.group(1)
            if "UP" in output.splitlines()[0] and "LOWER_UP" in output.splitlines()[0]:
                data["is_up"] = True
            elif "<UP," in output.splitlines()[0]:
                data["is_up"] = True
        except Exception as e:
            logger.warning(f"Error parsing 'ip addr show {iface_name}': {e}")
        return data

    def _get_driver_info(self, iface_name: str) -> Optional[str]:
        try:
            output = shelltools.run_command(f"ethtool -i {iface_name}", require_root=True, check=False)
            if not output:
                driver_path = f"/sys/class/net/{iface_name}/device/driver"
                if os.path.exists(driver_path) and os.path.islink(driver_path):
                    return os.path.basename(os.readlink(driver_path))
                return None
            driver_match = re.search(r"driver:\s+(\S+)", output)
            if driver_match:
                return driver_match.group(1)
        except Exception as e:
            logger.debug(f"Could not get driver for {iface_name} using ethtool: {e}")
        return None

    def _parse_iw_list(self) -> Dict[str, Dict[str, Any]]:
        """
        Parses 'iw list' to get capabilities per physical device (phy).
        Returns a dictionary: {'phyX': {'supported_modes': [...], ...}}
        """
        phy_data: Dict[str, Dict[str, Any]] = {}
        current_phy: Optional[str] = None
        in_modes_section: bool = False

        try:
            output = shelltools.run_command("iw list", require_root=False, check=True)
            
            # --- Advanced Improvement 1: Robustly handle multiline and nested sections ---
            for line in output.splitlines():
                line = line.strip()
                wiphy_match = re.match(r"Wiphy\s+(phy\d+)", line)
                if wiphy_match:
                    current_phy = wiphy_match.group(1)
                    phy_data[current_phy] = {"supported_modes": []}
                    in_modes_section = False
                    continue
                if not current_phy:
                    continue
                if "Supported interface modes:" in line:
                    in_modes_section = True
                    continue
                if in_modes_section:
                    mode_match = re.match(r"\*\s*(\S+)", line)
                    if mode_match:
                        phy_data[current_phy]["supported_modes"].append(mode_match.group(1))
                    else:
                        in_modes_section = False
        except Exception as e:
            logger.error(f"Failed to parse 'iw list': {e}")
        # --- Advanced Improvement 2: Log parsed data for easier debugging ---
        logger.debug(f"Parsed phy capabilities from 'iw list': {phy_data}")
        # --- Advanced Improvement 3: Sort supported_modes for consistency ---
        for phy in phy_data.values():
            phy["supported_modes"].sort()
        return phy_data

    def _parse_iw_dev_iface_info(self, iface_name: str) -> Dict[str, Any]:
        data = {
            "phy_name": None,
            "current_mode": "unknown",
            "ssid": None,
            "tx_power": None,
            "channel_frequency": None,
        }
        try:
            output = shelltools.run_command(f"iw dev {iface_name} info", require_root=False, check=False)
            if not output:
                return data
            phy_match = re.search(r"wiphy\s+(\d+)", output)
            if phy_match:
                data["phy_name"] = f"phy{phy_match.group(1)}"
            type_match = re.search(r"type\s+(\S+)", output)
            if type_match:
                data["current_mode"] = type_match.group(1)
            ssid_match = re.search(r"ssid\s+(.+)", output)
            if ssid_match:
                data["ssid"] = ssid_match.group(1).strip()
            txpower_match = re.search(r"txpower\s+([\d\.]+\s+dBm)", output)
            if txpower_match:
                data["tx_power"] = txpower_match.group(1)
            channel_match = re.search(r"channel\s+(\d+)\s+\(([\d\.]+\s+MHz)(?:[^)]*)?\)(?:.*width:\s*([\d\.]+\s+MHz))?", output)
            if channel_match:
                chan = channel_match.group(1)
                freq = channel_match.group(2)
                width = channel_match.group(3)
                chan_freq_str = f"{freq} (channel {chan})"
                if width:
                    chan_freq_str += f", width {width}"
                data["channel_frequency"] = chan_freq_str
        except Exception as e:
            logger.warning(f"Error parsing 'iw dev {iface_name} info': {e}")
        return data

    def _load_all_interface_data(self):
        logger.info("Starting comprehensive interface detection...")
        self.interfaces_info.clear()
        self.phy_capabilities = self._parse_iw_list()
        try:
            iface_names = os.listdir('/sys/class/net/')
        except FileNotFoundError:
            logger.error("Could not list /sys/class/net/. Interface detection failed.")
            return
        for iface_name in iface_names:
            logger.debug(f"Processing interface: {iface_name}")
            ip_data = self._parse_ip_addr_show(iface_name)
            driver = self._get_driver_info(iface_name)
            info = InterfaceInfo(
                name=iface_name,
                mac_address=ip_data["mac_address"],
                is_up=ip_data["is_up"],
                ip_address=ip_data["ip_address"],
                driver=driver
            )
            wireless_details = self._parse_iw_dev_iface_info(iface_name)
            if wireless_details["phy_name"]:
                info.is_wireless = True
                info.phy_name = wireless_details["phy_name"]
                info.current_mode = wireless_details["current_mode"]
                info.ssid = wireless_details["ssid"]
                info.tx_power = wireless_details["tx_power"]
                info.channel_frequency = wireless_details["channel_frequency"]
                if info.phy_name in self.phy_capabilities:
                    info.supported_modes = self.phy_capabilities[info.phy_name].get("supported_modes", [])
                else:
                    logger.warning(f"PHY {info.phy_name} for interface {iface_name} not found in 'iw list' parsed data.")
            else:
                info.is_wireless = False
                if iface_name == "lo":
                    info.current_mode = "loopback"
                elif os.path.exists(f"/sys/class/net/{iface_name}/phydev"):
                    info.current_mode = "ethernet"
                else:
                    info.current_mode = "unknown"
            self.interfaces_info.append(info)
            logger.debug(f"Detected and processed: {info!r}")
        logger.info(f"Finished interface detection. Found {len(self.interfaces_info)} interfaces.")

    def get_interfaces(self, 
                       wireless_only: bool = False, 
                       monitor_capable_only: bool = False,
                       is_up_only: bool = False) -> List[InterfaceInfo]:
        result = list(self.interfaces_info)
        if wireless_only:
            result = [iface for iface in result if iface.is_wireless]
        if monitor_capable_only:
            result = [iface for iface in result if iface.is_wireless and iface.supports_monitor_mode()]
        if is_up_only:
            result = [iface for iface in result if iface.is_up]
        return result

    def get_interface_by_name(self, name: str) -> Optional[InterfaceInfo]:
        for iface in self.interfaces_info:
            if iface.name == name:
                return iface
        return None

    def refresh_interfaces(self):
        logger.info("Refreshing interface list...")
        self._load_all_interface_data()

# Example usage (for testing this file standalone):
if __name__ == "__main__":
    manager = InterfaceManager()
    all_ifaces = manager.get_interfaces()
    print(f"\n--- All Detected Interfaces ({len(all_ifaces)}) ---")
    for iface in all_ifaces:
        print(iface)
    wireless_ifaces = manager.get_interfaces(wireless_only=True)
    print(f"\n--- Wireless Interfaces ({len(wireless_ifaces)}) ---")
    for iface in wireless_ifaces:
        print(iface)
    monitor_ifaces = manager.get_interfaces(monitor_capable_only=True)
    print(f"\n--- Monitor Capable Wireless Interfaces ({len(monitor_ifaces)}) ---")
    for iface in monitor_ifaces:
        print(iface)
    up_monitor_ifaces = manager.get_interfaces(monitor_capable_only=True, is_up_only=True)
    print(f"\n--- UP Monitor Capable Wireless Interfaces ({len(up_monitor_ifaces)}) ---")
    for iface in up_monitor_ifaces:
        print(iface)
    test_iface_name = "lo"
    if wireless_ifaces:
        test_iface_name = wireless_ifaces[0].name
    specific_iface = manager.get_interface_by_name(test_iface_name)
    if specific_iface:
        print(f"\n--- Details for Interface '{test_iface_name}' ---")
        print(json.dumps(specific_iface.to_dict(), indent=2))
    else:
        print(f"\nInterface '{test_iface_name}' not found by get_interface_by_name.")