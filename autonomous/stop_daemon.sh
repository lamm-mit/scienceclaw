#!/bin/bash
# Stop the ScienceClaw heartbeat daemon

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🛑 Stopping ScienceClaw Heartbeat Daemon..."
echo ""

# Check if running as systemd service
if systemctl is-active --quiet scienceclaw-heartbeat 2>/dev/null; then
    echo "Stopping systemd service..."
    sudo systemctl stop scienceclaw-heartbeat
    echo "✓ Service stopped"
    exit 0
fi

# Check if running in background
if [ -f ~/.scienceclaw/heartbeat_daemon.pid ]; then
    PID=$(cat ~/.scienceclaw/heartbeat_daemon.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping background process (PID: $PID)..."
        kill $PID
        rm ~/.scienceclaw/heartbeat_daemon.pid
        echo "✓ Daemon stopped"
        exit 0
    else
        echo "PID file exists but process not running"
        rm ~/.scienceclaw/heartbeat_daemon.pid
    fi
fi

# Try to find and kill by process name
PIDS=$(pgrep -f "heartbeat_daemon.py")
if [ -n "$PIDS" ]; then
    echo "Found daemon process(es): $PIDS"
    echo "Stopping..."
    kill $PIDS
    echo "✓ Daemon stopped"
    exit 0
fi

echo "No daemon found running"
