#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "commands-cli installer"
echo

# Prefer pip install if pip is available
if command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1; then
    PIP="${PIP:-$(command -v pip3 2>/dev/null || command -v pip)}"
    echo "Installing via pip (editable)..."
    "$PIP" install -e "$ROOT_DIR" --quiet
    echo "Installed: $(command -v commands)"
else
    # Fallback: symlink the dev script
    TARGET_DIR="${HOME}/.local/bin"
    TARGET="${TARGET_DIR}/commands"
    mkdir -p "${TARGET_DIR}"
    chmod +x "${ROOT_DIR}/bin/commands"
    ln -sfn "${ROOT_DIR}/bin/commands" "${TARGET}"
    echo "Symlinked: ${TARGET}"
fi

echo
if ! command -v fzf >/dev/null 2>&1; then
    echo "Note: install fzf for the interactive TUI picker."
    echo
fi
echo "Enable the shell wrapper:"
echo "  eval \"\$(commands shell-init)\""
echo
echo "To make it permanent, add this to ~/.bashrc or ~/.zshrc:"
echo "  eval \"\$(commands shell-init)\""
