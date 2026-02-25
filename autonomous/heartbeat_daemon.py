#!/usr/bin/env python3
"""
ScienceClaw Heartbeat Daemon

Runs continuously in the background and triggers the agent's heartbeat
routine every 6 hours automatically.

Uses the autonomous loop controller for full scientific investigation
cycles.
"""

import argparse
import time
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
DEFAULT_HEARTBEAT_INTERVAL = 6 * 60 * 60  # 6 hours in seconds
SCIENCECLAW_DIR = Path(__file__).parent.parent  # scienceclaw root (parent of autonomous/)

# These are set after arg parsing
HEARTBEAT_INTERVAL: int = DEFAULT_HEARTBEAT_INTERVAL
AGENT_PROFILE_NAME: str = ""  # empty = default single-agent path
STATE_FILE: Path = Path.home() / ".scienceclaw" / "heartbeat_state.json"
LOG_FILE: Path = Path.home() / ".scienceclaw" / "heartbeat_daemon.log"

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

def platform_configured():
    """Return 'infinite' if Infinite is configured, else False."""
    infinite_config = Path.home() / ".scienceclaw" / "infinite_config.json"
    if infinite_config.exists():
        try:
            with open(infinite_config) as f:
                if json.load(f).get("api_key"):
                    return "infinite"
        except Exception:
            pass
    return False


def load_agent_profile():
    """Load agent profile from config.

    If AGENT_PROFILE_NAME is set, loads from:
        ~/.scienceclaw/profiles/{AGENT_PROFILE_NAME}/agent_profile.json
    Otherwise falls back to the default single-agent path:
        ~/.scienceclaw/agent_profile.json
    """
    if AGENT_PROFILE_NAME:
        profile_file = (
            Path.home() / ".scienceclaw" / "profiles" / AGENT_PROFILE_NAME / "agent_profile.json"
        )
    else:
        profile_file = Path.home() / ".scienceclaw" / "agent_profile.json"

    if not profile_file.exists():
        log(f"⚠ No agent profile found at {profile_file}. Run setup.py to create one.")
        return None

    try:
        with open(profile_file) as f:
            return json.load(f)
    except Exception as e:
        log(f"✗ Error loading agent profile: {e}")
        return None


def run_heartbeat():
    """Execute the heartbeat routine using autonomous loop controller."""
    log("🦞 Running heartbeat routine...")
    
    # Check platform configuration
    platform = platform_configured()
    if not platform:
        log("⚠ No platform configured (Infinite)")
        log("   Run setup.py to configure a platform")
        return False
    
    log(f"✓ Platform configured: {platform}")
    
    # Load agent profile
    agent_profile = load_agent_profile()
    if not agent_profile:
        return False
    
    log(f"✓ Agent profile loaded: {agent_profile.get('name', 'Unknown')}")
    
    try:
        # Import and run autonomous loop controller
        sys.path.insert(0, str(SCIENCECLAW_DIR))
        from autonomous import AutonomousLoopController
        
        # Initialize controller
        controller = AutonomousLoopController(agent_profile)
        
        # Run full heartbeat cycle
        log("Starting autonomous investigation cycle...")
        summary = controller.run_heartbeat_cycle()
        
        # Log results
        steps_completed = summary.get("steps_completed", [])
        duration = summary.get("duration_seconds", 0)
        
        log(f"✓ Heartbeat completed successfully")
        log(f"  Steps completed: {', '.join(steps_completed)}")
        log(f"  Duration: {duration:.1f}s")
        
        if summary.get("gaps_found"):
            log(f"  Gaps found: {summary['gaps_found']}")
        if summary.get("hypotheses_generated"):
            log(f"  Hypotheses generated: {summary['hypotheses_generated']}")
        if summary.get("investigation_id"):
            log(f"  Investigation: {summary['investigation_id']}")
        if summary.get("post_id"):
            log(f"  Post created: {summary['post_id']}")
        
        return True
        
    except ImportError as e:
        log(f"✗ Failed to import autonomous controller: {e}")
        log("   Ensure Phase 3 components are installed")
        return False
    except Exception as e:
        log(f"✗ Error running heartbeat: {e}")
        import traceback
        traceback.print_exc()
        return False

def should_run_heartbeat(state):
    """Check if it's time to run heartbeat."""
    if not state.get("lastHeartbeat"):
        return True

    last_heartbeat = datetime.fromisoformat(state["lastHeartbeat"])
    next_heartbeat = last_heartbeat + timedelta(seconds=HEARTBEAT_INTERVAL)

    return datetime.now() >= next_heartbeat


def _parse_args():
    """Parse CLI arguments and configure globals."""
    global HEARTBEAT_INTERVAL, AGENT_PROFILE_NAME, STATE_FILE, LOG_FILE

    parser = argparse.ArgumentParser(description="ScienceClaw Heartbeat Daemon")
    parser.add_argument(
        "--profile",
        default="",
        help=(
            "Named agent profile to load from "
            "~/.scienceclaw/profiles/<name>/agent_profile.json. "
            "If omitted, uses the default ~/.scienceclaw/agent_profile.json."
        ),
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(DEFAULT_HEARTBEAT_INTERVAL),
        help=(
            "Heartbeat interval in seconds (default: 21600 = 6 hours). "
            "Set to 180 for a 3-minute demo cycle."
        ),
    )
    args = parser.parse_args()

    HEARTBEAT_INTERVAL = args.interval
    AGENT_PROFILE_NAME = args.profile

    # Per-profile state and log files so multiple daemons don't collide
    if AGENT_PROFILE_NAME:
        base = Path.home() / ".scienceclaw" / "profiles" / AGENT_PROFILE_NAME
        base.mkdir(parents=True, exist_ok=True)
        STATE_FILE = base / "heartbeat_state.json"
        LOG_FILE = base / "heartbeat_daemon.log"


def main():
    """Main daemon loop."""
    _parse_args()

    log("🚀 ScienceClaw Heartbeat Daemon starting...")
    if AGENT_PROFILE_NAME:
        log(f"Agent profile: {AGENT_PROFILE_NAME}")
    log(f"Heartbeat interval: {HEARTBEAT_INTERVAL}s ({HEARTBEAT_INTERVAL / 60:.1f} min)")
    log(f"Working directory: {SCIENCECLAW_DIR}")
    log(f"State file: {STATE_FILE}")
    log(f"Log file: {LOG_FILE}")
    
    # Check dependencies
    try:
        # Check for autonomous module
        sys.path.insert(0, str(SCIENCECLAW_DIR))
        from autonomous import AutonomousLoopController
        log("✓ Autonomous loop controller available")
    except ImportError as e:
        log(f"✗ Autonomous controller not found: {e}")
        log("Please ensure autonomous loop components are installed")
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
                log(f"Next heartbeat in {time_until:.0f}s at {next_time.strftime('%H:%M:%S')}")

            # Sleep for up to 10 % of the interval (min 10 s, max 600 s) before re-checking
            sleep_secs = min(max(int(HEARTBEAT_INTERVAL * 0.1), 10), 600)
            time.sleep(sleep_secs)
            
        except KeyboardInterrupt:
            log("🛑 Daemon stopped by user")
            break
        except Exception as e:
            log(f"✗ Unexpected error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()
