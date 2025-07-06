# iOS Lab (CapGate Plugin-Ready)

This lab is structured directly inside CapGate as a plugin under `capgate.plugins.ios_lab`.

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
```bash
ideviceinfo | tee /home/nexus/capgate/src/ios_lab/logs/device_$(date +%Y%m%d).txt
```

### Start iproxy + SSH
```bash
iproxy 2222 22
ssh root@localhost -p 2222
```

### Trace with Frida
```bash
frida-trace -n TARGET_APP -s /home/nexus/capgate/src/ios_lab/frida/trace_openurl.js
```

## Plugin Goals

This lab is designed to support:
- Automated Frida injection via CapGate plugin loader
- MDM profile delivery via phishing or USB profile injection
- Passive and active recon modules (Wi-Fi, device info, etc.)
