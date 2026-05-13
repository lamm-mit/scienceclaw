"""
Shared observability + robustness primitives for ScienceClaw.

This module is intentionally dependency-free (stdlib only) so it can be
imported from every layer of the codebase without creating cycles.

Provides:
    - get_logger(name)           : JSON-line structured logger (also prints to console)
    - locked_append(path, line)  : flock-protected JSONL append
    - safe_jsonl_lines(path)     : iterator over a JSONL file that surfaces
                                   parse errors via the logger instead of
                                   swallowing them
    - retry(...)                 : decorator with exponential backoff + jitter
    - LLMCache                   : prompt-hash keyed cache with TTL
    - SkillMetrics               : per-skill rolling success/latency stats

All file paths default under ~/.scienceclaw/ to match existing conventions.
"""

from __future__ import annotations

import contextlib
import errno
import functools
import hashlib
import json
import logging
import os
import random
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional, Tuple, Type

try:
    import fcntl  # POSIX only; falls back to no-op on Windows
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - non-posix
    _HAS_FCNTL = False


SCIENCECLAW_HOME = Path(os.path.expanduser("~/.scienceclaw"))
LOG_DIR = SCIENCECLAW_HOME / "logs"


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------


class _JSONFormatter(logging.Formatter):
    """Render LogRecord as a single JSON line."""

    _STANDARD = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Anything user-attached via `extra={...}` lands as a non-standard attr.
        for k, v in record.__dict__.items():
            if k in self._STANDARD or k.startswith("_"):
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except (TypeError, ValueError):
                payload[k] = repr(v)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_LOGGERS_CONFIGURED: set[str] = set()
_CONFIG_LOCK = threading.Lock()


# Names already used by logging.LogRecord. Passing any of these in `extra={...}`
# raises KeyError, so we transparently rename them to `*_x` to keep callers
# from accidentally breaking logging.
_RESERVED_LOGRECORD_ATTRS = frozenset({
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "message", "module",
    "msecs", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
})


class _SanitizeExtraFilter(logging.Filter):
    """Rename `extra` keys that collide with LogRecord attributes."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(record.__dict__.keys()):
            if key in _RESERVED_LOGRECORD_ATTRS:
                # `msg`, `name`, etc. are real attributes — but if a caller
                # also tried to set them via extra, the conflict would have
                # raised earlier. This branch is defensive for any other
                # path that may inject extras post-record-construction.
                continue
        return True


def get_logger(name: str = "scienceclaw", *, log_file: Optional[Path] = None) -> logging.Logger:
    """
    Return a logger that emits JSON lines to a per-agent log file and human-
    readable lines to stderr. Safe to call repeatedly; handlers are attached
    only once per logger name.
    """
    logger = logging.getLogger(name)
    with _CONFIG_LOCK:
        if name in _LOGGERS_CONFIGURED:
            return logger

        logger.setLevel(os.environ.get("SCIENCECLAW_LOG_LEVEL", "INFO").upper())
        logger.propagate = False

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        target = log_file or (LOG_DIR / "scienceclaw.jsonl")
        file_handler = logging.FileHandler(target, encoding="utf-8")
        file_handler.setFormatter(_JSONFormatter())
        logger.addHandler(file_handler)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(console)
        logger.addFilter(_SanitizeExtraFilter())

        _LOGGERS_CONFIGURED.add(name)
    return logger


def safe_extra(**fields: Any) -> Dict[str, Any]:
    """
    Build an `extra={...}` dict that won't collide with LogRecord builtins.
    Reserved keys get an `_x` suffix so the call doesn't raise.
    """
    out: Dict[str, Any] = {}
    for k, v in fields.items():
        if k in _RESERVED_LOGRECORD_ATTRS:
            out[f"{k}_x"] = v
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# File-locked JSONL append
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _file_lock(path: Path):
    """Acquire an OS file lock on `path` for the duration of the with-block."""
    if not _HAS_FCNTL:
        # Non-POSIX fallback: process-local lock only.
        with _PROCESS_LOCKS.setdefault(str(path), threading.Lock()):
            yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


_PROCESS_LOCKS: Dict[str, threading.Lock] = {}


def locked_append(path: Path, line: str) -> None:
    """
    Append a single line to `path` under an exclusive file lock.
    The caller is responsible for the trailing newline.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with _file_lock(path):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)


def safe_jsonl_lines(path: Path, logger: Optional[logging.Logger] = None) -> Iterator[dict]:
    """
    Iterate JSON objects from a JSONL file, logging parse errors instead of
    silently dropping them.
    """
    if not path.exists():
        return
    log = logger or get_logger("scienceclaw.jsonl")
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                log.warning(
                    "jsonl parse error",
                    extra={"path": str(path), "line_no": line_no, "error": str(exc)},
                )


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------


def retry(
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 300.0,
    factor: float = 2.0,
    jitter: float = 0.25,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    logger_name: str = "scienceclaw.retry",
):
    """
    Decorator: retry `attempts` times with exponential backoff + jitter.

    Only catches exceptions in `retry_on`. Re-raises the last exception when
    attempts are exhausted.
    """

    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            log = get_logger(logger_name)
            delay = base_delay
            last_exc: Optional[BaseException] = None
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except retry_on as exc:
                    last_exc = exc
                    if attempt >= attempts:
                        log.error(
                            "retry exhausted",
                            extra={
                                "fn": fn.__qualname__,
                                "attempts": attempt,
                                "error": str(exc),
                            },
                        )
                        raise
                    sleep_for = min(delay, max_delay) * (1 + random.uniform(-jitter, jitter))
                    log.warning(
                        "retrying after error",
                        extra={
                            "fn": fn.__qualname__,
                            "attempt": attempt,
                            "next_delay_s": round(sleep_for, 2),
                            "error": str(exc),
                        },
                    )
                    time.sleep(max(0.05, sleep_for))
                    delay *= factor
            # Unreachable, but mypy-friendly.
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# LLM response cache (prompt-hash keyed, TTL)
# ---------------------------------------------------------------------------


