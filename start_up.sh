#!/bin/bash
#
# CapGate Project Scaffolding Script
#
# This script is used to generate the initial directory and file structure
# for the CapGate project. It should only be run once when starting from an
# empty directory, like this:
# 1. mkdir capgate && cd capgate
# 2. ./start_up.sh
#
# Developers cloning an existing repository should use bootstrap.sh instead.
#

echo "🚀 Scaffolding new CapGate project..."
echo "This script should be run from within your new, empty project directory."

# --- Configuration ---
# Use "." to represent the current directory.
BASE_DIR="."

# Define the source code directory, following modern Python standards.
SRC_DIR="$BASE_DIR/src"

# Define other top-level directories.
CONFIG_DIR_YAML="$BASE_DIR/config" # For user-facing YAML files
SCRIPTS_DIR="$BASE_DIR/scripts"
TESTS_DIR="$BASE_DIR/tests"
VENV_DIR="$BASE_DIR/.venv"
VSC_DIR="$BASE_DIR/.vscode"


# --- 1. Create Core Project Structure ---
echo "🏗️  Creating directory structure..."
# Top-level directories
mkdir -p "$VSC_DIR"
mkdir -p "$CONFIG_DIR_YAML"
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$TESTS_DIR"

# Source code directories
mkdir -p "$SRC_DIR/cli"
mkdir -p "$SRC_DIR/config" # For Python config loading logic
mkdir -p "$SRC_DIR/core"
mkdir -p "$SRC_DIR/helpers"
mkdir -p "$SRC_DIR/plugins" # The "housing" for plugins
mkdir -p "$SRC_DIR/plugin_template/my_new_plugin"

echo "✅ Directory structure created."


# --- 2. Configure VS Code Environment ---
echo "⚙️  Configuring VS Code settings..."
# settings.json: Tells VS Code to use the virtual environment's Python interpreter and find modules in /src.
cat << EOF > "$VSC_DIR/settings.json"
{
    "python.defaultInterpreterPath": "\${workspaceFolder}/.venv/bin/python",
    "python.analysis.extraPaths": [
        "\${workspaceFolder}/src"
    ]
}
EOF

# launch.json: Configures the "Run and Debug" (F5) feature.
cat << EOF > "$VSC_DIR/launch.json"
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: CapGate CLI",
            "type": "python",
            "request": "launch",
            "module": "cli.cli",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "\${workspaceFolder}/src"
            },
            "args": []
        }
    ]
}
EOF

echo "✅ VS Code configured."


# --- 3. Create Virtual Environment and Initial Files ---
echo "🐍 Creating Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created in $VENV_DIR"
else
    echo "ℹ️  Virtual environment already exists."
fi

if [ ! -f "$BASE_DIR/.env" ]; then
    echo "📝 Creating .env file..."
    echo -e "DEBUG=True\nAPI_KEY=dev-placeholder" > "$BASE_DIR/.env"
fi

echo "✍️  Creating placeholder files..."

# --- Top-level project files ---
touch "$BASE_DIR/README.md"
touch "$BASE_DIR/.gitignore"
touch "$BASE_DIR/requirements.txt"
touch "$BASE_DIR/pyproject.toml" # Corrected this line
touch "$BASE_DIR/bootstrap.sh"

# --- User-facing config files ---
touch "$CONFIG_DIR_YAML/default.yaml"
touch "$CONFIG_DIR_YAML/interfaces.yaml"

# --- Source (`src`) files ---
touch "$SRC_DIR/__init__.py"
touch "$SRC_DIR/paths.py"
touch "$SRC_DIR/runner.py"

# `src/cli`
touch "$SRC_DIR/cli/__init__.py"
touch "$SRC_DIR/cli/cli.py"

# `src/config` (Python part)
touch "$SRC_DIR/config/__init__.py"
touch "$SRC_DIR/config/config.py"

# `src/core`
touch "$SRC_DIR/core/__init__.py"
touch "$SRC_DIR/core/context.py"
touch "$SRC_DIR/core/exceptions.py"
touch "$SRC_DIR/core/interface_manager.py"
touch "$SRC_DIR/core/logger.py"
touch "$SRC_DIR/core/plugin_creator.py"
touch "$SRC_DIR/core/plugin_loader.py"

# `src/helpers`
touch "$SRC_DIR/helpers/__init__.py"
touch "$SRC_DIR/helpers/shelltools.py"
touch "$SRC_DIR/helpers/filetools.py"
touch "$SRC_DIR/helpers/nettools.py"
touch "$SRC_DIR/helpers/string_utils.py"

# `src/plugins` and `src/plugin_template`
touch "$SRC_DIR/plugins/__init__.py"
touch "$SRC_DIR/plugin_template/__init__.py"
touch "$SRC_DIR/plugin_template/my_new_plugin/__init__.py"
touch "$SRC_DIR/plugin_template/my_new_plugin/main.py"
touch "$SRC_DIR/plugin_template/my_new_plugin/metadata.json"
touch "$SRC_DIR/plugin_template/my_new_plugin/README.md"

# --- Script files ---
touch "$SCRIPTS_DIR/install.sh"
touch "$SCRIPTS_DIR/update_plugins.sh"
touch "$SCRIPTS_DIR/run_dev.sh"

# --- Test files ---
touch "$TESTS_DIR/__init__.py"
touch "$TESTS_DIR/test_runner.py"

echo "✅ Placeholder files created."


# --- 4. Final Instructions ---
echo ""
echo "🎉 CapGate project scaffolding complete!"
echo ""
echo "Next Steps:"
echo "1. Run './bootstrap.sh' to install all dependencies."
echo "2. Activate the environment with: 'source ./.venv/bin/activate'"
echo "3. Start developing! This directory is ready to be opened in VS Code."

