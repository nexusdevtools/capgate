# src/core/cracking_manager.py
"""
Provides core functionalities for cracking captured network handshakes,
primarily using aircrack-ng.
"""

import os
from typing import Optional

from core.logger import logger
from helpers import shelltools # Assuming shelltools path is correct


class CrackingManager:
    """
    Encapsulates operations related to cracking captured handshakes.
    """
    def __init__(self):
        self.logger = logger

    def crack_wpa_handshake(self, 
                            handshake_file_path: str, 
                            wordlist_path: str
                           ) -> Optional[str]:
        """
        Attempts to crack a WPA/WPA2 handshake using aircrack-ng.

        Args:
            handshake_file_path (str): Full path to the .cap handshake file.
            wordlist_path (str): Full path to the wordlist file.

        Returns:
            Optional[str]: The cracked password if found, None otherwise.
        """
        self.logger.info(f"[CrackingManager] Starting cracking attempt for {handshake_file_path} using {wordlist_path}...")

        if not os.path.exists(handshake_file_path):
            self.logger.error(f"[CrackingManager] Handshake file not found: {handshake_file_path}")
            return None
        if not os.path.exists(wordlist_path):
            self.logger.error(f"[CrackingManager] Wordlist file not found: {wordlist_path}")
            return None

        cracked_password: Optional[str] = None
        try:
            # aircrack-ng command: aircrack-ng -w <wordlist> <handshake_file>
            # Add -b <bssid> for targeted cracking if BSSID is known and aircrack-ng supports it for filtering.
            # For simplicity, we'll assume handshake file is already filtered or general cracking.
            cmd = ["aircrack-ng", "-w", wordlist_path, handshake_file_path]
            
            self.logger.debug(f"[CrackingManager] Executing aircrack-ng: {' '.join(cmd)}")
            
            # Use shelltools.run_command which handles subprocess.run
            # set check=False as aircrack-ng might exit with non-zero on "no key found" which isn't an error for us.
            result_output = shelltools.run_command(cmd, require_root=False, check=False) 

            # Parse output for "KEY FOUND!"
            if "KEY FOUND!" in result_output:
                for line in result_output.splitlines():
                    if "KEY FOUND!" in line:
                        # Example: KEY FOUND! [ the_password ]
                        # Or: KEY FOUND! [1234567890] (hex)
                        match = re.search(r"KEY FOUND!\s+\[\s*(.+?)\s*\]", line)
                        if match:
                            cracked_password = match.group(1).strip()
                            self.logger.info(f"[✓] Password cracked: {cracked_password}")
                            break # Found the password, exit loop
                if not cracked_password: # If KEY FOUND! was there but couldn't parse
                    self.logger.warning("[CrackingManager] 'KEY FOUND!' detected, but could not parse password from line.")
            else:
                self.logger.info(f"[CrackingManager] Password not found in handshake file using {wordlist_path}.")

        except FileNotFoundError:
            self.logger.error("[CrackingManager] aircrack-ng command not found. Please ensure it's installed and in your PATH.")
        except Exception as e:
            self.logger.error(f"[CrackingManager] An error occurred during cracking: {e}")
        
        return cracked_password