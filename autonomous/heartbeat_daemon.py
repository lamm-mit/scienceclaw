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
import random
import signal
import sys
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
DEFAULT_HEARTBEAT_INTERVAL = 6 * 60 * 60  # 6 hours in seconds
SCIENCECLAW_DIR = Path(__file__).parent.parent  # scienceclaw root (parent of autonomous/)

# Backoff parameters when run_heartbeat() fails. Replaces the previous fixed
# 60s retry, which wasted cycles during transient API outages.
BACKOFF_BASE_SECONDS = 30
BACKOFF_MAX_SECONDS = 1800        # cap individual sleep at 30 min
BACKOFF_FACTOR = 2.0
BACKOFF_JITTER = 0.25
ESCALATE_AFTER_FAILURES = 3       # log at ERROR after this many consecutive misses

# These are set after arg parsing
HEARTBEAT_INTERVAL: int = DEFAULT_HEARTBEAT_INTERVAL
AGENT_PROFILE_NAME: str = ""  # empty = default single-agent path
STATE_FILE: Path = Path.home() / ".scienceclaw" / "heartbeat_state.json"
LOG_FILE: Path = Path.home() / ".scienceclaw" / "heartbeat_daemon.log"

# Make the repo importable so utils.observability is available.
if str(SCIENCECLAW_DIR) not in sys.path:
    sys.path.insert(0, str(SCIENCECLAW_DIR))
from utils.observability import get_logger  # noqa: E402

_LOGGER = None  # configured lazily in _parse_args once LOG_FILE is known


def log(message, *, level: str = "info", **fields):
    """Structured log that also keeps the historical text-log format."""
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = get_logger("scienceclaw.heartbeat", log_file=LOG_FILE)
    fn = getattr(_LOGGER, level, _LOGGER.info)
    if fields:
        fn(message, extra=fields)
    else:
        fn(message)


# Shutdown coordination. The main loop polls _shutdown.is_set() so a SIGTERM
# arriving mid-cycle lets the in-flight heartbeat finish (the file locks
# ensure no torn writes), then exits cleanly before the next iteration.
_shutdown = threading.Event()
_shutdown_reason = "unknown"


def _install_signal_handlers() -> None:
    def _handle(signum, _frame):
        global _shutdown_reason
        _shutdown_reason = {
            signal.SIGTERM: "SIGTERM",
            signal.SIGINT: "SIGINT",
            signal.SIGHUP: "SIGHUP",
        }.get(signum, f"signal {signum}")
        # Use the print fallback because the logger handler might be mid-flush.
        sys.stderr.write(f"\n[shutdown] received {_shutdown_reason}, exiting after current cycle\n")
        sys.stderr.flush()
        _shutdown.set()

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):
            # SIGHUP isn't available everywhere; ignore.
            pass

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
    
    _install_signal_handlers()
    log("signal handlers installed (SIGTERM/SIGINT/SIGHUP)")

    # Main loop. Consecutive-failure counter drives exponential backoff so a
    # transient outage (e.g. Infinite or PubMed flaking) doesn't burn the
    # next scheduled heartbeat window.
    consecutive_failures = 0
    while not _shutdown.is_set():
        try:
            state = load_state()

            if should_run_heartbeat(state):
                log("heartbeat tick")
                success = run_heartbeat()
                now_iso = datetime.now().isoformat()

                if success:
                    consecutive_failures = 0
                    state["lastHeartbeat"] = now_iso
                    state["lastSuccess"] = now_iso
                    state["consecutiveFailures"] = 0
                    save_state(state)
                    next_time = datetime.now() + timedelta(seconds=HEARTBEAT_INTERVAL)
                    log(
                        "heartbeat scheduled",
                        next_run=next_time.strftime("%Y-%m-%d %H:%M:%S"),
                    )

                    # Opportunistic JSONL compaction during idle window.
                    # Only runs when files exceed the size threshold, so
                    # this is a no-op for most cycles.
                    try:
                        from utils.compaction import compact_all_stores
                        result = compact_all_stores()
                        for r in result.get("results", []):
                            if r.get("kept") or r.get("dropped_old") or r.get("dropped_dup"):
                                log(
                                    "compacted",
                                    path=r.get("path", ""),
                                    kept=r.get("kept", 0),
                                    dropped_old=r.get("dropped_old", 0),
                                    dropped_dup=r.get("dropped_dup", 0),
                                )
                    except Exception as _ce:
                        log("compaction error", level="warning", error=str(_ce))
                else:
                    consecutive_failures += 1
                    state["lastFailure"] = now_iso
                    state["consecutiveFailures"] = consecutive_failures
                    save_state(state)

                    delay = min(
                        BACKOFF_BASE_SECONDS * (BACKOFF_FACTOR ** (consecutive_failures - 1)),
                        BACKOFF_MAX_SECONDS,
                    )
                    delay *= 1 + random.uniform(-BACKOFF_JITTER, BACKOFF_JITTER)
                    delay = max(BACKOFF_BASE_SECONDS, delay)

                    level = "error" if consecutive_failures >= ESCALATE_AFTER_FAILURES else "warning"
                    log(
                        "heartbeat failed; backing off",
                        level=level,
                        consecutive_failures=consecutive_failures,
                        retry_in_s=round(delay, 1),
                    )
                    # Wait, but exit early if a shutdown signal arrives.
                    if _shutdown.wait(delay):
                        break
                    continue
            else:
                last_heartbeat = datetime.fromisoformat(state["lastHeartbeat"])
                next_time = last_heartbeat + timedelta(seconds=HEARTBEAT_INTERVAL)
                time_until = (next_time - datetime.now()).total_seconds()
                log(
                    "idle",
                    next_run=next_time.strftime("%H:%M:%S"),
                    seconds_until=int(time_until),
                )

            # Sleep for up to 10 % of the interval (min 10 s, max 600 s) before re-checking
            sleep_secs = min(max(int(HEARTBEAT_INTERVAL * 0.1), 10), 600)
            if _shutdown.wait(sleep_secs):
                break

        except KeyboardInterrupt:
            log("daemon stopped by user")
            _shutdown.set()
            break
        except Exception as e:
            consecutive_failures += 1
            delay = min(
                BACKOFF_BASE_SECONDS * (BACKOFF_FACTOR ** (consecutive_failures - 1)),
                BACKOFF_MAX_SECONDS,
            )
            log(
                "unexpected error",
                level="error",
                error=str(e),
                consecutive_failures=consecutive_failures,
                retry_in_s=round(delay, 1),
            )
            if _shutdown.wait(delay):
                break

    # Persist shutdown reason so `scienceclaw-status` can show it.
    try:
        final_state = load_state()
        final_state["lastShutdown"] = datetime.now().isoformat()
        final_state["lastShutdownReason"] = _shutdown_reason
        save_state(final_state)
    except Exception:
        pass
    log("daemon exited cleanly", reason=_shutdown_reason)

if __name__ == "__main__":
    main()
