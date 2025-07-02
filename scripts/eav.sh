#!/bin/bash

# CapGate iOS Lab Setup Script for Kali Purple
# Author: nexusdevtools | CapGate Training Initiative

set -e

echo "[+] Creating iOS lab directory structure..."
mkdir -p ~/ios-lab/{bin,logs,profiles,frida,jailbreaks,tmp,notes}

echo "[+] Updating and installing required packages..."
sudo apt update
sudo apt install -y \
    libimobiledevice-utils \
    usbmuxd \
    ideviceinstaller \
    ifuse \
    libplist-utils \
    iproxy \
    python3-pip \
    build-essential \
    git \
    curl \
    unzip \
    python3-venv

echo "[+] Installing Frida (latest version)..."
pip3 install --upgrade frida-tools

echo "[+] Cloning essential iOS tooling repos..."

cd ~/ios-lab/bin
if [ ! -d "frida-ios-dump" ]; then
    git clone https://github.com/AloneMonkey/frida-ios-dump.git
fi

echo "[+] Setting up persistent usbmuxd service..."
sudo systemctl enable usbmuxd
sudo systemctl start usbmuxd

echo "[+] Creating Frida trace hook example..."
cat << 'EOF' > ~/ios-lab/frida/trace_openurl.js
// Hook UIApplication openURL on jailbroken device
if (ObjC.available) {
    var UIApplication = ObjC.classes.UIApplication;
    var sharedApp = UIApplication.sharedApplication();

    Interceptor.attach(sharedApp.openURL_.implementation, {
        onEnter: function(args) {
            var url = new ObjC.Object(args[2]);
            console.log("[*] openURL called with: " + url.toString());
        }
    });
}
EOF

echo "[+] Writing README and CapGate hook..."
cat << 'EOF' > ~/ios-lab/README.md
# iOS Lab Setup (CapGate-Ready)

This lab is designed to simulate real-world attacker scenarios using iPhones and iPads.
Structured for future CapGate plugin integration.

## Directories
- **bin/** – Repositories and tools
- **frida/** – Trace scripts, hook templates
- **logs/** – Device info, Frida output, SSH logs
- **profiles/** – Custom .mobileconfig payloads
- **tmp/** – Mounts and dumps
- **notes/** – Markdown writeups

## Core Tools
- Frida
- usbmuxd
- libimobiledevice
- iproxy
- ifuse

## Example: Dump Device Info
```bash
ideviceinfo | tee ~/ios-lab/logs/device_$(date +%Y%m%d).txt
