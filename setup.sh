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
if [ -t 0 ]; then
    # stdin is a terminal
    read -p "Do you want to enable local semantic/vector search? (Requires installing fastembed) [Y/n]: " INSTALL_FAST
else
    # Headless / automated script fallback (e.g. piped curl install without process substitution)
    INSTALL_FAST="Y"
fi

INSTALL_FAST="${INSTALL_FAST:-Y}"

if [[ "$INSTALL_FAST" =~ ^[Yy]$ ]]; then
    echo "Installing Python dependencies (fastembed, numpy)..."
    python3 -m pip install fastembed numpy
    echo "✔ Dependencies installed successfully."
    echo ""
else
    echo "Skipping fastembed installation. The CLI helper will fall back to standard keyword search."
    echo ""
fi

# 3. Run the Python Interactive Vault Init Wizard
if [ -f "synapse.py" ]; then
    # Running from a local cloned repository
    python3 synapse.py init
else
    # Running via one-line curl install (download temporary launcher)
    echo "Downloading Synapse setup wizard..."
    TEMP_DIR=$(mktemp -d)
    curl -fsSL "https://raw.githubusercontent.com/IrakliXYZ/synapse/main/synapse.py" -o "$TEMP_DIR/synapse.py"
    python3 "$TEMP_DIR/synapse.py" init
    rm -rf "$TEMP_DIR"
fi

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
