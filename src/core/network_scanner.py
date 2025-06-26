# src/core/network_scanner.py
"""
Provides core network scanning functionalities, such as running airodump-ng
and parsing its output. Designed to be reusable across plugins.
"""

import subprocess
import tempfile
import time
import os
import csv # For more robust CSV parsing
from typing import Dict, Any, Optional, List

from core.logger import logger

class NetworkScanner:
    """
    Encapsulates network scanning operations, primarily using airodump-ng.
    """
    def __init__(self):
        self.logger = logger

    def perform_airodump_scan(self, 
                             monitor_interface: str, 
                             scan_duration_seconds: int, 
                             network_security_filter: str = "WPA") -> List[Dict[str, str]]:
        """
        Executes airodump-ng to scan for Wi-Fi networks and parses its output.

        Args:
            monitor_interface (str): The interface (must be in monitor mode) to use for scanning.
            scan_duration_seconds (int): How long (in seconds) to run the scan.
            network_security_filter (str): A string to filter networks by privacy type (e.g., "WPA", "WEP", "OPN").

        Returns:
            List[Dict[str, str]]: A list of dictionaries, each representing a discovered AP
                                   matching the filter. Returns an empty list on failure or no matches.
                                   Each dict contains keys: "bssid", "channel", "essid", "essid_raw", "privacy", "power".
        """
        self.logger.info(f"[NetworkScanner] Starting airodump-ng scan on {monitor_interface} for {scan_duration_seconds}s...")

        # Create a temporary file for airodump-ng output prefix
        temp_csv_handle: Optional[Any] = None
        output_prefix: Optional[str] = None
        try:
            temp_csv_handle = tempfile.NamedTemporaryFile(mode='w', suffix=".csv", delete=False)
            output_prefix = temp_csv_handle.name[:-4] # Get prefix without .csv
            temp_csv_handle.close() # Close handle so airodump-ng can write
        except Exception as e:
            self.logger.error(f"[NetworkScanner] Failed to create temporary file for scan: {e}")
            if temp_csv_handle:
                os.unlink(temp_csv_handle.name) # Ensure cleanup if temp_csv_handle exists
            return []

        airodump_csv_file = f"{output_prefix}-01.csv"
        # List of all files airodump-ng might create, for cleanup
        airodump_log_files_to_clean = [
            airodump_csv_file, 
            f"{output_prefix}.cap", 
            f"{output_prefix}.kismet.csv", 
            f"{output_prefix}.kismet.netxml", 
            f"{output_prefix}.log.csv"
        ]

        proc: Optional[subprocess.Popen] = None # Initialize as None, will be set if subprocess starts successfully
        try:
            if output_prefix is None:
                self.logger.error("[NetworkScanner] Output prefix is None, cannot proceed with airodump-ng command.")
                return []
            airodump_cmd: List[str] = [
                "airodump-ng",
                "--output-format", "csv",
                "--write", output_prefix,
                "--write-interval", "1", # Flush CSV more often for real-time parsing capability (though not used here)
                monitor_interface
            ]
            self.logger.debug(f"[NetworkScanner] Executing airodump-ng command: {' '.join(airodump_cmd)}")
            
            proc = subprocess.Popen(airodump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True) # start_new_session creates new process group
                                                                                                                   # so terminate() kills it and its children.

            self.logger.info(f"[NetworkScanner] Scanning on {monitor_interface} for {scan_duration_seconds} seconds (filter: {network_security_filter})...")
            
            interrupted = False
            for _ in range(scan_duration_seconds):
                if proc.poll() is not None: # Process terminated unexpectedly
                    self.logger.warning("[NetworkScanner] airodump-ng terminated prematurely.")
                    break
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    self.logger.info("[NetworkScanner] Scan interrupted by user (Ctrl+C).")
                    interrupted = True
                    break
            
            if interrupted and proc.poll() is None: # If interrupted and process still running
                self.logger.info("[NetworkScanner] Terminating airodump-ng due to user interrupt...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("[NetworkScanner] airodump-ng did not terminate gracefully after interrupt, killing.")
                    proc.kill()
                    proc.wait() # Ensure process is truly dead
            
        except FileNotFoundError:
            self.logger.error("[NetworkScanner] airodump-ng command not found. Please ensure it's installed and in your PATH.")
            return []
        except Exception as e:
            self.logger.error(f"[NetworkScanner] Failed to start airodump-ng: {e}")
            return []
        finally:
            if proc and proc.poll() is None: # If process is still running (e.g., unexpected error before loop finished)
                self.logger.info("[NetworkScanner] Ensuring airodump-ng process is terminated.")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("[NetworkScanner] airodump-ng did not terminate gracefully in finally block, killing.")
                    proc.kill()
                    proc.wait()

        # Check if output file was created
        if not os.path.exists(airodump_csv_file) or os.path.getsize(airodump_csv_file) == 0:
            self.logger.error(f"[NetworkScanner] Airodump-ng output CSV file not found or is empty: {airodump_csv_file}")
            # Clean up other potential airodump files even if CSV is missing/empty
            for f_to_clean in airodump_log_files_to_clean:
                if os.path.exists(f_to_clean) and f_to_clean != airodump_csv_file:
                    try:
                        os.remove(f_to_clean)
                    except OSError: pass # Ignore if removal fails
            return []

        # --- Parse the CSV output ---
        networks: List[Dict[str, str]] = []
        try:
            with open(airodump_csv_file, "r", encoding='utf-8', errors='ignore') as f:
                csv_reader = csv.reader(f) # Use csv module for robustness
                
                ap_section = True
                for row in csv_reader:
                    if not row or not row[0].strip(): continue # Skip blank rows or rows with empty first column

                    if row[0].strip() == "Station MAC": # Start of the client section
                        ap_section = False
                        continue
                    if not ap_section: continue # We only care about APs for now

                    if row[0].strip() == "BSSID": # Skip header for APs
                        continue

                    # Expected fields: BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
                    # Indices:         0    , 1           , 2          , 3      , 4    , 5       , 6     , 7             , 8    , 9        , 10 , 11    , 12       , 13   , 14
                    
                    # Basic check for enough parts for an AP line before accessing indices
                    if len(row) < 14: # ESSID is typically the 14th field (index 13)
                        self.logger.debug(f"[NetworkScanner] Skipping malformed Airodump-ng AP row: {row}")
                        continue

                    bssid = row[0].strip()
                    channel = row[3].strip()
                    privacy = row[5].strip()
                    power = row[8].strip()
                    essid_raw = row[13].strip()

                    # Filter out "hidden" SSIDs (empty or with null bytes)
                    if not essid_raw or '\x00' in essid_raw:
                        essid_display = "<Hidden SSID>"
                    else:
                        essid_display = essid_raw
                    
                    # Apply security filter (case-insensitive check)
                    if network_security_filter.upper() in privacy.upper():
                        networks.append({
                            "bssid": bssid,
                            "channel": channel,
                            "essid": essid_display,
                            "essid_raw": essid_raw,
                            "privacy": privacy,
                            "power": power # Stored as string, convert to int for sorting later
                        })
        except Exception as e:
            self.logger.error(f"[NetworkScanner] Failed to parse airodump-ng CSV output: {e}")
            networks = [] # Clear networks if parsing failed
        finally:
            # Clean up all airodump-ng generated files regardless of success
            for f_to_clean in airodump_log_files_to_clean:
                if os.path.exists(f_to_clean):
                    try:
                        os.remove(f_to_clean)
                        self.logger.debug(f"[NetworkScanner] Removed temp file: {f_to_clean}")
                    except OSError as e_remove:
                        self.logger.warning(f"[NetworkScanner] Could not remove temp file {f_to_clean}: {e_remove}")


        if not networks:
            self.logger.warning(f"[NetworkScanner] No networks matching filter '{network_security_filter}' found after scan.")
            return []

        # Sort networks by power (descending) if power info is available
        try:
            # Convert power to int for reliable sorting, default to a very low number if conversion fails
            networks.sort(key=lambda x: int(x.get("power", "-100").replace(',', '')), reverse=True) # .replace(',', '') for power values like "-45,"
        except ValueError:
            self.logger.warning("[NetworkScanner] Could not sort networks by power due to non-integer power values.")

        return networks