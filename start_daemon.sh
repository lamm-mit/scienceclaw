#!/bin/bash
# Start the ScienceClaw heartbeat daemon
# Works from any ScienceClaw install directory (e.g. ~/scienceclaw or clone path)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting ScienceClaw Heartbeat Daemon..."
echo "  Install dir: $SCRIPT_DIR"
echo ""

# Option 1: Run in background with nohup (simple)
if [ "$1" == "background" ]; then
    nohup python3 "$SCRIPT_DIR/heartbeat_daemon.py" > ~/.scienceclaw/heartbeat_daemon.log 2>&1 &
    PID=$!
    echo $PID > ~/.scienceclaw/heartbeat_daemon.pid
    echo "✓ Daemon started in background (PID: $PID)"
    echo "  Log: ~/.scienceclaw/heartbeat_daemon.log"
    echo "  To stop: $SCRIPT_DIR/stop_daemon.sh"
    echo "  Or: kill \$(cat ~/.scienceclaw/heartbeat_daemon.pid)"
    exit 0
fi

# Option 2: Install as systemd service (recommended)
if [ "$1" == "service" ]; then
    echo "Installing as systemd service..."
    # Generate service file with actual paths for this user/install
    SERVICE_FILE="/tmp/scienceclaw-heartbeat.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=ScienceClaw Heartbeat Daemon
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
ExecStart=$(command -v python3) $SCRIPT_DIR/heartbeat_daemon.py
Restart=always
RestartSec=60
StandardOutput=append:$HOME/.scienceclaw/heartbeat_daemon.log
StandardError=append:$HOME/.scienceclaw/heartbeat_daemon.log
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="HOME=$HOME"

[Install]
WantedBy=multi-user.target
EOF
    sudo cp "$SERVICE_FILE" /etc/systemd/system/scienceclaw-heartbeat.service
    sudo systemctl daemon-reload
    sudo systemctl enable scienceclaw-heartbeat
    sudo systemctl start scienceclaw-heartbeat
    echo ""
    echo "✓ Service installed and started"
    echo ""
    echo "  sudo systemctl status scienceclaw-heartbeat  # Check status"
    echo "  sudo systemctl stop scienceclaw-heartbeat    # Stop daemon"
    echo "  journalctl -u scienceclaw-heartbeat -f      # View logs"
    exit 0
fi

# Option 3: Run one heartbeat and exit (manual / testing)
if [ "$1" == "once" ]; then
    echo "🦞 Running one heartbeat..."
    openclaw agent --message "Run your heartbeat routine: Reply to DMs, post to m/scienceclaw if you have findings, run a short science investigation and share results, then engage with the feed (upvote, comment). Follow the manifesto format." --session-id scienceclaw
    echo "✓ Done"
    exit 0
fi

# Option 4: Run daemon in foreground (Ctrl+C to stop)
echo "Running daemon in foreground (Ctrl+C to stop)..."
echo "  Once:     $0 once"
echo "  Background: $0 background"
echo "  Service:   $0 service"
echo ""
python3 "$SCRIPT_DIR/heartbeat_daemon.py"
