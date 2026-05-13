"""
Cost and safety guardrails for a single heartbeat cycle.

Why this exists: a bug in skill selection, an infinite loop in the reactor, or
a runaway hypothesis generator could chew through tokens and wallclock without
bound. CycleBudget gives the loop controller a single object to consult before
expensive operations and a single place to enforce hard limits.

Defaults are intentionally generous — they catch obvious runaways without
hampering normal cycles. Tune via environment variables:
    SCIENCECLAW_MAX_LLM_CALLS         (default 60)
    SCIENCECLAW_MAX_LLM_TOKENS        (default 250_000, approximate)
    SCIENCECLAW_MAX_CYCLE_SECONDS     (default 1800 = 30 min)
    SCIENCECLAW_MAX_SKILL_EXECS       (default 40)

The PAUSE file (~/.scienceclaw/PAUSE) is checked at every budget query — touch
it to make the next budget check raise BudgetExhausted, halting the cycle
without killing the daemon.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .observability import get_logger


PAUSE_FILE = Path.home() / ".scienceclaw" / "PAUSE"


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class CycleBudget:
    """
    Per-cycle resource accountant. Construct one at the start of each
    heartbeat cycle; pass it to subsystems that need to check or charge.

    Thread-safe — counters are guarded by a lock so parallel skill
    execution can charge concurrently.
    """

    max_llm_calls: int = field(default_factory=lambda: _int_env("SCIENCECLAW_MAX_LLM_CALLS", 60))
    max_llm_tokens: int = field(default_factory=lambda: _int_env("SCIENCECLAW_MAX_LLM_TOKENS", 250_000))
    max_cycle_seconds: int = field(default_factory=lambda: _int_env("SCIENCECLAW_MAX_CYCLE_SECONDS", 1800))
    max_skill_execs: int = field(default_factory=lambda: _int_env("SCIENCECLAW_MAX_SKILL_EXECS", 40))

    llm_calls: int = 0
    llm_tokens: int = 0
    skill_execs: int = 0
    started_at: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _log: Optional[logging.Logger] = field(default=None, repr=False)

    def __post_init__(self):
        self._log = get_logger("scienceclaw.budget")

    # -- queries ----------------------------------------------------------

    def elapsed_s(self) -> float:
        return time.time() - self.started_at

    def remaining_s(self) -> float:
        return max(0.0, self.max_cycle_seconds - self.elapsed_s())

    def is_paused(self) -> bool:
        return PAUSE_FILE.exists()

    def reason_exhausted(self) -> Optional[str]:
        """Return a short reason if any limit is breached, else None.

        `max_*` is the maximum number of *successful* charges; the (N+1)th
        charge raises. The counter has already been incremented by the time
        we evaluate, so the comparison is `>` not `>=`.
        """
        if self.is_paused():
            return f"PAUSE file present: {PAUSE_FILE}"
        if self.llm_calls > self.max_llm_calls:
            return f"llm_calls {self.llm_calls} > {self.max_llm_calls}"
        if self.llm_tokens > self.max_llm_tokens:
            return f"llm_tokens {self.llm_tokens} > {self.max_llm_tokens}"
        if self.skill_execs > self.max_skill_execs:
            return f"skill_execs {self.skill_execs} > {self.max_skill_execs}"
        if self.elapsed_s() > self.max_cycle_seconds:
            return f"wallclock {int(self.elapsed_s())}s > {self.max_cycle_seconds}s"
        return None

    # -- charges ----------------------------------------------------------

    def charge_llm(self, *, tokens: int) -> None:
        """Record one LLM call. Raises BudgetExhausted if caps are exceeded."""
        with self._lock:
            self.llm_calls += 1
            self.llm_tokens += max(0, tokens)
        self._check()

    def charge_skill(self) -> None:
        with self._lock:
            self.skill_execs += 1
        self._check()

    def _check(self) -> None:
        reason = self.reason_exhausted()
        if reason:
            self._log.error("cycle budget exhausted", extra={"reason": reason})
            raise BudgetExhausted(reason)

    def snapshot(self) -> dict:
        return {
            "llm_calls": self.llm_calls,
            "llm_tokens": self.llm_tokens,
            "skill_execs": self.skill_execs,
            "elapsed_s": round(self.elapsed_s(), 1),
            "max_llm_calls": self.max_llm_calls,
            "max_llm_tokens": self.max_llm_tokens,
            "max_skill_execs": self.max_skill_execs,
            "max_cycle_seconds": self.max_cycle_seconds,
        }


class BudgetExhausted(Exception):
    """Raised when a cycle exceeds its configured budget. Callers should
    abort the current cycle cleanly — the next scheduled heartbeat gets a
    fresh budget."""


# Process-wide active budget. Subsystems that don't have a clean way to
# receive a budget through their call chain (notably LLMClient) consult
# this. The loop controller sets it at the top of every cycle and clears
# it at the bottom; if no budget is set, charging is a no-op.
_ACTIVE: Optional[CycleBudget] = None
_ACTIVE_LOCK = threading.Lock()


def set_active_budget(budget: Optional[CycleBudget]) -> None:
    global _ACTIVE
    with _ACTIVE_LOCK:
        _ACTIVE = budget


def get_active_budget() -> Optional[CycleBudget]:
    return _ACTIVE


def charge_llm_if_active(tokens: int) -> None:
    """Convenience: charge the process-wide active budget, if any."""
    b = _ACTIVE
    if b is None:
        return
    b.charge_llm(tokens=tokens)


def charge_skill_if_active() -> None:
    b = _ACTIVE
    if b is None:
        return
    b.charge_skill()
