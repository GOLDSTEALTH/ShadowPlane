#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# ShadowPlane Installer
# One-line install:
#   curl -sSL https://raw.githubusercontent.com/GOLDSTEALTH/ShadowPlane/main/install.sh | bash
#
# Requires: Python 3.10+, pip, git
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

banner() {
    echo ""
    echo -e "${CYAN}  ┌─────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}  │         ShadowPlane Installer                │${NC}"
    echo -e "${CYAN}  │   Autonomous Infrastructure Verification     │${NC}"
    echo -e "${CYAN}  └─────────────────────────────────────────────┘${NC}"
    echo ""
}

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${YELLOW}$1${NC}"; }

banner

# ── Preflight ─────────────────────────────────────────────────────────────────
info "[1/4] Checking prerequisites..."

PYTHON_CMD=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" --version 2>&1)
        if [[ "$ver" =~ Python\ 3\.([0-9]+) ]]; then
            minor="${BASH_REMATCH[1]}"
            if [ "$minor" -ge 10 ]; then
                PYTHON_CMD="$candidate"
                ok "$candidate ($ver)"
                break
            fi
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fail "Python 3.10+ is required but not found."
    echo "       Download from: https://www.python.org/downloads/"
    exit 1
fi

# pip
if ! "$PYTHON_CMD" -m pip --version &>/dev/null; then
    fail "pip is not available."
    exit 1
fi
ok "pip"

# git
if ! command -v git &>/dev/null; then
    fail "git is required but not found."
    exit 1
fi
ok "git"

# ── Install ───────────────────────────────────────────────────────────────────
echo ""
info "[2/4] Installing ShadowPlane..."

# Try PyPI first, fall back to GitHub
if "$PYTHON_CMD" -m pip install shadowplane 2>/dev/null; then
    ok "Installed from PyPI"
else
    warn "PyPI package not found, installing from GitHub..."
    "$PYTHON_CMD" -m pip install "git+https://github.com/GOLDSTEALTH/ShadowPlane.git"
    if [ $? -ne 0 ]; then
        fail "Installation failed."
        exit 1
    fi
    ok "Installed from GitHub"
fi

# ── Verify ────────────────────────────────────────────────────────────────────
echo ""
info "[3/4] Verifying installation..."

for cmd in shadowplane shadowplane-server shadowplane-engine; do
    if command -v "$cmd" &>/dev/null; then
        ok "$cmd"
    else
        warn "$cmd not found in PATH"
    fi
done

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
info "[4/4] Installation complete!"
echo ""
echo -e "  ${NC}Available commands:${NC}"
echo -e "    ${CYAN}shadowplane${NC}             Run the verification pipeline"
echo -e "    ${CYAN}shadowplane-server${NC}      Start the MCP gateway server"
echo -e "    ${CYAN}shadowplane-engine${NC}      Run the enterprise engine"
echo ""
echo -e "  ${NC}Quick start:${NC}"
echo -e "    ${CYAN}shadowplane --help${NC}"
echo -e "    ${CYAN}shadowplane --target-dir ./your-infra${NC}"
echo ""
