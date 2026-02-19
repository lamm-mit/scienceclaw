#!/bin/bash
#
# Check status of all 6 agent heartbeat daemons
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
echo "📊 Agent Heartbeat Status"
echo "================================================================================"
echo ""

running_count=0
stopped_count=0

for agent in "${AGENTS[@]}"; do
    pid_file="$PIDS_DIR/${agent}.pid"

    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "✅ $agent: Running (PID: $pid)"
            running_count=$((running_count + 1))

            # Show comment stats if available
            state_file="$HOME/.scienceclaw/comment_state/${agent}_comment_history.json"
            if [ -f "$state_file" ]; then
                total_comments=$(jq -r '.total_comments // 0' "$state_file" 2>/dev/null || echo "N/A")
                unique_posts=$(jq -r '.commented_posts | length' "$state_file" 2>/dev/null || echo "N/A")
                echo "   📊 Comments: $total_comments total, $unique_posts unique posts"
            fi
        else
            echo "❌ $agent: Stopped (stale PID: $pid)"
            stopped_count=$((stopped_count + 1))
        fi
    else
        echo "⚪ $agent: Not started"
        stopped_count=$((stopped_count + 1))
    fi
    echo ""
done

echo "================================================================================"
echo "Summary: $running_count running, $stopped_count stopped"
echo "================================================================================"
echo ""

if [ $running_count -gt 0 ]; then
    echo "Logs:"
    for agent in "${AGENTS[@]}"; do
        log_file="$HOME/.scienceclaw/logs/${agent}_heartbeat.log"
        if [ -f "$log_file" ]; then
            echo "  tail -f $log_file"
        fi
    done
    echo ""
fi
