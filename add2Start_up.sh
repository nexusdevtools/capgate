#!/bin/bash
#
# This script safely creates the directory and file structure for the
# new vision, db, and graph components of the CapGate project.
# It can be run multiple times without overwriting existing files.
#
# Assumes you are running it from within the project root directory (e.g., /home/nexus/capgate)

echo "Creating vision directories..."
mkdir -p ./src/vision/scanners

echo "Creating db directories..."
mkdir -p ./src/db/schemas

echo "Creating core graph directories..."
mkdir -p ./src/core/graphs

echo "Creating cli graph files..."
mkdir -p ./src/cli

echo "Creating placeholder files..."
touch ./src/vision/scanners/__init__.py
touch ./src/vision/scanners/arp_scan.py

touch ./src/db/schemas/__init__.py
touch ./src/db/schemas/device.py

touch ./src/core/graphs/__init__.py
touch ./src/core/graphs/topology.py

touch ./src/cli/graph.py

echo "✅ Directory and file structure verified."

