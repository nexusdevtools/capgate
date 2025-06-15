# CapGate — Wireless Attack Automation Toolkit

> From survival to cybersecurity — building tools that break barriers.

---

CapGate is a modular automation toolkit for wireless attacks, designed to streamline red team operations. Built from scratch using Python, Bettercap, and real-world recon workflows.

## 👤 About Me

I’ve spent most of my life surviving—homeless, locked up, and invisible. One relationship changed everything—it introduced me to the dark side of tech: cyberstalking, spyware, and emotional manipulation. I didn’t have a degree. I didn’t have money. But I had *fire* and *time*. I taught myself dev tooling and cybersecurity from the ground up.

Now, I build tools like CapGate for the people on the frontlines—people like me who don’t come from privilege but build with purpose.

---

## 💸 Support My Work

If this project speaks to you, if my story resonates, or if you want to help fund a comeback — here’s how you can support me:

- 🧋 [Buy Me a Ko-fi](https://ko-fi.com/YOURNAME) *(Support with $1 or more)*
- 💬 Reach out on [Discord (link coming soon)]()

Your support literally helps me eat, save to sleep under a roof someday soon, and keep building open tools for the hacker community.

---

## ⚙️ Coming Soon

- Interface selection (wlan0, wlan1, etc.)
- Handshake capture automation
- Plugin-based architecture (MITM, Beacon Flood, etc.)
- Full CLI (Typer)

## 📡 CapGate SDR Scanner Module

## Overview

The **CapGate SDR Scanner Module** is the first foundational component of CapGate's upcoming wireless spectrum intelligence suite. It introduces passive spectrum scanning and mapping capabilities using software-defined radios (SDRs), enabling deep visibility into the airspace beyond traditional Wi-Fi.

This module is built with scalability, modularity, and hardware abstraction in mind, and is designed to support both standalone use and tight integration within the broader CapGate CLI and automation ecosystem.

---

## ✅ Key Features

- **Wideband RF Spectrum Scanning**
- **Signal Power Logging to CSV**
- **Waterfall Plot Generation (PNG)**
- **Device Abstraction Layer (RTL-SDR, HackRF, etc.)**
- **Future-Proof Modular Architecture**

---

## 📂 Directory Structure

```plaintext
capgate/
├── airwave/
│   ├── scanners/
│   │   ├── __init__.py
│   │   ├── sdr_spectrum.py          # Entry: full-band scan, waterfall generation
│   │   └── sdr_peak_detector.py     # Detects active frequencies (future)
│   ├── demodulators/
│   │   └── fm_demod.py              # FM broadcast demodulation (future)
│   ├── analyzers/
│   │   └── signal_classifier.py     # ML-based signal ID (future)
│   └── replayers/
│       └── rf_replay.py             # Transmit captured RF (future)
├── configs/
│   └── sdr_config.yaml              # Device settings, freq ranges, logging modes
└── core/
    └── drivers/
        └── sdr_device.py            # Hardware abstraction
```

---

## 🚀 Main Entry Point

A separate entry point can be used to invoke the scanner directly:

```bash
python -m capgate.airwave.scanners.sdr_spectrum
```

---

## 🔗 CLI Integration

Integrated into the CapGate CLI:

```bash
capgate sdr scan         # Triggers spectrum scan
capgate sdr plot         # Plots previous scan file
capgate sdr info         # Shows available SDR devices and status
```

---

## ⚙️ Configuration Example: `sdr_config.yaml`

```yaml
device: rtlsdr
sample_rate: 2400000
gain: auto
band_range:
  start: 50000000
  end: 1700000000
scan_step: 1000000
```

---

## 🔮 Future Roadmap

### Short Term

- ✅ Full-band passive spectrum scanning
- 🔜 Peak detector & heatmap overlays
- 🔜 Device info & capabilities report

### Medium Term

- 🔄 Signal classification via ML (modulation type, known protocols)
- 📡 Basic demodulation (FM, AM, ADS-B, POCSAG, AIS)

### Long Term

- 🚀 Transmit/replay module for HackRF/BladeRF
- 🧠 AI-assisted signal fingerprinting
- 🌐 Web-based real-time spectrum dashboard
- 📦 Plugin API for integrating SDR scans into MITM and network attacks

---

## 📌 Standalone Reusability

This module is built to be imported in other apps:

```python
from capgate.airwave.scanners.sdr_spectrum import scan_spectrum
scan_spectrum()
```

Or used with CLI flags from your own plugin:

```bash
python custom_plugin.py --spectrum-scan --range 400000000:900000000
```

---

## 🧭 Vision

This scanner marks CapGate's first step into the realm of cyber-physical spectrum dominance. By unlocking the airspace as a readable, measurable, and eventually writable medium, CapGate expands from Wi-Fi automation into universal signal intelligence.

Let this module serve as the basecamp for everything that follows.

---

*Made for CapGate. Built to see the unseen.*
