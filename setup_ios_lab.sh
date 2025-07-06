#!/bin/bash

# CapGate iOS Lab Setup Script – Full Plugin Integration Mode
# Author: nexusdevtools | CapGate Training Initiative

set -e

BASE_DIR="/home/nexus/capgate/src/ios_lab"

echo "[+] Creating CapGate iOS lab directory structure at: $BASE_DIR"
mkdir -p "$BASE_DIR"/{bin,logs,profiles,frida,jailbreaks,tmp,notes}

echo "[+] Updating and installing required packages..."
sudo apt update
sudo apt install -y \
    libimobiledevice-utils \
    usbmuxd \
    ideviceinstaller \
    ifuse \
    libplist-utils \
    python3-pip \
    build-essential \
    git \
    curl \
    unzip \
    python3-venv

echo "[+] Installing Frida (latest version)..."
pip3 install --upgrade frida-tools

echo "[+] Cloning essential iOS tooling repos..."
cd "$BASE_DIR/bin"
if [ ! -d "frida-ios-dump" ]; then
    git clone https://github.com/AloneMonkey/frida-ios-dump.git
fi

echo "[+] Setting up usbmuxd service..."
if systemctl list-units --type=service | grep -q usbmuxd; then
    sudo systemctl enable usbmuxd || true
    sudo systemctl start usbmuxd || true
else
    echo "[!] usbmuxd is likely socket-activated or manually managed. Proceeding anyway."
fi

echo "[+] Creating Frida trace hook example..."
cat << 'EOF' > "$BASE_DIR/frida/trace_openurl.js"
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

echo "[+] Writing README and CapGate hook reference..."
cat << EOF > "$BASE_DIR/README.md"
# iOS Lab (CapGate Plugin-Ready)

This lab is structured directly inside CapGate as a plugin under \`capgate.plugins.ios_lab\`.

## Directory Layout

- **bin/** – iOS research tools (Frida dumpers, usbmuxd clients)
- **frida/** – Hook scripts for runtime inspection
- **logs/** – Device info, session logs, Frida traces
- **profiles/** – MDM payloads, Wi-Fi configs, etc.
- **jailbreaks/** – IPA payloads, sideloaders
- **tmp/** – Mounts, recovery data
- **notes/** – Markdown learning, walkthroughs, testing trails

## Example Commands

### Dump iOS Device Info
\`\`\`bash
ideviceinfo | tee $BASE_DIR/logs/device_\$(date +%Y%m%d).txt
\`\`\`

### Start iproxy + SSH
\`\`\`bash
iproxy 2222 22
ssh root@localhost -p 2222
\`\`\`

### Trace with Frida
\`\`\`bash
frida-trace -n TARGET_APP -s $BASE_DIR/frida/trace_openurl.js
\`\`\`

## Plugin Goals

This lab is designed to support:
- Automated Frida injection via CapGate plugin loader
- MDM profile delivery via phishing or USB profile injection
- Passive and active recon modules (Wi-Fi, device info, etc.)
EOF

echo "[+] ✅ CapGate iOS lab plugin folder is ready at: $BASE_DIR"
