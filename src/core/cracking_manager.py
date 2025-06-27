# src/core/cracking_manager.py
"""
Provides core functionalities for cracking captured network handshakes,
primarily using aircrack-ng.
"""

import os
import re
import gzip
import tempfile
import shlex # <--- Added for run_command fix
from typing import Optional, List

from core.logger import logger
from helpers import shelltools


class CrackingManager:
    """
    Encapsulates operations related to cracking captured handshakes.
    """
    def __init__(self):
        self.logger = logger

    def _get_temp_uncompressed_wordlist_path(self, compressed_path: str) -> Optional[str]:
        """
        Decompresses a gzipped wordlist to a temporary file.
        Returns the path to the uncompressed file, or None on failure.
        """
        temp_path: Optional[str] = None
        try:
            temp_fd, temp_path = tempfile.mkstemp(suffix=".txt", prefix="capgate_wordlist_")
            os.close(temp_fd)

            self.logger.info(f"[CrackingManager] Decompressing '{compressed_path}' to '{temp_path}'...")
            with gzip.open(compressed_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                self.logger.info("[CrackingManager] Decompression complete and temp file verified.")
                return temp_path
            else:
                self.logger.error(f"[CrackingManager] Decompression failed: '{temp_path}' is empty or not created.")
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                return None

        except Exception as e:
            self.logger.error(f"[CrackingManager] Failed to decompress wordlist '{compressed_path}': {e}")
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return None

    def find_wordlist(self, user_provided_path: str) -> Optional[str]:
        """
        Intelligently finds a wordlist path.
        Checks original path, then with common extensions, and decompresses .gz files.

        Args:
            user_provided_path (str): The path provided by the user or default.

        Returns:
            Optional[str]: The absolute path to a usable (uncompressed) wordlist file, or None.
        """
        self.logger.debug(f"[CrackingManager] Attempting to find wordlist from: '{user_provided_path}'")

        potential_paths: List[str] = []
        
        # Add the user-provided path directly (e.g., from --wordlist arg or default)
        potential_paths.append(user_provided_path)
        
        # Add paths with common extensions if not already present
        if not user_provided_path.endswith((".txt", ".gz")):
            potential_paths.append(f"{user_provided_path}.txt")
            potential_paths.append(f"{user_provided_path}.gz")

        # Add your new dedicated wordlist path and its gzipped variant
        # Ensure this is an absolute path or relative from where CapGate is typically run
        capgate_wordlist_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'wordlists')) # /home/nexus/capgate/src/wordlists
        potential_paths.extend([
            os.path.join(capgate_wordlist_base, "wordlist-top4800-probable.txt"),
            os.path.join(capgate_wordlist_base, "wordlist-top4800-probable.txt.gz")
        ])


        # Common Kali Linux rockyou.txt paths
        # Keep these as fallbacks in case the user specified "rockyou.txt"
        if "rockyou" in user_provided_path.lower() or "/usr/share/wordlists" in user_provided_path.lower():
            potential_paths.extend([
                "/usr/share/wordlists/rockyou.txt",
                "/usr/share/wordlists/rockyou.txt.gz",
                "/usr/share/wordlists/rockyou.gz",
                "/usr/share/wordlists/rockyou-wordlist/rockyou.txt",
                "/usr/share/wordlists/rockyou-wordlist/rockyou.txt.gz"
            ])

        # Remove duplicates and normalize paths
        # Using a dict as an ordered set
        unique_paths_dict = {os.path.abspath(p): None for p in potential_paths}
        unique_paths = list(unique_paths_dict.keys())

        for current_path_abs in unique_paths:
            self.logger.debug(f"[CrackingManager] Checking path: '{current_path_abs}'")
            
            if os.path.exists(current_path_abs):
                if not os.path.isfile(current_path_abs):
                    self.logger.debug(f"Path '{current_path_abs}' exists but is not a file.")
                    continue
                
                if not os.access(current_path_abs, os.R_OK):
                    self.logger.warning(f"Wordlist file '{current_path_abs}' exists but is not readable (permission denied).")
                    continue

                if current_path_abs.endswith(".gz"):
                    return self._get_temp_uncompressed_wordlist_path(current_path_abs)
                
                self.logger.info(f"[CrackingManager] Found usable wordlist at: '{current_path_abs}'")
                return current_path_abs
            
        self.logger.error(f"[CrackingManager] Wordlist not found at any expected path after exhaustive search for '{user_provided_path}'.")
        return None


    def crack_wpa_handshake(self, 
                            handshake_file_path: str, 
                            wordlist_path: str
                           ) -> Optional[str]:
        """
        Attempts to crack a WPA/WPA2 handshake using aircrack-ng.

        Args:
            handshake_file_path (str): Full path to the .cap handshake file.
            wordlist_path (str): The initial path to the wordlist file (will be resolved).

        Returns:
            Optional[str]: The cracked password if found, None otherwise.
        """
        self.logger.info(f"[CrackingManager] Starting cracking attempt for {handshake_file_path}...")

        if not os.path.exists(handshake_file_path):
            self.logger.error(f"[CrackingManager] Handshake file not found: {handshake_file_path}")
            return None
        
        actual_wordlist_path = self.find_wordlist(wordlist_path)
        if not actual_wordlist_path:
            return None

        cracked_password: Optional[str] = None
        try:
            # Ensure the command is passed as a list of arguments, not a single string
            cmd_args = ["aircrack-ng", "-w", actual_wordlist_path, handshake_file_path]
            
            self.logger.debug(f"[CrackingManager] Executing aircrack-ng: {shlex.join(cmd_args)}") # Use shlex.join for logging
            
            # CRITICAL FIX: Pass cmd_args (list) to run_command, not a joined string
            result_output = shelltools.run_command(cmd_args, require_root=False, check=False) 

            if "KEY FOUND!" in result_output:
                for line in result_output.splitlines():
                    if "KEY FOUND!" in line:
                        match = re.search(r"KEY FOUND!\s+\[\s*(.+?)\s*\]", line)
                        if match:
                            cracked_password = match.group(1).strip()
                            self.logger.info(f"[✓] Password cracked: {cracked_password}")
                            break
                if not cracked_password:
                    self.logger.warning("[CrackingManager] 'KEY FOUND!' detected, but could not parse password from line.")
            else:
                self.logger.info(f"[CrackingManager] Password not found in handshake file using '{actual_wordlist_path}'.")

        except FileNotFoundError:
            self.logger.error("[CrackingManager] aircrack-ng command not found. Please ensure it's installed and in your PATH.")
        except Exception as e:
            self.logger.error(f"[CrackingManager] An unexpected error occurred during cracking: {e}")
        finally:
            if actual_wordlist_path and actual_wordlist_path.startswith(tempfile.gettempdir()):
                try:
                    os.remove(actual_wordlist_path)
                    self.logger.debug(f"[CrackingManager] Removed temporary wordlist: {actual_wordlist_path}")
                except OSError as e_remove:
                    self.logger.warning(f"[CrackingManager] Could not remove temporary wordlist {actual_wordlist_path}: {e_remove}")
        
        return cracked_password