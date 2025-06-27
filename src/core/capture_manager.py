# src/core/capture_manager.py
"""
Provides core functionalities for capturing wireless traffic,
including WPA/WPA2 handshakes using airodump-ng and aireplay-ng.
"""

import subprocess
import time
import os
import tempfile
import shlex # <--- ADDED for explicit shlex.join in logging.
from typing import Optional, List # Added List for precise type hints

from core.logger import logger
from helpers import shelltools


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
                                      The actual file will be {prefix}-01.cap.
            capture_time_seconds (int): How long to attempt capturing the handshake.
            deauth_count (int): Number of deauthentication packets to send to force handshake.
            auto_mode (bool): If True, will wait for `capture_time_seconds` automatically.
                              If False, will inform user to press Ctrl+C to stop early.

        Returns:
            Optional[str]: Full path to the captured .cap file if successful, None otherwise.
        """
        self.logger.info(f"[CaptureManager] Starting handshake capture for BSSID {target_bssid} on channel {target_channel} via {monitor_interface}...")

        base_output_path = os.path.join(tempfile.gettempdir(), output_file_prefix)
        final_cap_file_path = f"{base_output_path}-01.cap"
        
        # Files airodump-ng creates (excluding the .cap itself from automatic cleanup loop)
        airodump_auxiliary_files_to_clean: List[str] = [ # Explicitly type as List[str]
            f"{base_output_path}-01.csv", 
            f"{base_output_path}-01.kismet.csv", 
            f"{base_output_path}-01.kismet.netxml", 
            f"{base_output_path}-01.log.csv"
        ]
        
        # Clean up any leftover auxiliary files from previous runs with the same prefix
        for f_to_clean in airodump_auxiliary_files_to_clean:
            if os.path.exists(f_to_clean):
                try:
                    os.remove(f_to_clean)
                    self.logger.debug(f"[CaptureManager] Removed leftover auxiliary temp file: {f_to_clean}")
                except OSError as e_remove:
                    self.logger.warning(f"Could not remove leftover auxiliary temp file {f_to_clean}: {e_remove}")

        # If .cap file from previous run exists, remove it to ensure a fresh capture.
        if os.path.exists(final_cap_file_path):
            try:
                os.remove(final_cap_file_path)
                self.logger.debug(f"[CaptureManager] Removed old .cap file: {final_cap_file_path}")
            except OSError as e_remove:
                self.logger.warning(f"Could not remove old .cap file {final_cap_file_path}: {e_remove}")


        dump_proc: Optional[subprocess.Popen[bytes]] = None
        try:
            # Start airodump-ng in the background to capture traffic
            airodump_cmd: List[str] = [ # Explicitly type as List[str]
                "airodump-ng",
                "--bssid", target_bssid,
                "--channel", target_channel, 
                "--write", base_output_path, # airodump-ng automatically adds -01.cap etc.
                monitor_interface
            ]
            # CRITICAL FIX 1: Pass `airodump_cmd` (list) directly to Popen
            self.logger.debug(f"[CaptureManager] Executing airodump-ng: {shlex.join(airodump_cmd)}")
            dump_proc = subprocess.Popen(airodump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)

            self.logger.info(f"[CaptureManager] Sending {deauth_count} deauth packets to {target_bssid}...")
            aireplay_cmd: List[str] = [ # Explicitly type as List[str]
                "aireplay-ng", 
                "--deauth", str(deauth_count), 
                "-a", target_bssid, 
                monitor_interface
            ]
            # CRITICAL FIX 2: Pass `aireplay_cmd` (list) directly to shelltools.run_command
            self.logger.debug(f"[CaptureManager] Executing aireplay-ng: {shlex.join(aireplay_cmd)}")
            shelltools.run_command(aireplay_cmd, require_root=True, check=False) 

            self.logger.info(f"[CaptureManager] Waiting for handshake capture ({capture_time_seconds}s) in auto mode...")
            
            for _ in range(capture_time_seconds):
                if dump_proc and dump_proc.poll() is not None:
                    self.logger.warning("[CaptureManager] airodump-ng terminated prematurely during capture wait.")
                    break
                time.sleep(1)
            
            self.logger.info("[CaptureManager] Stopping airodump-ng capture...")
            if dump_proc and dump_proc.poll() is None:
                dump_proc.terminate()
                try:
                    dump_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("[CaptureManager] airodump-ng did not terminate gracefully, killing.")
                    dump_proc.kill()
                    dump_proc.wait()
            self.logger.debug("[CaptureManager] Airodump-ng process finished.")

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
            self.logger.error(f"[CaptureManager] An unexpected error occurred during handshake capture: {e}")
            return None
        finally:
            if dump_proc and dump_proc.poll() is None:
                self.logger.warning("[CaptureManager] airodump-ng process was still running in finally block, terminating.")
                dump_proc.terminate()
                try:
                    dump_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    dump_proc.kill()
            
            # Clean up all auxiliary files, but NOT the .cap file
            for f_to_clean in airodump_auxiliary_files_to_clean:
                if os.path.exists(f_to_clean):
                    try:
                        os.remove(f_to_clean)
                        self.logger.debug(f"[CaptureManager] Removed temp auxiliary file: {f_to_clean}")
                    except OSError as e_remove:
                        self.logger.warning(f"Could not remove temp auxiliary file {f_to_clean}: {e_remove}")