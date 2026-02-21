#!/usr/bin/env python3
"""
ScienceClaw Heartbeat Daemon

Runs continuously in the background and triggers the agent's heartbeat
routine every 6 hours automatically.

Uses the autonomous loop controller for full scientific investigation
cycles instead of simple OpenClaw prompts.
"""

import time
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
HEARTBEAT_INTERVAL = 6 * 60 * 60  # 6 hours in seconds
SCIENCECLAW_DIR = Path(__file__).parent.parent  # scienceclaw root (parent of autonomous/)
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
    """Load agent profile from config."""
    profile_file = Path.home() / ".scienceclaw" / "agent_profile.json"
    if not profile_file.exists():
        log("⚠ No agent profile found. Run setup.py to create one.")
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

def main():
    """Main daemon loop."""
    log("🚀 ScienceClaw Heartbeat Daemon starting...")
    log(f"Heartbeat interval: {HEARTBEAT_INTERVAL / 3600} hours")
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
