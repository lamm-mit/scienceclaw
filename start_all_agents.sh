#!/bin/bash
#
# Start heartbeat daemons for all 6 agents with anti-lazy safeguards
# Agents: ProteinEngineer, MedicinalChem, MLResearcher, MaterialsScientist, DrugDesigner, ChemistryBot
#

set -e

SCIENCECLAW_DIR="/home/fiona/LAMM/scienceclaw"
AGENTS_DIR="$HOME/.scienceclaw/agents"
PIDS_DIR="$HOME/.scienceclaw/pids"

# Create PID directory
mkdir -p "$PIDS_DIR"

# List of agents to start
AGENTS=(
    "ProteinEngineer"
    "MedicinalChem"
    "MLResearcher"
    "MaterialsScientist"
    "DrugDesigner"
    "ChemistryBot"
)

echo "================================================================================"
echo "🚀 Starting Heartbeat Daemons for 6 Agents"
echo "================================================================================"
echo ""
echo "Anti-Lazy Safeguards Enabled:"
echo "  ✓ No consecutive commenting on same posts (24h cooldown)"
echo "  ✓ Minimum 1-2 comments per cycle required"
echo "  ✓ Diversity tracking across posts"
echo ""

# Function to start one agent
start_agent() {
    local agent_name=$1
    local config_file=""

    # Determine config file path
    if [ "$agent_name" == "ChemistryBot" ]; then
        config_file="$HOME/.scienceclaw/infinite_config.json"
    else
        config_file="$AGENTS_DIR/${agent_name}_config.json"
    fi

    # Check if config exists
    if [ ! -f "$config_file" ]; then
        echo "❌ $agent_name: Config not found at $config_file"
        return 1
    fi

    # Check if already running
    local pid_file="$PIDS_DIR/${agent_name}.pid"
    if [ -f "$pid_file" ]; then
        local existing_pid=$(cat "$pid_file")
        if kill -0 "$existing_pid" 2>/dev/null; then
            echo "⚠️  $agent_name: Already running (PID: $existing_pid)"
            return 0
        else
            echo "   Removing stale PID file..."
            rm "$pid_file"
        fi
    fi

    # Start heartbeat daemon
    echo "🔬 Starting $agent_name..."

    cd "$SCIENCECLAW_DIR"
    nohup python3 autonomous/heartbeat_daemon.py --config "$config_file" \
        > "$HOME/.scienceclaw/logs/${agent_name}_heartbeat.log" 2>&1 &

    local pid=$!
    echo $pid > "$pid_file"

    sleep 2

    # Verify it's still running
    if kill -0 "$pid" 2>/dev/null; then
        echo "   ✅ Started (PID: $pid)"
        echo "   📋 Log: ~/.scienceclaw/logs/${agent_name}_heartbeat.log"
    else
        echo "   ❌ Failed to start (check logs)"
        rm "$pid_file"
        return 1
    fi
}

# Create logs directory
mkdir -p "$HOME/.scienceclaw/logs"

# Start all agents
for agent in "${AGENTS[@]}"; do
    start_agent "$agent"
    echo ""
done

echo "================================================================================"
echo "✅ All Agents Started"
echo "================================================================================"
echo ""
echo "Monitor logs:"
echo "  tail -f ~/.scienceclaw/logs/*_heartbeat.log"
echo ""
echo "Check status:"
echo "  ./status_all_agents.sh"
echo ""
echo "Stop all agents:"
echo "  ./stop_all_agents.sh"
echo ""
