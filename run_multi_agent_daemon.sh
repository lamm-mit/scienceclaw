#!/bin/bash
# Automated Multi-Agent Collaboration Daemon
# Runs multi-agent collaboration cycles on a schedule

set -e

SCIENCECLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$HOME/.scienceclaw/multi_agent_cycles.log"
STATE_FILE="$HOME/.scienceclaw/multi_agent_state.json"
PID_FILE="$HOME/.scienceclaw/multi_agent_daemon.pid"

# Configuration
CYCLE_INTERVAL=${CYCLE_INTERVAL:-3600}  # 1 hour (set to 86400 for daily, 3600 for hourly)
TEST_MODE=${TEST_MODE:-false}

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Logging function
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] $1" | tee -a "$LOG_FILE"
}

# Ensure log file exists
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

log "═══════════════════════════════════════════════════════════"
log "🤖 Multi-Agent Collaboration Daemon"
log "═══════════════════════════════════════════════════════════"

# Parse arguments
case "${1:-start}" in
    start)
        log "Starting daemon..."

        # Check if already running
        if [ -f "$PID_FILE" ]; then
            old_pid=$(cat "$PID_FILE")
            if kill -0 "$old_pid" 2>/dev/null; then
                log "❌ Daemon already running (PID: $old_pid)"
                exit 1
            fi
        fi

        # Save current PID
        echo $$ > "$PID_FILE"
        log "✅ Daemon started (PID: $$)"

        # Main loop
        cycle_count=0
        while true; do
            cycle_count=$((cycle_count + 1))

            log ""
            log "───────────────────────────────────────────────────────────"
            log "🔄 COLLABORATION CYCLE #$cycle_count"
            log "───────────────────────────────────────────────────────────"

            # Run the multi-agent cycle
            cd "$SCIENCECLAW_DIR"
            python3 run_multi_agent_cycle.py >> "$LOG_FILE" 2>&1

            if [ $? -eq 0 ]; then
                log "✅ Cycle #$cycle_count completed successfully"
            else
                log "❌ Cycle #$cycle_count failed"
            fi

            # Calculate next cycle time
            next_time=$(date -d "+$CYCLE_INTERVAL seconds" '+%Y-%m-%d %H:%M:%S')
            log "⏰ Next cycle scheduled: $next_time"

            # In test mode, run immediately; otherwise sleep
            if [ "$TEST_MODE" = "true" ]; then
                log "⚡ TEST MODE: Running next cycle immediately"
                sleep 2
            else
                sleep "$CYCLE_INTERVAL"
            fi
        done
        ;;

    stop)
        if [ ! -f "$PID_FILE" ]; then
            log "❌ Daemon not running (no PID file)"
            exit 1
        fi

        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping daemon (PID: $pid)..."
            kill "$pid"
            rm "$PID_FILE"
            log "✅ Daemon stopped"
        else
            log "⚠️  Daemon not running (PID $pid not found)"
            rm "$PID_FILE"
        fi
        ;;

    status)
        if [ ! -f "$PID_FILE" ]; then
            echo -e "${RED}❌ Daemon not running${NC}"
            exit 1
        fi

        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ Daemon running (PID: $pid)${NC}"
            echo ""
            echo "Recent cycles:"
            tail -20 "$LOG_FILE" | grep -E "(COLLABORATION CYCLE|completed|failed)" || echo "No recent cycles"
        else
            echo -e "${RED}❌ Daemon not running (PID $pid not found)${NC}"
            rm "$PID_FILE" 2>/dev/null
            exit 1
        fi
        ;;

    logs)
        echo -e "${BLUE}📋 Multi-Agent Daemon Logs${NC}"
        echo "File: $LOG_FILE"
        echo ""
        tail -50 "$LOG_FILE"
        ;;

    once)
        log "Running single collaboration cycle..."
        cd "$SCIENCECLAW_DIR"
        python3 run_multi_agent_cycle.py
        ;;

    *)
        echo "Usage: $0 {start|stop|status|logs|once}"
        echo ""
        echo "Commands:"
        echo "  start   - Start daemon (runs collaboration cycles indefinitely)"
        echo "  stop    - Stop daemon"
        echo "  status  - Show daemon status"
        echo "  logs    - View recent logs"
        echo "  once    - Run single cycle and exit"
        echo ""
        echo "Environment Variables:"
        echo "  CYCLE_INTERVAL  - Seconds between cycles (default: 3600/1 hour)"
        echo "  TEST_MODE       - Set to 'true' for immediate cycles"
        echo ""
        echo "Examples:"
        echo "  $0 start                                  # Start daemon"
        echo "  CYCLE_INTERVAL=86400 $0 start            # Daily cycles"
        echo "  TEST_MODE=true $0 start                  # Immediate cycles (for testing)"
        echo "  $0 stop                                   # Stop daemon"
        echo "  $0 status                                 # Check if running"
        echo "  $0 logs                                   # View logs"
        exit 1
        ;;
esac
