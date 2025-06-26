# src/core/cracking_manager.py
"""
Provides core functionalities for cracking captured network handshakes,
primarily using aircrack-ng.
"""

import os
import re
import gzip # For decompressing gzipped wordlists
import tempfile # For creating temporary uncompressed wordlist files
from typing import Optional

from core.logger import logger
from helpers import shelltools # Assuming shelltools path is correct


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
        try:
            temp_fd, temp_path = tempfile.mkstemp(suffix=".txt", prefix="capgate_wordlist_")
            os.close(temp_fd) # Close file descriptor as gzip will open it by path

            self.logger.info(f"[CrackingManager] Decompressing {compressed_path} to {temp_path}...")
            with gzip.open(compressed_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            self.logger.info("[CrackingManager] Decompression complete.")
            return temp_path
        except Exception as e:
            self.logger.error(f"[CrackingManager] Failed to decompress wordlist {compressed_path}: {e}")
            return None

    def find_wordlist(self, user_provided_path: str) -> Optional[str]:
        """
        Intelligently finds a wordlist path.
        Checks original path, then with .txt, .gz extensions.
        Decompresses .gz files to a temporary location.

        Args:
            user_provided_path (str): The path provided by the user or default.

        Returns:
            Optional[str]: The absolute path to a usable (uncompressed) wordlist file, or None.
        """
        checked_paths: list[str] = []

        # 1. Check the path as is
        if os.path.exists(user_provided_path):
            checked_paths.append(user_provided_path)
            if user_provided_path.endswith(".gz"):
                return self._get_temp_uncompressed_wordlist_path(user_provided_path)
            self.logger.debug(f"[CrackingManager] Found wordlist at: {user_provided_path}")
            return user_provided_path

        # 2. Try appending .txt
        path_txt = f"{user_provided_path}.txt"
        if os.path.exists(path_txt):
            checked_paths.append(path_txt)
            self.logger.debug(f"[CrackingManager] Found wordlist at: {path_txt}")
            return path_txt

        # 3. Try appending .gz
        path_gz = f"{user_provided_path}.gz"
        if os.path.exists(path_gz):
            checked_paths.append(path_gz)
            self.logger.debug(f"[CrackingManager] Found compressed wordlist at: {path_gz}")
            return self._get_temp_uncompressed_wordlist_path(path_gz)

        # 4. Try common default locations if rockyou.txt
        if "rockyou.txt" in user_provided_path.lower():
            common_rockyou_paths = [
                "/usr/share/wordlists/rockyou.txt",
                "/usr/share/wordlists/rockyou.txt.gz",
                "/usr/share/wordlists/rockyou.gz" # Common alternative for compressed
            ]
            for rp in common_rockyou_paths:
                if os.path.exists(rp):
                    self.logger.debug(f"[CrackingManager] Found rockyou.txt at common path: {rp}")
                    if rp.endswith(".gz"):
                        return self._get_temp_uncompressed_wordlist_path(rp)
                    return rp
                checked_paths.append(rp)

        self.logger.error(f"[CrackingManager] Wordlist not found at any checked path. Attempted: {', '.join(checked_paths)}")
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
        
        # CRITICAL FIX: Resolve wordlist path and decompress if necessary
        actual_wordlist_path = self.find_wordlist(wordlist_path)
        if not actual_wordlist_path:
            # Error message already logged by find_wordlist
            return None

        cracked_password: Optional[str] = None
        try:
            cmd = ["aircrack-ng", "-w", actual_wordlist_path, handshake_file_path]
            
            self.logger.debug(f"[CrackingManager] Executing aircrack-ng: {' '.join(cmd)}")
            
            result_output = shelltools.run_command(' '.join(cmd), require_root=False, check=False) 

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
                self.logger.info(f"[CrackingManager] Password not found in handshake file using {actual_wordlist_path}.")

        except FileNotFoundError:
            self.logger.error("[CrackingManager] aircrack-ng command not found. Please ensure it's installed and in your PATH.")
        except Exception as e:
            self.logger.error(f"[CrackingManager] An unexpected error occurred during cracking: {e}")
        finally:
            # Clean up the temporary uncompressed wordlist if one was created
            if actual_wordlist_path and actual_wordlist_path.startswith(tempfile.gettempdir()):
                try:
                    os.remove(actual_wordlist_path)
                    self.logger.debug(f"[CrackingManager] Removed temporary wordlist: {actual_wordlist_path}")
                except OSError as e_remove:
                    self.logger.warning(f"[CrackingManager] Could not remove temporary wordlist {actual_wordlist_path}: {e_remove}")
        
        return cracked_password