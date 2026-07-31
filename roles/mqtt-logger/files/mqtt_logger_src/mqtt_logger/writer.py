"""JSONL writer with file rotation and disk-space budget enforcement."""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

FILE_PREFIX = "mqtt-"
FILE_SUFFIX = ".jsonl"


def _utcnow() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _new_filename() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return f"{FILE_PREFIX}{ts}{FILE_SUFFIX}"


def _dir_size(log_dir: Path) -> int:
    """Return total size in bytes of all JSONL log files in log_dir."""
    return sum(f.stat().st_size for f in _log_files(log_dir))


def _log_files(log_dir: Path) -> list[Path]:
    """Return log files sorted oldest-first."""
    files = sorted(log_dir.glob(f"{FILE_PREFIX}*{FILE_SUFFIX}"))
    return files


class JsonlWriter:
    """Writes MQTT messages as JSON lines, rotating files and enforcing a disk budget.

    Rotation: a new file is opened once the current file reaches *max_file_bytes*.
    Eviction: after each rotation the oldest files are deleted until total
              directory usage is at or below *max_total_bytes*.
    """

    def __init__(self, log_dir: str | Path, max_file_bytes: int, max_total_bytes: int) -> None:
        self.log_dir = Path(log_dir)
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes

        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._current_path: Path | None = None
        self._fh: object = None  # file handle
        self._open_new_file()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, topic: str, payload: bytes) -> None:
        """Encode and append a message, rotating if necessary."""
        try:
            payload_str = payload.decode("utf-8")
            encoding = "utf-8"
        except (UnicodeDecodeError, AttributeError):
            payload_str = base64.b64encode(payload).decode("ascii")
            encoding = "base64"

        record = {
            "timestamp": _utcnow(),
            "topic": topic,
            "payload": payload_str,
            "payload_encoding": encoding,
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        self._fh.write(line)
        self._fh.flush()

        if self._current_path.stat().st_size >= self.max_file_bytes:
            self._rotate()

    def close(self) -> None:
        """Flush and close the current log file."""
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_new_file(self) -> None:
        if self._fh is not None:
            self._fh.close()
        filename = _new_filename()
        self._current_path = self.log_dir / filename
        self._fh = self._current_path.open("a", encoding="utf-8")
        log.info("Opened log file: %s", self._current_path)

    def _rotate(self) -> None:
        log.info("Rotating log file: %s (size=%d bytes)", self._current_path, self._current_path.stat().st_size)
        self._open_new_file()
        self._evict()

    def _evict(self) -> None:
        """Delete oldest log files until total directory size ≤ max_total_bytes."""
        files = _log_files(self.log_dir)
        # Never delete the currently open file
        evictable = [f for f in files if f != self._current_path]
        total = _dir_size(self.log_dir)

        while total > self.max_total_bytes and evictable:
            oldest = evictable.pop(0)
            freed = oldest.stat().st_size
            oldest.unlink()
            total -= freed
            log.info("Evicted old log file: %s (freed %d bytes, total now %d bytes)", oldest, freed, total)

        if total > self.max_total_bytes:
            log.warning(
                "Total log size %d bytes still exceeds budget %d bytes after eviction — only the current file remains.",
                total,
                self.max_total_bytes,
            )
