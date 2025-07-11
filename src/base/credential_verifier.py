# src/core/credential_verifier.py
"""
Credential Verifier: Provides functions to verify captured Wi-Fi passwords
by attempting to connect to the target AP.
"""

import subprocess
import time
import shlex
from typing import Optional, List

from base.logger import logger
from helpers import shelltools # For run_command


class CredentialVerifier:
    """
    Manages the verification of Wi-Fi credentials by attempting to connect
    to an access point using nmcli.
    """
    def __init__(self):
        self.logger = logger
        # No process to store for nmcli, as it's run synchronously via shelltools.run_command

    def verify_password(
        self,
        verify_interface: str, # The interface to use for verification (must be in managed mode)
        ssid: str,
        password: str,
        bssid: Optional[str] = None, # Optional: target specific AP if multiple with same SSID
        timeout_seconds: int = 10 # How long to wait for connection attempt
    ) -> bool:
        """
        Attempts to connect to a Wi-Fi network using the provided credentials via nmcli.

        Args:
            verify_interface (str): The network interface to use for verification.
                                    This interface should NOT be the Evil Twin AP interface
                                    and must be in managed mode.
            ssid (str): The SSID (network name) of the target Wi-Fi.
            password (str): The password to attempt.
            bssid (Optional[str]): The BSSID of the target AP (useful if multiple APs have same SSID).
            timeout_seconds (int): Maximum time to wait for the connection attempt.

        Returns:
            bool: True if connection is successful (password is valid), False otherwise.
        """
        self.logger.info(f"[CredentialVerifier] Attempting to verify password for SSID '{ssid}' on {verify_interface}...")

        # 1. Check if NetworkManager is managing the interface, and temporarily unmanage/disconnect it
        nm_managed_by_us: bool = False
        try:
            # Check if device is active and managed by NM, or if it's already connected to something
            nm_dev_status = shelltools.run_command(f"nmcli -g GENERAL.STATE,GENERAL.NM-MANAGED dev show {verify_interface}", require_root=True, check=False).strip().lower()
            
            # If the interface is in an active state or managed by NM
            if "connected" in nm_dev_status or "connecting" in nm_dev_status or "activated" in nm_dev_status or "yes" in nm_dev_status:
                self.logger.warning(f"[CredentialVerifier] {verify_interface} is currently active/managed by NetworkManager. Attempting to disconnect/unmanage.")
                
                # Disconnect any existing connection first
                shelltools.run_command(["nmcli", "dev", "disconnect", verify_interface], require_root=True, check=False)
                # Then set it to unmanaged
                shelltools.run_command(["nmcli", "dev", "set", verify_interface, "managed", "no"], require_root=True, check=False)
                nm_managed_by_us = True
                time.sleep(1) # Give NM time to release the interface
            else:
                self.logger.debug(f"[CredentialVerifier] {verify_interface} not actively managed/connected by NetworkManager. Proceeding.")

        except Exception as e:
            self.logger.warning(f"[CredentialVerifier] Could not check/unmanage NetworkManager for {verify_interface}: {e}. Proceeding with potential interference.")

        connection_successful: bool = False
        # Create a unique connection name
        temp_connection_name = f"capgate_test_conn_{int(time.time())}" 

        try:
            # 2. Create a temporary nmcli connection profile
            add_conn_cmd: List[str] = [
                "nmcli", "con", "add", "type", "wifi", 
                "ifname", verify_interface, 
                "con-name", temp_connection_name,
                "ssid", ssid,
                "wifi-sec.key-mgmt", "wpa-psk", # Assume WPA/WPA2 Personal
                "wifi-sec.psk", password
            ]
            if bssid:
                add_conn_cmd.extend(["bssid", bssid])

            self.logger.debug(f"[CredentialVerifier] Creating nmcli connection: {shlex.join(add_conn_cmd)}")
            # Check=True here to ensure the connection profile itself is added successfully
            shelltools.run_command(add_conn_cmd, require_root=True, check=True) 

            # 3. Bring up the newly created connection
            up_conn_cmd: List[str] = ["nmcli", "con", "up", temp_connection_name]
            self.logger.debug(f"[CredentialVerifier] Bringing up nmcli connection: {shlex.join(up_conn_cmd)}")
            
            try:
                # Run the 'up' command with the specified timeout.
                # If this command exits with 0 within the timeout, it's considered successful.
                shelltools.run_command(up_conn_cmd, require_root=True, check=True, timeout=timeout_seconds)
                self.logger.info(f"[CredentialVerifier] Successfully connected to '{ssid}' with provided password!")
                connection_successful = True
            except subprocess.TimeoutExpired:
                self.logger.warning(f"[CredentialVerifier] Connection to '{ssid}' timed out after {timeout_seconds}s. Password likely incorrect.")
            except subprocess.CalledProcessError as e:
                # Log stderr for more detail from nmcli
                self.logger.warning(f"[CredentialVerifier] Failed to connect to '{ssid}' (Exit: {e.returncode}). Password likely incorrect. Error: {e.stderr.strip()}")

        except FileNotFoundError:
            self.logger.error("[CredentialVerifier] nmcli command not found. Please ensure NetworkManager is installed.")
        except Exception as e:
            self.logger.error(f"[CredentialVerifier] An unexpected error occurred during password verification: {e}")
        
        finally:
            # 4. Clean up the temporary nmcli connection profile
            self.logger.debug("[CredentialVerifier] Cleaning up temporary nmcli connection profile...")
            # Use check=False as it might fail if connection was never fully established or already gone
            shelltools.run_command(["nmcli", "con", "delete", temp_connection_name], require_root=True, check=False)

            # 5. Restore NetworkManager management if we temporarily disabled it
            if nm_managed_by_us:
                self.logger.info(f"[CredentialVerifier] Restoring NetworkManager management for {verify_interface}.")
                shelltools.run_command(["nmcli", "dev", "set", verify_interface, "managed", "yes"], require_root=True, check=False)
            
            self.logger.info(f"[CredentialVerifier] Verification attempt for '{ssid}' finished.")

        return connection_successful
