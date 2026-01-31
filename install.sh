#!/bin/bash
# ScienceClaw Installer
#
# One-line install:
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash
#
# Install and create agent:
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash -s -- --setup
#
# Install, create agent with custom name:
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash -s -- --setup --name "MyBot-7"

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
SETUP=false
AGENT_NAME=""
START=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --setup|-s)
            SETUP=true
            shift
            ;;
        --name|-n)
            AGENT_NAME="$2"
            shift 2
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

# Default install directory
INSTALL_DIR="${SCIENCECLAW_DIR:-$HOME/scienceclaw}"

# Check if already installed
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}ScienceClaw found at $INSTALL_DIR${NC}"
    echo "Updating..."
    cd "$INSTALL_DIR"
    git pull --quiet
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

# Check pip
if command -v pip3 &> /dev/null; then
    PIP="pip3"
elif command -v pip &> /dev/null; then
    PIP="pip"
else
    echo -e "${RED}Error: pip is not installed${NC}"
    exit 1
fi

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
$PIP install -r requirements.txt --quiet 2>/dev/null || $PIP install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Quick setup if requested
if [ "$SETUP" = true ]; then
    echo ""
    echo -e "${CYAN}Creating your agent...${NC}"
    echo ""

    if [ -n "$AGENT_NAME" ]; then
        $PYTHON setup.py --quick --name "$AGENT_NAME"
    else
        $PYTHON setup.py --quick
    fi
else
    # Success message without setup
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✓ ScienceClaw installed successfully!                   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Installed to: $INSTALL_DIR"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo ""
    echo "  cd $INSTALL_DIR"
    echo "  python3 setup.py      # Create your agent"
    echo "  python3 agent.py --loop   # Start exploring"
    echo ""
fi

# Start agent if requested
if [ "$START" = true ]; then
    echo ""
    echo -e "${CYAN}Starting agent...${NC}"
    $PYTHON agent.py
fi

echo -e "${GREEN}Happy exploring! 🔬🧬🦀${NC}"
echo ""
