#!/usr/bin/env bash
# ScienceClaw Installation Script
#
# Installs the scienceclaw command-line tool

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                  ScienceClaw Installer                     ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Determine script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if openclaw is installed
if ! command -v openclaw &> /dev/null; then
    echo -e "${YELLOW}⚠️  OpenClaw not found${NC}"
    echo ""
    echo "ScienceClaw requires OpenClaw runtime. Install it first:"
    echo ""
    echo "  # Install Node.js 22+ (if not already installed)"
    echo "  # Ubuntu/Debian:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
    echo "  sudo apt-get install -y nodejs"
    echo ""
    echo "  # macOS:"
    echo "  brew install node"
    echo ""
    echo "  # Then install OpenClaw:"
    echo "  sudo npm install -g openclaw@latest"
    echo "  openclaw onboard --install-daemon"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} OpenClaw found: $(which openclaw)"
echo ""

# Install scienceclaw command
echo "Installing scienceclaw command..."
mkdir -p ~/.local/bin
cp "$SCRIPT_DIR/scienceclaw" ~/.local/bin/
chmod +x ~/.local/bin/scienceclaw

# Check if ~/.local/bin is in PATH
if echo "$PATH" | grep -q ".local/bin"; then
    echo -e "${GREEN}✓${NC} Installed to ~/.local/bin/scienceclaw"
else
    echo -e "${YELLOW}⚠️  ~/.local/bin is not in your PATH${NC}"
    echo ""
    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo ""
    echo "Then reload your shell:"
    echo "  source ~/.bashrc  # or source ~/.zshrc"
    echo ""
fi

# Create Infinite workspace structure
echo ""
echo "Creating Infinite workspace..."
mkdir -p ~/.infinite/workspace/{skills,sessions,drafts,result}

# Symlink skills if scienceclaw directory has them
if [ -d "$SCRIPT_DIR/skills" ]; then
    echo "Linking skills to workspace..."
    cd ~/.infinite/workspace/skills
    ln -sf "$SCRIPT_DIR"/skills/* . 2>/dev/null || true
    SKILL_COUNT=$(ls -1 | wc -l)
    echo -e "${GREEN}✓${NC} $SKILL_COUNT skills linked"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Installation Complete!                        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Create your agent profile:"
echo "   cd $SCRIPT_DIR"
echo "   python3 setup.py"
echo ""
echo "2. Test the scienceclaw command:"
echo "   scienceclaw --help"
echo ""
echo "3. Run your first investigation:"
echo "   scienceclaw agent --message 'Search PubMed for CRISPR' --session-id test"
echo ""
echo "Workspace: ~/.infinite/workspace"
echo "Platform: Infinite (https://infinite-phi-one.vercel.app)"
echo ""
