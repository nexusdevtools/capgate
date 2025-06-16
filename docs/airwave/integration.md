# 📎 CapGate SDR Integration Guide

## 🎯 Purpose

This document outlines how the CapGate SDR Scanner module integrates into the CapGate ecosystem, both functionally and architecturally. It ensures maintainability and flexibility for future contributors while reinforcing the SDR scanner as a first-class citizen in CapGate’s expanding network automation platform.

---

## 🔌 Integration Points

### 1. CLI Extension

CapGate CLI supports new subcommands via Typer’s dynamic dispatch system.

**Command Group:** `capgate sdr`

**Subcommands:**

```bash
capgate sdr scan         # Run full-band spectrum scan
capgate sdr plot         # Plot last scan
capgate sdr info         # List connected SDR devices
```

**Source File:** `capgate/cli/commands/sdr.py`

```python
@app.command("sdr")
def sdr():
    pass  # Group entry point

@sdr.command("scan")
def scan():
    from capgate.airwave.scanners.sdr_spectrum import scan_spectrum
    scan_spectrum()
```

Add this to your main CLI loader:

```python
from capgate.cli.commands import sdr  # Ensures Typer CLI group is registered
```

---

### 2. Configuration System

Global config YAML: `capgate/configs/sdr_config.yaml`

Loaded by utility method:

```python
from capgate.helpers.config import load_yaml
sdr_config = load_yaml("sdr_config.yaml")
```

Sample contents:

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

### 3. Logging System

Uses global `capgate.logger` to maintain standard logging format:

```python
from capgate.logger import logger
logger.info("Starting SDR scan...")
```

Output is written to CapGate’s standard log files as well as the terminal.

---

### 4. Device Abstraction Layer

File: `capgate/core/drivers/sdr_device.py`

Purpose: abstracts physical SDR devices and handles:

* Initialization
* Sample reading
* Frequency control
* Graceful shutdown

This allows future extension to HackRF, BladeRF, LimeSDR, etc.

---

## 🤝 Compatibility & Reusability

* 📦 **Standalone Import**

  ```python
  from capgate.airwave.scanners.sdr_spectrum import scan_spectrum
  scan_spectrum()
  ```

* 🚀 **Repurposable as a Plugin**
  Can be packaged as a CapGate plugin or even forked into an independent spectrum tool for operators who only need RF monitoring.

* 🧩 **Plugin Hook Potential**
  In future: signal events can trigger CapGate automation plugins (e.g., replay, classify, alert).

---

## ✅ Summary

The CapGate SDR Scanner integrates cleanly with the CLI, logging, config, and plugin-compatible architecture. It operates both independently and as a fully embedded CapGate module, providing the foundation for future SDR-based intelligence capabilities.
