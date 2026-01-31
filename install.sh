#!/bin/bash
# ScienceClaw Installer
#
# One-line install (full setup):
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash
#
# Skip OpenClaw install (if already installed):
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash -s -- --skip-openclaw
#
# Custom agent name:
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash -s -- --name "MyBot-7"
#
# Interactive setup (customize agent profile):
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash -s -- --interactive

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
SKIP_OPENCLAW=false
AGENT_NAME=""
INTERACTIVE=false
START=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-openclaw)
            SKIP_OPENCLAW=true
            shift
            ;;
        --name|-n)
            AGENT_NAME="$2"
            shift 2
            ;;
        --interactive|-i)
            INTERACTIVE=true
            shift
            ;;
        --start)
            START=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║   🦀 ScienceClaw Installer 🧬                             ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║   Autonomous science agents for biology                   ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# Step 1: Install OpenClaw (if not skipped)
# =============================================================================

if [ "$SKIP_OPENCLAW" = false ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Step 1: Installing OpenClaw${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Check if OpenClaw is already installed
    if command -v openclaw &> /dev/null; then
        echo -e "${GREEN}✓ OpenClaw is already installed${NC}"
        openclaw --version 2>/dev/null || true
    else
        # Check for Node.js
        if ! command -v node &> /dev/null; then
            echo -e "${RED}Error: Node.js is not installed${NC}"
            echo ""
            echo "OpenClaw requires Node.js >= 22. Install it first:"
            echo ""
            echo "  macOS:   brew install node"
            echo "  Ubuntu:  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs"
            echo "  Other:   https://nodejs.org/en/download/"
            echo ""
            exit 1
        fi

        # Check Node version
        NODE_VERSION=$(node --version | sed 's/v//' | cut -d'.' -f1)
        if [ "$NODE_VERSION" -lt 22 ]; then
            echo -e "${RED}Error: Node.js version $NODE_VERSION is too old${NC}"
            echo "OpenClaw requires Node.js >= 22"
            echo ""
            echo "Update Node.js:"
            echo "  macOS:   brew upgrade node"
            echo "  nvm:     nvm install 22 && nvm use 22"
            echo ""
            exit 1
        fi

        echo -e "${YELLOW}Installing OpenClaw via npm...${NC}"
        sudo npm install -g openclaw@latest

        if command -v openclaw &> /dev/null; then
            echo -e "${GREEN}✓ OpenClaw installed successfully${NC}"
        else
            echo -e "${RED}Error: OpenClaw installation failed${NC}"
            exit 1
        fi
    fi

    # Run OpenClaw onboarding (if not already done)
    echo ""
    echo -e "${YELLOW}Running OpenClaw onboarding...${NC}"
    echo -e "${YELLOW}(This will set up your workspace and daemon)${NC}"
    echo ""

    # Check if already onboarded by looking for config
    if [ -f "$HOME/.openclaw/openclaw.json" ]; then
        echo -e "${GREEN}✓ OpenClaw already configured${NC}"
    else
        # Redirect stdin from /dev/tty to allow interactive input in piped scripts
        echo -e "${YELLOW}OpenClaw needs to be configured. Running onboarding...${NC}"
        echo -e "${YELLOW}(You'll need to answer a few questions)${NC}"
        echo ""
        openclaw onboard --install-daemon < /dev/tty
        echo -e "${GREEN}✓ OpenClaw onboarding complete${NC}"
    fi

    echo ""
fi

# =============================================================================
# Step 2: Install ScienceClaw
# =============================================================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Step 2: Installing ScienceClaw Skills${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Default install directory (OpenClaw workspace skills directory)
OPENCLAW_SKILLS_DIR="$HOME/.openclaw/workspace/skills"
INSTALL_DIR="${SCIENCECLAW_DIR:-$HOME/scienceclaw}"

# Check if already installed
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}ScienceClaw found at $INSTALL_DIR${NC}"
    echo "Updating..."
    cd "$INSTALL_DIR"
    git pull --quiet 2>/dev/null || true
else
    # Clone repository
    echo -e "${YELLOW}Cloning ScienceClaw...${NC}"

    if ! command -v git &> /dev/null; then
        echo -e "${RED}Error: git is not installed${NC}"
        echo "Please install git and try again."
        exit 1
    fi

    git clone --quiet https://github.com/lamm-mit/scienceclaw.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    echo -e "${GREEN}✓ Cloned to $INSTALL_DIR${NC}"
fi

# Check Python
echo ""
echo -e "${YELLOW}Checking Python...${NC}"

if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

VERSION=$($PYTHON --version 2>&1)
echo -e "${GREEN}✓ $VERSION${NC}"

# Create virtual environment and install dependencies
echo ""
echo -e "${YELLOW}Creating virtual environment...${NC}"
VENV_DIR="$INSTALL_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    # Try to create venv, install python3-venv if needed (Debian/Ubuntu)
    if ! $PYTHON -m venv "$VENV_DIR" 2>/dev/null; then
        echo -e "${YELLOW}Installing python3-venv package...${NC}"
        # Get Python version for package name (e.g., python3.13-venv)
        PY_VERSION=$($PYTHON --version | grep -oE '[0-9]+\.[0-9]+')
        sudo apt-get update -qq
        sudo apt-get install -y "python${PY_VERSION}-venv" >/dev/null 2>&1 || \
            sudo apt-get install -y python3-venv >/dev/null 2>&1 || true
        $PYTHON -m venv "$VENV_DIR"
    fi
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Use venv Python and pip
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

# Install Python dependencies
echo ""
echo -e "${YELLOW}Installing Python dependencies...${NC}"
$PIP install -r requirements.txt --quiet 2>/dev/null || $PIP install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Link skills to OpenClaw workspace (if OpenClaw is installed)
if [ -d "$OPENCLAW_SKILLS_DIR" ]; then
    echo ""
    echo -e "${YELLOW}Linking skills to OpenClaw workspace...${NC}"

    # Link each skill directory
    for skill_dir in "$INSTALL_DIR"/skills/*/; do
        skill_name=$(basename "$skill_dir")
        target="$OPENCLAW_SKILLS_DIR/$skill_name"

        if [ ! -e "$target" ]; then
            ln -s "$skill_dir" "$target" 2>/dev/null || true
            echo "  Linked: $skill_name"
        fi
    done

    echo -e "${GREEN}✓ Skills linked to OpenClaw${NC}"
fi

echo ""

# =============================================================================
# Step 3: Create Agent Profile
# =============================================================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Step 3: Creating Your Science Agent${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$INSTALL_DIR"

if [ "$INTERACTIVE" = true ]; then
    # Full interactive setup - redirect stdin from /dev/tty for piped scripts
    $PYTHON setup.py < /dev/tty
else
    # Quick setup (non-interactive, no stdin needed)
    if [ -n "$AGENT_NAME" ]; then
        $PYTHON setup.py --quick --name "$AGENT_NAME"
    else
        $PYTHON setup.py --quick
    fi
fi

echo ""

# =============================================================================
# Complete!
# =============================================================================

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║   ✓ ScienceClaw Installation Complete!                    ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Installed:"
echo "  • OpenClaw:    $(command -v openclaw 2>/dev/null || echo 'skipped')"
echo "  • ScienceClaw: $INSTALL_DIR"
echo "  • SOUL.md:     ~/.openclaw/workspace/SOUL.md"
echo ""
echo -e "${YELLOW}Start your agent via OpenClaw:${NC}"
echo ""
echo "  # One-shot exploration"
echo "  openclaw agent --message \"Start exploring biology\" --session scienceclaw"
echo ""
echo "  # Specific task"
echo "  openclaw agent --message \"Search PubMed for CRISPR delivery and share on Moltbook\""
echo ""
echo "  # Interactive session"
echo "  openclaw agent --session scienceclaw"
echo ""

# Start agent if requested
if [ "$START" = true ]; then
    echo -e "${CYAN}Starting agent via OpenClaw...${NC}"
    echo ""
    openclaw agent --message "Introduce yourself, explore a biology topic using your science skills, and share any interesting findings on Moltbook" --session scienceclaw
fi

echo -e "${GREEN}Happy exploring! 🔬🧬🦀${NC}"
echo ""
