# 🧭 CapGate SDR Scanner Development Roadmap

This roadmap defines the stages, milestones, and vision for the CapGate SDR scanner module. It provides clarity for core development, encourages community contributions, and ensures the module grows as a robust tool in both offensive and observational network operations.

---

## 🚦 Phase 1: Initialization (FOUNDATION)

**Goal:** Establish baseline SDR capability within CapGate.

### ✅ Milestones

* [x] Create SDR module directory structure
* [x] Define integration points (CLI, logging, config, device abstraction)
* [x] Write baseline scanner (spectrum scan + waterfall plot)
* [x] YAML config system for scan parameters

### 🔧 Outputs

* `sdr_spectrum.py` with basic scanning + PNG generation
* `sdr_config.yaml`
* CLI integration (`capgate sdr scan`)

### 🎯 Completion Criteria

* Scan from 50 MHz to 1.7 GHz
* Save signal strength CSV per MHz step
* Generate waterfall PNG

---

## ⚙️ Phase 2: Expansion (ANALYSIS & VISIBILITY)

**Goal:** Begin to extract intelligence from captured RF.

### 📌 Milestones

* [ ] Implement peak frequency detection
* [ ] Annotate strongest signals with estimated power/frequency
* [ ] Add scan caching and timestamped session logs
* [ ] Create `sdr_peak_detector.py`
* [ ] Launch `capgate sdr plot --peaks`

### 💡 Additional Concepts

* Frequency heatmap overlays
* Device fingerprinting based on RF behavior

---

## 🧠 Phase 3: Intelligence (SIGNAL UNDERSTANDING)

**Goal:** Classify, decode, and demodulate visible signals.

### 🧩 Milestones

* [ ] Add support for FM/AM demodulation
* [ ] Extract RDS data from FM (station info, metadata)
* [ ] Start ML-based modulation classification
* [ ] Signal fingerprint storage

### 🔍 Example Targets

* FM Radio
* ADS-B (Airplane telemetry)
* AIS (Ship telemetry)
* POCSAG (Pager messages)
* Weather FAX

---

## 🛰️ Phase 4: Interaction (RF REPLAY & REACTION)

**Goal:** Actively engage with the RF environment.

### 🚨 Milestones

* [ ] Integrate HackRF/BladeRF transmission support
* [ ] Build `rf_replay.py` to rebroadcast recorded I/Q
* [ ] Safeguards for legal transmission boundaries
* [ ] Offline replay file support (with timestamped control)

### ⚠️ Compliance

Strict regional restrictions must be followed for TX functionality. Licensing required in many countries.

---

## 🔮 Phase 5: Ecosystem Integration (FULL CAPGATE EMBED)

**Goal:** Tie SDR data into CapGate’s broader network automation and visibility stack.

### 🌐 Milestones

* [ ] Signal triggers as CapGate plugin hooks
* [ ] Shared visualization with MITM or Wi-Fi tools
* [ ] Realtime dashboard (Web + CLI TUI)
* [ ] Bundle as standalone SDR toolkit: `airwave`

---

## 💥 Future Concepts

* RF threat detection
* Spectrum anomaly hunting
* Visual AI for I/Q data pattern recognition
* Mobile SDR deployments
* SDR-to-CLI automation bridge for incident response
* Autonomous signal hunting + fingerprinting agents

---

## 🧵 Summary

This roadmap serves as the strategic plan for CapGate’s SDR development. By following these progressive, purpose-driven phases, CapGate evolves into not just a Wi-Fi automation tool — but a full-spectrum network intelligence platform.

Let this be your compass.
Let the signal tell the truth.
