#!/bin/bash
# OpenClaw Installation Script
#
# Run this FIRST to install and set up OpenClaw:
#   bash install-openclaw.sh
#
# After OpenClaw is ready, run the ScienceClaw installer:
#   curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                           ║${NC}"
echo -e "${CYAN}║   OpenClaw Installation                                   ║${NC}"
echo -e "${CYAN}║                                                           ║${NC}"
echo -e "${CYAN}║   Step 1 of 2: Install OpenClaw framework                 ║${NC}"
echo -e "${CYAN}║                                                           ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

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

echo -e "${GREEN}Node.js $(node --version) detected${NC}"
echo ""

# Check if OpenClaw is already installed
if command -v openclaw &> /dev/null; then
    echo -e "${GREEN}OpenClaw is already installed${NC}"
    openclaw --version 2>/dev/null || true
else
    echo -e "${YELLOW}Installing OpenClaw via npm...${NC}"
    sudo npm install -g openclaw@latest

    if command -v openclaw &> /dev/null; then
        echo -e "${GREEN}OpenClaw installed successfully${NC}"
    else
        echo -e "${RED}Error: OpenClaw installation failed${NC}"
        exit 1
    fi
fi

echo ""

# Check if already onboarded
if [ -f "$HOME/.openclaw/openclaw.json" ]; then
    echo -e "${GREEN}OpenClaw is already configured${NC}"
    echo ""
    echo -e "${GREEN}OpenClaw is ready! Now install ScienceClaw:${NC}"
    echo ""
    echo "  curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash"
    echo ""
    exit 0
fi

# Run onboarding interactively
echo -e "${YELLOW}Running OpenClaw onboarding...${NC}"
echo -e "${YELLOW}This requires interactive input - please follow the prompts.${NC}"
echo ""

openclaw onboard --install-daemon

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║   OpenClaw is ready!                                      ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next step - install ScienceClaw:"
echo ""
echo "  curl -sSL https://raw.githubusercontent.com/lamm-mit/scienceclaw/main/install.sh | bash"
echo ""
