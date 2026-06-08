#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "==============================================="
echo "  Synapse Memory Vault Setup Wizard            "
echo "==============================================="
echo ""

# 1. Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✔ Found Python 3 (Version $PYTHON_VERSION)"
echo ""

# 2. Ask about local semantic search
read -p "Do you want to enable local semantic/vector search? (Requires installing fastembed) [Y/n]: " INSTALL_FAST
INSTALL_FAST="${INSTALL_FAST:-Y}"

if [[ "$INSTALL_FAST" =~ ^[Yy]$ ]]; then
    echo "Installing dependencies from requirements.txt..."
    python3 -m pip install -r requirements.txt
    echo "✔ Dependencies installed successfully."
    echo ""
else
    echo "Skipping fastembed installation. The CLI helper will fall back to standard keyword search."
    echo ""
fi

# 3. Hand off to the Python Interactive Vault Init Wizard
python3 synapse.py init

echo ""
echo "==============================================="
echo "✔ SUCCESS: Setup complete!"
echo "==============================================="
echo "Your Synapse Memory Vault is configured and ready."
echo "Helper tool deployed to: Tools/synapse.py"
echo ""
echo "To search your vault semantically, run:"
echo "python3 Tools/synapse.py search \"your query\""
echo "==============================================="
