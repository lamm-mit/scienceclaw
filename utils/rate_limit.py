"""
Process-shared rate limiters for external APIs.

The first concrete consumer is NCBI E-utilities (PubMed): NCBI throttles
unauthenticated traffic to 3 req/s and authenticated (NCBI_API_KEY) traffic
to 10 req/s. Multiple skills can hit PubMed in a single cycle, so an
in-process token bucket prevents the daemon from getting an IP-level ban.

Token buckets are shared via module-level dicts; for the single-daemon
deployment that's enough. Multi-process coordination would need a file-
based last-call timestamp, which we add lazily if needed.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TokenBucket:
    """
    Classic token bucket: capacity tokens refilled at `rate` tokens/sec.
    `acquire(n)` blocks until n tokens are available.
    """
    rate: float                 # tokens per second
    capacity: float             # max tokens stored
    _tokens: float = field(init=False)
    _last: float = field(init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self):
        self._tokens = self.capacity
        self._last = time.monotonic()

    def acquire(self, tokens: float = 1.0) -> None:
        if tokens > self.capacity:
            raise ValueError(f"requested {tokens} > capacity {self.capacity}")
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                wait_s = deficit / self.rate
            time.sleep(wait_s)


_BUCKETS: Dict[str, TokenBucket] = {}
_BUCKETS_LOCK = threading.Lock()


def get_bucket(name: str, rate: float, capacity: float) -> TokenBucket:
    """Return a named, process-shared TokenBucket (created on first call)."""
    with _BUCKETS_LOCK:
        bucket = _BUCKETS.get(name)
        if bucket is None:
            bucket = TokenBucket(rate=rate, capacity=capacity)
            _BUCKETS[name] = bucket
        return bucket


# -- NCBI / PubMed convenience -----------------------------------------------


def ncbi_bucket() -> TokenBucket:
    """
    Bucket for NCBI E-utilities. 10 req/s with an API key, 3 req/s without.
    Capacity matches rate so a burst of N tokens means N immediate calls.
    """
    has_key = bool(os.environ.get("NCBI_API_KEY"))
    rate = 10.0 if has_key else 3.0
    return get_bucket("ncbi", rate=rate, capacity=rate)


def throttle_ncbi() -> None:
    """Block until the NCBI bucket has a token. Call before each Entrez op."""
    ncbi_bucket().acquire(1.0)
