"""Smart summary cache for Git2Report.

Caches AI module summaries and executive summaries by commit hashes,
preventing redundant LLM calls and enabling sub-second re-runs.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("git2report.cache")
DEFAULT_CACHE_FILE = Path(".git2report_cache.json")


def compute_cache_key(prefix: str, module: str, commit_hashes: list[str], audience: str, model: str) -> str:
    """Create a deterministic SHA-256 cache key based on inputs."""
    sorted_hashes = sorted(commit_hashes)
    payload = f"{prefix}::{module}::{','.join(sorted_hashes)}::{audience}::{model}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SummaryCache:
    def __init__(self, cache_file: Path | str = DEFAULT_CACHE_FILE, enabled: bool = True):
        self.cache_file = Path(cache_file)
        self.enabled = enabled
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.enabled or not self.cache_file.exists():
            return
        try:
            raw = self.cache_file.read_text(encoding="utf-8")
            self._data = json.loads(raw)
        except Exception as exc:
            logger.debug(f"Failed to load cache: {exc}")
            self._data = {}

    def _save(self) -> None:
        if not self.enabled:
            return
        try:
            self.cache_file.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug(f"Failed to save cache: {exc}")

    def get(self, key: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        return self._data.get(key)

    def set(self, key: str, summary: str, mode: str = "ai", meta: dict[str, Any] | None = None) -> None:
        if not self.enabled:
            return
        entry = {
            "summary": summary,
            "mode": mode,
            "meta": meta or {},
        }
        self._data[key] = entry
        self._save()

    def clear(self) -> int:
        count = len(self._data)
        self._data = {}
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception:
                pass
        return count


# Global default cache instance
default_cache = SummaryCache()
