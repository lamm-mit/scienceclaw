#!/usr/bin/env python3
"""
ScienceClaw Heartbeat Daemon

Runs continuously in the background and triggers the agent's heartbeat
routine every 4 hours automatically.
"""

import time
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
HEARTBEAT_INTERVAL = 4 * 60 * 60  # 4 hours in seconds
SCIENCECLAW_DIR = Path(__file__).parent
STATE_FILE = Path.home() / ".scienceclaw" / "heartbeat_state.json"
LOG_FILE = Path.home() / ".scienceclaw" / "heartbeat_daemon.log"

def log(message):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    # Also write to log file
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_msg + "\n")

def load_state():
    """Load last heartbeat timestamp."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading state: {e}")
    return {"lastHeartbeat": None}

def save_state(state):
    """Save heartbeat state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def run_heartbeat():
    """Execute the heartbeat routine via openclaw."""
    log("🦞 Running heartbeat routine...")
    
    try:
        # Run openclaw agent with heartbeat message
        result = subprocess.run(
            [
                "openclaw", "agent",
                "--message", """Run your heartbeat routine (every 4 hours):

1. Reply to DMs — Check Moltbook DMs, respond to messages, escalate new requests or needs_human_input to your human.
2. Post — If you have new findings or a hypothesis you tested, post to m/scienceclaw in manifesto format (Hypothesis, Method, Finding, Data, Open question).
3. Investigate — Run a short science investigation (e.g. BLAST, TDC, PubChem, PubMed), then share any interesting result on Moltbook.
4. Engage — Browse m/scienceclaw feed, upvote good posts, comment or peer review where useful.

Follow the m/scienceclaw manifesto. Be evidence-based and cite sources.""",
                "--session-id", "scienceclaw"
            ],
            cwd=SCIENCECLAW_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            log("✓ Heartbeat completed successfully")
            log(f"Output preview: {result.stdout[:200]}...")
            return True
        else:
            log(f"✗ Heartbeat failed with exit code {result.returncode}")
            log(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log("✗ Heartbeat timed out after 5 minutes")
        return False
    except Exception as e:
        log(f"✗ Error running heartbeat: {e}")
        return False

def should_run_heartbeat(state):
    """Check if it's time to run heartbeat."""
    if not state.get("lastHeartbeat"):
        return True
    
    last_heartbeat = datetime.fromisoformat(state["lastHeartbeat"])
    next_heartbeat = last_heartbeat + timedelta(seconds=HEARTBEAT_INTERVAL)
    
    return datetime.now() >= next_heartbeat

def main():
    """Main daemon loop."""
    log("🚀 ScienceClaw Heartbeat Daemon starting...")
    log(f"Heartbeat interval: {HEARTBEAT_INTERVAL / 3600} hours")
    log(f"Working directory: {SCIENCECLAW_DIR}")
    log(f"State file: {STATE_FILE}")
    log(f"Log file: {LOG_FILE}")
    
    # Check if openclaw is available
    try:
        subprocess.run(["openclaw", "--version"], capture_output=True, check=True)
        log("✓ OpenClaw is available")
    except Exception as e:
        log(f"✗ OpenClaw not found: {e}")
        log("Please install OpenClaw: npm install -g openclaw@latest")
        sys.exit(1)
    
    # Main loop
    while True:
        try:
            state = load_state()
            
            if should_run_heartbeat(state):
                log("Time for heartbeat!")
                success = run_heartbeat()
                
                if success:
                    state["lastHeartbeat"] = datetime.now().isoformat()
                    state["lastSuccess"] = datetime.now().isoformat()
                    save_state(state)
                else:
                    state["lastFailure"] = datetime.now().isoformat()
                    save_state(state)
                
                # Calculate next heartbeat time
                next_time = datetime.now() + timedelta(seconds=HEARTBEAT_INTERVAL)
                log(f"Next heartbeat scheduled for: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                last_heartbeat = datetime.fromisoformat(state["lastHeartbeat"])
                next_time = last_heartbeat + timedelta(seconds=HEARTBEAT_INTERVAL)
                time_until = (next_time - datetime.now()).total_seconds()
                log(f"Next heartbeat in {time_until / 3600:.1f} hours at {next_time.strftime('%H:%M:%S')}")
            
            # Sleep for 10 minutes, then check again
            time.sleep(600)
            
        except KeyboardInterrupt:
            log("🛑 Daemon stopped by user")
            break
        except Exception as e:
            log(f"✗ Unexpected error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()
