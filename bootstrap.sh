#!/bin/bash

echo "🔧 Bootstrapping CapGate Development Environment..."

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run start_up.sh first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
REQ_FILE="capgate/requirements.txt"
if [ -f "$REQ_FILE" ]; then
    echo "📦 Installing dependencies from $REQ_FILE..."
    pip install -r "$REQ_FILE"
else
    echo "⚠️  No requirements.txt found. Skipping dependency installation."
fi

# Install and configure pre-commit
if [ -f ".pre-commit-config.yaml" ]; then
    echo "🔗 Installing and configuring pre-commit hooks..."
    pip install pre-commit
    pre-commit install
    echo "✅ Pre-commit installed and hooks activated."
fi

echo ""
echo "✅ Environment setup complete!"
echo ""
echo "🧪 Test your setup:"
echo "  source .venv/bin/activate"
echo "  python capgate/run.py"
echo "  git commit -m 'Test hooks' to see pre-commit in action"
