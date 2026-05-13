"""
Artifact JSONL compaction.

Why this exists: ~/.scienceclaw/artifacts/global_index.jsonl and the per-agent
store.jsonl files are append-only. Over weeks they grow into MB-then-GB.
Reads (used by the reactor every cycle) scan the whole file, so growth makes
each cycle slower.

`compact_jsonl()` rotates a JSONL file in place:
  1. Renames the file out of the way to <name>.compacting under a file lock.
  2. Streams entries into a temp file, keeping only:
       - the most recent occurrence of each `artifact_id` (dedupe), and
       - entries whose `timestamp` is within `keep_days` of now.
  3. Anything dropped goes into <name>-<YYYYMMDD>.jsonl.gz next to the live
     file, so nothing is lost — it's just out of the hot path.
  4. Renames the temp file back to <name>.

Safe under concurrent appends because:
  - Writers use locked_append (same file lock) so an append can't interleave
    with the rotation.
  - The whole compaction holds the lock for the duration; appends queue up.

Trigger from the heartbeat daemon between cycles (idle time), guarded by a
size threshold so we don't compact every cycle.
"""

from __future__ import annotations

import gzip
import json
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .observability import _file_lock, get_logger, safe_jsonl_lines


_LOG = get_logger("scienceclaw.compaction")


def compact_jsonl(
    path: Path,
    *,
    keep_days: int = 30,
    min_size_bytes: int = 5 * 1024 * 1024,  # 5 MB
    archive_dir: Optional[Path] = None,
    dedupe_key: str = "artifact_id",
) -> dict:
    """
    Compact a JSONL file in place. Returns a summary dict:
        {kept, dropped_old, dropped_dup, archived_path, before_bytes, after_bytes}

    No-op if the file doesn't exist or is below min_size_bytes.
    """
    if not path.exists():
        return {"skipped": "missing", "kept": 0}
    size = path.stat().st_size
    if size < min_size_bytes:
        return {"skipped": "below_threshold", "size": size, "kept": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    archive_dir = archive_dir or (path.parent / "archive")
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = archive_dir / f"{path.stem}-{stamp}.jsonl.gz"
    tmp_path = path.with_suffix(path.suffix + ".compacting")

    kept = 0
    dropped_old = 0
    dropped_dup = 0
    seen: dict = {}

    # Read every entry first, deciding what to keep. We need a two-pass
    # approach to honor "most recent wins" on dedupe: stream-collect into a
    # dict keyed by dedupe_key, with the newest entry winning by timestamp.
    started = time.monotonic()
    with _file_lock(path):
        for entry in safe_jsonl_lines(path, logger=_LOG):
            ts_raw = entry.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_raw)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                # Missing/bad timestamp — keep, but treat as "old enough to
                # be deduped by later identical key".
                ts = datetime.now(timezone.utc)

            if ts < cutoff:
                dropped_old += 1
                _append_archived(archive_path, entry)
                continue

            key = entry.get(dedupe_key)
            if key is None:
                # No dedupe key — keep unconditionally
                seen[id(entry)] = (ts, entry)
                continue
            prev = seen.get(key)
            if prev is None or prev[0] < ts:
                if prev is not None:
                    dropped_dup += 1
                    _append_archived(archive_path, prev[1])
                seen[key] = (ts, entry)
            else:
                dropped_dup += 1
                _append_archived(archive_path, entry)

        # Write surviving entries to temp, then atomic rename.
        with open(tmp_path, "w", encoding="utf-8") as fh:
            for _, entry in seen.values():
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
                kept += 1

        shutil.move(str(tmp_path), str(path))

    after_size = path.stat().st_size
    elapsed_ms = int((time.monotonic() - started) * 1000)
    summary = {
        "kept": kept,
        "dropped_old": dropped_old,
        "dropped_dup": dropped_dup,
        "before_bytes": size,
        "after_bytes": after_size,
        "elapsed_ms": elapsed_ms,
        "archive_path": str(archive_path) if archive_path.exists() else "",
    }
    _LOG.info("compaction complete", extra=summary)
    return summary


def _append_archived(archive_path: Path, entry: dict) -> None:
    """Append a dropped entry to the gzipped archive (created on first write)."""
    line = (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")
    with gzip.open(archive_path, "ab") as gz:
        gz.write(line)


def compact_all_stores(*, keep_days: int = 30, min_size_bytes: int = 5 * 1024 * 1024) -> dict:
    """
    Walk ~/.scienceclaw/artifacts/ and compact:
      - global_index.jsonl
      - every per-agent store.jsonl
    """
    base = Path.home() / ".scienceclaw" / "artifacts"
    if not base.exists():
        return {"results": []}
    targets = [base / "global_index.jsonl"]
    for child in base.iterdir():
        if child.is_dir():
            store = child / "store.jsonl"
            if store.exists():
                targets.append(store)
    out = []
    for p in targets:
        try:
            out.append({"path": str(p), **compact_jsonl(
                p, keep_days=keep_days, min_size_bytes=min_size_bytes,
            )})
        except Exception as e:
            _LOG.error("compaction failed", extra={"path": str(p), "error": str(e)})
            out.append({"path": str(p), "error": str(e)})
    return {"results": out}
