import os

DEFAULT_WORDLIST = "home/nexus/wifite2/wordlist-top4800-probable.txt"
CAPTURE_DIR = "handshakes"
POTFILE = os.path.expanduser("~/.hashcat/hashcat.potfile")
DEFAULT_CAPTURE_FILE = "handshake.pcap"
DEFAULT_CAPTURE_PATH = os.path.join(CAPTURE_DIR, DEFAULT_CAPTURE_FILE)
