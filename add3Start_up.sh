#!/bin/bash

# Create the SDR module directory structure inside CapGate
mkdir -p capgate/airwave/scanners
mkdir -p capgate/airwave/demodulators
mkdir -p capgate/airwave/analyzers
mkdir -p capgate/airwave/replayers
mkdir -p capgate/core/drivers
mkdir -p capgate/configs
mkdir -p docs/airwave

# Touch initial Python files
touch capgate/airwave/scanners/__init__.py
touch capgate/airwave/scanners/sdr_spectrum.py
touch capgate/airwave/scanners/sdr_peak_detector.py
touch capgate/airwave/demodulators/fm_demod.py
touch capgate/airwave/analyzers/signal_classifier.py
touch capgate/airwave/replayers/rf_replay.py
touch capgate/core/drivers/sdr_device.py
touch capgate/configs/sdr_config.yaml

# Optional starter doc space
touch docs/airwave/integration.md
touch docs/airwave/roadmap.md

echo "✅ CapGate SDR module structure initialized."
