#!/bin/bash
# ScienceClaw Installer
#
# PREREQUISITE: OpenClaw must be installed and onboarded first!
#   bash install-openclaw.sh   (or install OpenClaw manually)
#
# Then run this installer:
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash
#
# Custom agent name:
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash -s -- --name "MyBot-7"
#
# Interactive setup (customize agent profile):
#   curl -sSL ... | bash -s -- --interactive
#
# Start heartbeat daemon after install (agent checks Moltbook every 4 hours):
#   curl -sSL ... | bash -s -- --start-heartbeat

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
AGENT_NAME=""
AGENT_PROFILE=""
INTERACTIVE=false
START=false
START_HEARTBEAT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --name|-n)
            AGENT_NAME="$2"
            shift 2
            ;;
        --profile|-p)
            AGENT_PROFILE="$2"
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
        --start-heartbeat)
            START_HEARTBEAT=true
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
# Step 1: Check OpenClaw is installed and configured
# =============================================================================

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Step 1: Checking OpenClaw${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if OpenClaw is installed
if ! command -v openclaw &> /dev/null; then
    echo -e "${RED}Error: OpenClaw is not installed${NC}"
    echo ""
    echo "Please install OpenClaw first:"
    echo ""
    echo "  1. Install Node.js >= 22:"
    echo "     macOS:  brew install node"
    echo "     Ubuntu: curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs"
    echo ""
    echo "  2. Install and configure OpenClaw:"
    echo "     sudo npm install -g openclaw@latest"
    echo "     openclaw onboard --install-daemon"
    echo ""
    echo "  3. Then run this installer again."
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ OpenClaw is installed${NC}"
openclaw --version 2>/dev/null || true

# Check if OpenClaw is configured
if [ ! -f "$HOME/.openclaw/openclaw.json" ]; then
    echo ""
    echo -e "${RED}Error: OpenClaw is not configured${NC}"
    echo ""
    echo "Please run OpenClaw onboarding first:"
    echo ""
    echo "  openclaw onboard --install-daemon"
    echo ""
    echo "Then run this installer again."
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ OpenClaw is configured${NC}"
echo ""

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

# Optional: Set up TDC conda environment (for BBB/hERG/CYP3A4 prediction)
echo ""
echo -e "${YELLOW}Optional: TDC conda environment setup${NC}"
if command -v conda &> /dev/null; then
    if conda info --envs | grep -q "^tdc "; then
        echo -e "${GREEN}✓ conda env 'tdc' already exists${NC}"
    else
        read -p "Create conda env 'tdc' for TDC skill (BBB/hERG/CYP3A4)? (y/n) [n]: " CREATE_TDC
        if [[ "$CREATE_TDC" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Creating conda env 'tdc' with Python 3.11...${NC}"
            conda create -n tdc python=3.11 -y -q
            conda run -n tdc conda install -c dglteam dgl -y -q
            conda run -n tdc conda install -c conda-forge rdkit descriptastorus -y -q
            conda run -n tdc pip install PyTDC DeepPurpose fuzzywuzzy huggingface_hub 'pydantic<2' -q
            echo -e "${GREEN}✓ TDC conda env created${NC}"
        else
            echo -e "${YELLOW}Skipped TDC setup. Install later or see requirements.txt.${NC}"
        fi
    fi
else
    echo -e "${YELLOW}conda not found; skipping TDC env setup. Install conda or see requirements.txt.${NC}"
fi

# Link skills to OpenClaw workspace (if OpenClaw is installed)
if [ -d "$HOME/.openclaw/workspace" ]; then
    echo ""
    echo -e "${YELLOW}Linking skills to OpenClaw workspace...${NC}"

    # Create skills directory if it doesn't exist
    mkdir -p "$OPENCLAW_SKILLS_DIR"

    # Link each skill directory
    for skill_dir in "$INSTALL_DIR"/skills/*/; do
        skill_name=$(basename "$skill_dir")
        target="$OPENCLAW_SKILLS_DIR/$skill_name"

        if [ -e "$target" ]; then
            echo -e "  ${YELLOW}Skipped (exists):${NC} $skill_name"
        else
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
    if [ -n "$AGENT_PROFILE" ]; then
        $PYTHON setup.py --profile "$AGENT_PROFILE" < /dev/tty
    else
        $PYTHON setup.py < /dev/tty
    fi
else
    # Quick setup (non-interactive, no stdin needed)
    SETUP_ARGS="--quick"
    [ -n "$AGENT_PROFILE" ] && SETUP_ARGS="$SETUP_ARGS --profile $AGENT_PROFILE"
    [ -n "$AGENT_NAME" ] && SETUP_ARGS="$SETUP_ARGS --name $AGENT_NAME"
    $PYTHON setup.py $SETUP_ARGS
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
echo "  openclaw agent --message \"Start exploring biology\" --session-id scienceclaw"
echo ""
echo "  # Specific task"
echo "  openclaw agent --message \"Search PubMed for CRISPR delivery and share on Moltbook\""
echo ""
echo "  # Interactive session"
echo "  openclaw agent --session-id scienceclaw"
echo ""

# Start agent if requested
if [ "$START" = true ]; then
    echo -e "${CYAN}Starting agent via OpenClaw...${NC}"
    echo ""
    openclaw agent --message "Introduce yourself, explore a biology topic using your science skills, and share any interesting findings on Moltbook" --session-id scienceclaw
fi

# Start heartbeat daemon so agent checks Moltbook every 4 hours automatically
if [ "$START_HEARTBEAT" = true ]; then
    echo ""
    echo -e "${CYAN}Starting Moltbook heartbeat daemon (checks every 4 hours)...${NC}"
    cd "$INSTALL_DIR"
    ./start_daemon.sh background
    echo -e "${GREEN}✓ Heartbeat daemon running. Agent will check Moltbook every 4 hours.${NC}"
    echo "  To stop: $INSTALL_DIR/stop_daemon.sh"
    echo ""
elif [ -t 0 ]; then
    # Interactive terminal: offer to start heartbeat
    echo -e "${YELLOW}Start Moltbook heartbeat daemon? (agent will check m/scienceclaw every 4 hours) [y/N]:${NC} "
    read -r START_NOW
    if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
        cd "$INSTALL_DIR"
        ./start_daemon.sh background
        echo -e "${GREEN}✓ Heartbeat daemon started.${NC}"
        echo ""
    fi
fi

echo -e "${YELLOW}Moltbook heartbeat:${NC}"
echo "  Your agent can check Moltbook every 4 hours automatically."
echo "  Start daemon:  cd $INSTALL_DIR && ./start_daemon.sh background"
echo "  As service:    cd $INSTALL_DIR && ./start_daemon.sh service"
echo "  Stop:         $INSTALL_DIR/stop_daemon.sh"
echo ""

echo -e "${GREEN}Happy exploring! 🔬🧬🦀${NC}"
echo ""
