#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "==============================================="
echo "  Synapse Memory Vault Uninstaller             "
echo "==============================================="
echo ""

# 1. Ask for confirmation
read -p "Are you sure you want to uninstall Synapse? [y/N]: " CONFIRM
CONFIRM="${CONFIRM:-N}"

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# 2. Ask for the vault location to clean up
DEFAULT_PATH="$HOME/SynapseVault"
read -p "Enter the absolute path of the Synapse Vault to remove [$DEFAULT_PATH]: " VAULT_PATH
VAULT_PATH="${VAULT_PATH:-$DEFAULT_PATH}"
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"

echo ""
if [ -d "$VAULT_PATH" ]; then
    echo "Found vault at: $VAULT_PATH"
    
    # Check if this is indeed a Synapse vault
    if [ -f "$VAULT_PATH/Tools/synapse.py" ] || [ -f "$VAULT_PATH/README.md" ]; then
        read -p "Do you want to delete the local SQLite database cache (embeddings.db)? [Y/n]: " REMOVE_DB
        REMOVE_DB="${REMOVE_DB:-Y}"
        
        if [[ "$REMOVE_DB" =~ ^[Yy]$ ]]; then
            if [ -f "$VAULT_PATH/Tools/embeddings.db" ]; then
                rm "$VAULT_PATH/Tools/embeddings.db"
                echo "✔ Removed embeddings.db SQLite database cache."
            fi
        fi
        
        read -p "Do you want to delete the Synapse directories and notes (Inbox, Projects, Areas, Resources, Memories, Tools)? WARNING: This will delete your markdown notes! [y/N]: " REMOVE_NOTES
        REMOVE_NOTES="${REMOVE_NOTES:-N}"
        
        if [[ "$REMOVE_NOTES" =~ ^[Yy]$ ]]; then
            echo "Deleting directories..."
            rm -rf "$VAULT_PATH/Inbox"
            rm -rf "$VAULT_PATH/Projects"
            rm -rf "$VAULT_PATH/Areas"
            rm -rf "$VAULT_PATH/Resources"
            rm -rf "$VAULT_PATH/Memories"
            rm -rf "$VAULT_PATH/Tools"
            if [ -f "$VAULT_PATH/README.md" ]; then
                # Remove if it matches Synapse root
                if grep -q "Synapse Memory & Workspace" "$VAULT_PATH/README.md"; then
                    rm "$VAULT_PATH/README.md"
                    echo "✔ Removed root README.md MOC."
                fi
            fi
            echo "✔ Synapse folders and note structure deleted."
            
            # Remove parent directory if empty
            if [ -d "$VAULT_PATH" ] && [ -z "$(ls -A "$VAULT_PATH")" ]; then
                rmdir "$VAULT_PATH"
                echo "✔ Removed empty parent directory: $VAULT_PATH"
            fi
        else
            # Only remove the Tools directory (the script and db)
            echo "Only removing Synapse code integrations..."
            rm -rf "$VAULT_PATH/Tools"
            echo "✔ Removed Tools/ folder (synapse.py and embeddings.db)."
        fi
    else
        echo "Warning: Target folder does not appear to contain a Synapse installation. Skipping directory deletion."
    fi
else
    echo "Vault path '$VAULT_PATH' does not exist. Skipping directory cleanup."
fi

# 3. Offer to uninstall python dependencies
echo ""
read -p "Do you want to uninstall the python fastembed dependency? [y/N]: " UNINSTALL_PIP
UNINSTALL_PIP="${UNINSTALL_PIP:-N}"

if [[ "$UNINSTALL_PIP" =~ ^[Yy]$ ]]; then
    echo "Uninstalling fastembed..."
    python3 -m pip uninstall -y fastembed numpy || true
    echo "✔ Uninstalled Python dependencies."
fi

echo ""
echo "==============================================="
echo "✔ SUCCESS: Synapse has been uninstalled!"
echo "==============================================="
