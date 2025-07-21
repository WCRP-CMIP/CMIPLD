#!/bin/bash
# install_scripts.sh - Install CMIP-LD shell scripts to user's PATH

set -e

# Determine installation directory
if [[ -n "$VIRTUAL_ENV" ]]; then
    INSTALL_DIR="$VIRTUAL_ENV/bin"
elif [[ -d "$HOME/.local/bin" ]]; then
    INSTALL_DIR="$HOME/.local/bin"
else
    INSTALL_DIR="/usr/local/bin"
fi

echo "Installing CMIP-LD shell scripts to: $INSTALL_DIR"

# Find the cmipld package location
CMIPLD_DIR=$(python -c "import cmipld; import os; print(os.path.dirname(cmipld.__file__))")
SCRIPTS_DIR="$CMIPLD_DIR/scripts"

if [[ ! -d "$SCRIPTS_DIR" ]]; then
    echo "Error: Scripts directory not found at $SCRIPTS_DIR"
    exit 1
fi

# Install scripts
install_script() {
    local script_name="$1"
    local subdir="$2"
    local script_path="$SCRIPTS_DIR/$subdir/$script_name"
    
    if [[ -f "$script_path" ]]; then
        echo "Installing $script_name..."
        cp "$script_path" "$INSTALL_DIR/$script_name"
        chmod +x "$INSTALL_DIR/$script_name"
    else
        echo "Warning: Script $script_path not found"
    fi
}

# Install all scripts
install_script "ld2graph" "directory-utilities"
install_script "validjsonld" "directory-utilities" 
install_script "dev" "directory-utilities"
install_script "rmbak" "jsonld-util"
install_script "rmgraph" "jsonld-util"
install_script "coauthor_file" "development"

echo "✓ Shell scripts installed successfully!"
echo "Make sure $INSTALL_DIR is in your PATH"

# Check if directory is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "⚠️  $INSTALL_DIR is not in your PATH"
    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "export PATH=\"$INSTALL_DIR:\$PATH\""
fi
