#!/bin/bash
#
# Stop all 6 agent heartbeat daemons
#

PIDS_DIR="$HOME/.scienceclaw/pids"

AGENTS=(
    "ProteinEngineer"
    "MedicinalChem"
    "MLResearcher"
    "MaterialsScientist"
    "DrugDesigner"
    "ChemistryBot"
)

echo "================================================================================"
echo "🛑 Stopping All Agent Heartbeat Daemons"
echo "================================================================================"
echo ""

stopped_count=0
not_running_count=0

for agent in "${AGENTS[@]}"; do
    pid_file="$PIDS_DIR/${agent}.pid"

    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "🛑 Stopping $agent (PID: $pid)..."
            kill "$pid"
            sleep 1

            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo "   Force killing..."
                kill -9 "$pid"
            fi

            rm "$pid_file"
            echo "   ✅ Stopped"
            stopped_count=$((stopped_count + 1))
        else
            echo "⚪ $agent: Not running (removing stale PID)"
            rm "$pid_file"
            not_running_count=$((not_running_count + 1))
        fi
    else
        echo "⚪ $agent: Not running"
        not_running_count=$((not_running_count + 1))
    fi
    echo ""
done

echo "================================================================================"
echo "✅ Stopped: $stopped_count | Not running: $not_running_count"
echo "================================================================================"
echo ""