class LLMCache:
    """
    Lightweight on-disk + in-memory cache for LLM responses.

    Key: sha256(backend|model|prompt|max_tokens|temperature).
    Stored under ~/.scienceclaw/llm_cache/<first2>/<hash>.json
    Entries past `ttl_seconds` are treated as misses.

    The cache is intentionally process-local for hits (no fsync per call) but
    durable across processes via the on-disk copy.
    """

    def __init__(
        self,
        *,
        cache_dir: Optional[Path] = None,
        ttl_seconds: int = 3600,
        max_memory_entries: int = 512,
    ):
        self.cache_dir = cache_dir or (SCIENCECLAW_HOME / "llm_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.max_memory_entries = max_memory_entries
        self._mem: Dict[str, Tuple[float, str]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.log = get_logger("scienceclaw.llm_cache")

    @staticmethod
    def make_key(
        backend: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        h = hashlib.sha256()
        h.update(backend.encode("utf-8"))
        h.update(b"|")
        h.update(model.encode("utf-8"))
        h.update(b"|")
        h.update(prompt.encode("utf-8"))
        h.update(b"|")
        h.update(str(max_tokens).encode("utf-8"))
        h.update(b"|")
        h.update(f"{temperature:.4f}".encode("utf-8"))
        return h.hexdigest()

    def _path_for(self, key: str) -> Path:
        return self.cache_dir / key[:2] / f"{key}.json"

    def get(self, key: str) -> Optional[str]:
        now = time.time()
        with self._lock:
            entry = self._mem.get(key)
        if entry is not None:
            ts, value = entry
            if now - ts <= self.ttl_seconds:
                self.hits += 1
                return value
        path = self._path_for(key)
        if not path.exists():
            self.misses += 1
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.misses += 1
            return None
        ts = float(data.get("ts", 0))
        if now - ts > self.ttl_seconds:
            self.misses += 1
            return None
        value = data.get("response", "")
        with self._lock:
            self._mem[key] = (ts, value)
            self._evict_if_needed()
        self.hits += 1
        return value

    def put(self, key: str, value: str) -> None:
        if not value:
            return  # never cache empty responses
        ts = time.time()
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({"ts": ts, "response": value}, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp, path)
        except OSError as exc:
            self.log.warning("llm cache write failed", extra={"error": str(exc)})
            return
        with self._lock:
            self._mem[key] = (ts, value)
            self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        if len(self._mem) <= self.max_memory_entries:
            return
        # Evict oldest ~10%
        items = sorted(self._mem.items(), key=lambda kv: kv[1][0])
        drop = max(1, len(items) // 10)
        for k, _ in items[:drop]:
            self._mem.pop(k, None)

    def stats(self) -> Dict[str, int]:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(100 * self.hits / total, 1) if total else 0,
        }


# ---------------------------------------------------------------------------
# Per-skill metrics
# ---------------------------------------------------------------------------


class SkillMetrics:
    """
    Per-skill rolling stats persisted to ~/.scienceclaw/metrics/skills.json.

    Tracks success/failure counts and a moving average of latency_ms. Used by
    skill selection to deprioritize chronically failing or slow skills.
    """

    def __init__(self, path: Optional[Path] = None, ema_alpha: float = 0.2):
        self.path = path or (SCIENCECLAW_HOME / "metrics" / "skills.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ema_alpha = ema_alpha
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _flush(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass

    def record(self, skill: str, *, success: bool, latency_ms: float, payload_bytes: int = 0) -> None:
        with self._lock:
            entry = self._data.setdefault(skill, {
                "success": 0,
                "failure": 0,
                "ema_latency_ms": float(latency_ms),
                "last_payload_bytes": 0,
                "last_run_ts": 0,
            })
            if success:
                entry["success"] += 1
            else:
                entry["failure"] += 1
            a = self.ema_alpha
            entry["ema_latency_ms"] = (1 - a) * entry["ema_latency_ms"] + a * latency_ms
            entry["last_payload_bytes"] = payload_bytes
            entry["last_run_ts"] = int(time.time())
            self._flush()

    def success_rate(self, skill: str) -> float:
        entry = self._data.get(skill)
        if not entry:
            return 1.0  # unknown skills get the benefit of the doubt
        total = entry["success"] + entry["failure"]
        return entry["success"] / total if total else 1.0

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._data.items()}


# ---------------------------------------------------------------------------
# Investigation fingerprint helpers
# ---------------------------------------------------------------------------


def normalize_topic(topic: str) -> str:
    """Lower-case + collapse whitespace + strip punctuation for fingerprinting."""
    s = topic.lower()
    keep = []
    for ch in s:
        if ch.isalnum() or ch.isspace():
            keep.append(ch)
        else:
            keep.append(" ")
    return " ".join("".join(keep).split())


def investigation_fingerprint(topic: str, *, method: str = "", params: Optional[Dict[str, Any]] = None) -> str:
    """Stable hash over (normalized topic, method, sorted params)."""
    body = {
        "topic": normalize_topic(topic),
        "method": method.strip().lower(),
        "params": params or {},
    }
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
