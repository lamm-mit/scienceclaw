#!/bin/bash
# Start the ScienceClaw heartbeat daemon
#
# Runs autonomous investigation cycles every 6 hours.
#
# Usage:
#   ./start_daemon.sh background  # Run in background
#   ./start_daemon.sh service     # Install as systemd service
#   ./start_daemon.sh once        # Run one cycle and exit

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCIENCECLAW_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Starting ScienceClaw Heartbeat Daemon..."
echo "  ScienceClaw dir: $SCIENCECLAW_DIR"
echo "  Daemon script: $SCRIPT_DIR/heartbeat_daemon.py"
echo ""

MODE="${1:-background}"

case "$MODE" in
    "background")
        echo "Starting daemon in background..."
        cd "$SCIENCECLAW_DIR"
        nohup "$SCIENCECLAW_DIR/.venv/bin/python3" "$SCRIPT_DIR/heartbeat_daemon.py" > ~/.scienceclaw/heartbeat_daemon.log 2>&1 &
        PID=$!
        echo $PID > ~/.scienceclaw/heartbeat_daemon.pid
        echo "✓ Daemon started (PID: $PID)"
        echo "  Log: ~/.scienceclaw/heartbeat_daemon.log"
        echo "  Stop: $SCRIPT_DIR/stop_daemon.sh"
        ;;
    
    "service")
        echo "Installing systemd service..."
        
        cat > /tmp/scienceclaw-heartbeat.service <<EOF
[Unit]
Description=ScienceClaw Autonomous Heartbeat Daemon
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCIENCECLAW_DIR
ExecStart=$SCIENCECLAW_DIR/.venv/bin/python3 $SCRIPT_DIR/heartbeat_daemon.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF
        
        sudo cp /tmp/scienceclaw-heartbeat.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable scienceclaw-heartbeat
        sudo systemctl start scienceclaw-heartbeat
        
        echo "✓ Service installed and started"
        echo "  Status: sudo systemctl status scienceclaw-heartbeat"
        echo "  Logs: journalctl -u scienceclaw-heartbeat -f"
        echo "  Stop: sudo systemctl stop scienceclaw-heartbeat"
        ;;
    
    "once")
        echo "Running one heartbeat cycle..."
        cd "$SCIENCECLAW_DIR"
        "$SCIENCECLAW_DIR/.venv/bin/python3" "$SCRIPT_DIR/heartbeat_daemon.py" --once
        echo "✓ Heartbeat cycle complete"
        ;;
    
    *)
        echo "Usage: $0 {background|service|once}"
        echo ""
        echo "  background  - Run in background (nohup)"
        echo "  service     - Install as systemd service (auto-start on boot)"
        echo "  once        - Run one cycle and exit"
        exit 1
        ;;
esac
