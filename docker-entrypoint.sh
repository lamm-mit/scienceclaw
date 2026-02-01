#!/bin/bash
# Docker entrypoint for ScienceClaw agent
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                           ║${NC}"
echo -e "${CYAN}║   🦀 ScienceClaw Agent Container                          ║${NC}"
echo -e "${CYAN}║                                                           ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

cd /home/sciencebot/scienceclaw

# Check if OpenClaw is configured
if [ ! -f "$HOME/.openclaw/openclaw.json" ]; then
    echo -e "${YELLOW}First-time setup: Configuring OpenClaw...${NC}"
    echo ""
    echo "This requires interactive input. Please follow the prompts."
    echo ""
    
    # Run OpenClaw onboarding
    openclaw onboard --install-daemon
    
    echo ""
    echo -e "${GREEN}✓ OpenClaw configured${NC}"
fi

# Check if agent profile exists
if [ ! -f "$HOME/.scienceclaw/agent_profile.json" ]; then
    echo ""
    echo -e "${YELLOW}Creating agent profile...${NC}"
    
    # Use quick setup with optional custom name
    if [ -n "$AGENT_NAME" ]; then
        .venv/bin/python setup.py --quick --name "$AGENT_NAME"
    else
        .venv/bin/python setup.py --quick
    fi
    
    echo ""
    echo -e "${GREEN}✓ Agent profile created${NC}"
fi

# Link skills to OpenClaw workspace if not already linked
if [ ! -L "$HOME/.openclaw/workspace/skills/uniprot" ]; then
    echo ""
    echo -e "${YELLOW}Linking skills to OpenClaw...${NC}"
    
    mkdir -p "$HOME/.openclaw/workspace/skills"
    
    for skill_dir in /home/sciencebot/scienceclaw/skills/*/; do
        skill_name=$(basename "$skill_dir")
        target="$HOME/.openclaw/workspace/skills/$skill_name"
        
        if [ ! -e "$target" ]; then
            ln -s "$skill_dir" "$target"
        fi
    done
    
    echo -e "${GREEN}✓ Skills linked${NC}"
fi

# Display agent info
if [ -f "$HOME/.scienceclaw/agent_profile.json" ]; then
    echo ""
    echo -e "${CYAN}Agent Profile:${NC}"
    AGENT_NAME=$(cat "$HOME/.scienceclaw/agent_profile.json" | grep -o '"name": "[^"]*"' | cut -d'"' -f4)
    AGENT_BIO=$(cat "$HOME/.scienceclaw/agent_profile.json" | grep -o '"bio": "[^"]*"' | cut -d'"' -f4)
    echo "  Name: $AGENT_NAME"
    echo "  Bio:  $AGENT_BIO"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Ready to explore science! 🔬🧬                          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Handle different commands
case "$1" in
    start)
        echo "Starting agent..."
        echo ""
        exec openclaw agent --message "Start exploring biology" --session-id scienceclaw
        ;;
    interactive)
        echo "Starting interactive session..."
        echo ""
        exec openclaw agent --session-id scienceclaw
        ;;
    bash)
        echo "Starting bash shell..."
        echo ""
        exec /bin/bash
        ;;
    *)
        # Custom command
        exec "$@"
        ;;
esac
