"""Production scraper utilities: caching, throttling, backoff, and local raw store."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeConfig:
    enabled: bool
    cache_dir: Path
    cache_ttl_seconds: int
    throttle_seconds: float
    max_backoff_seconds: float
    raw_store_dir: Path


class ScraperRuntime:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self._last_request_by_key: dict[str, float] = {}
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config.raw_store_dir.mkdir(parents=True, exist_ok=True)

    def throttle(self, key: str) -> None:
        if not self.config.enabled:
            return
        last = self._last_request_by_key.get(key)
        now = time.time()
        if last is None:
            self._last_request_by_key[key] = now
            return
        delta = now - last
        if delta < self.config.throttle_seconds:
            sleep_for = self.config.throttle_seconds - delta
            LOGGER.info("Throttling %s for %.2fs", key, sleep_for)
            time.sleep(sleep_for)
        self._last_request_by_key[key] = time.time()

    def retry_with_backoff(self, fn: Callable[[], Any], retries: int, label: str) -> Any:
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return fn()
            except Exception as exc:  # intentionally broad for resilient scraping
                last_exc = exc
                if attempt >= retries:
                    break
                wait = self._backoff_seconds(attempt, exc)
                LOGGER.warning("%s failed (attempt %s/%s): %s. Backing off %.2fs", label, attempt, retries, exc, wait)
                time.sleep(wait)
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"{label} failed without exception")

    def get_cache(self, cache_key: str) -> list[dict[str, Any]] | None:
        if not self.config.enabled:
            return None
        path = self._cache_path(cache_key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            created_at = float(payload.get("created_at", 0))
            if time.time() - created_at > self.config.cache_ttl_seconds:
                return None
            rows = payload.get("rows")
            if isinstance(rows, list):
                LOGGER.info("Cache hit for %s (%s rows)", cache_key, len(rows))
                return [r for r in rows if isinstance(r, dict)]
        except Exception:
            return None
        return None

    def set_cache(self, cache_key: str, rows: list[dict[str, Any]]) -> None:
        if not self.config.enabled:
            return
        payload = {"created_at": time.time(), "rows": rows}
        self._cache_path(cache_key).write_text(json.dumps(payload), encoding="utf-8")

    def store_raw_dataset(self, source: str, city: str, rows: list[dict[str, Any]]) -> None:
        if not self.config.enabled or not rows:
            return
        city_slug = city.lower().replace(" ", "_")
        out_dir = self.config.raw_store_dir / source
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{city_slug}.jsonl"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with out_path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps({"ingested_at": now_iso, "city": city, "source": source, "row": row}))
                handle.write("\n")

    def _cache_path(self, cache_key: str) -> Path:
        safe_key = cache_key.replace("/", "_").replace(" ", "_")
        return self.config.cache_dir / f"{safe_key}.json"

    def _backoff_seconds(self, attempt: int, exc: Exception) -> float:
        base = min((2 ** attempt), self.config.max_backoff_seconds)
        msg = str(exc)
        if "429" in msg:
            base = min(base * 2, self.config.max_backoff_seconds)
        jitter = random.uniform(0, 0.5)
        return min(base + jitter, self.config.max_backoff_seconds)


def get_runtime() -> ScraperRuntime:
    enabled = os.getenv("PRODUCTION_SCRAPER_MODE", "true").strip().lower() in {"1", "true", "yes", "on"}
    cache_dir = Path(os.getenv("SCRAPER_CACHE_DIR", ".cache/scraper"))
    ttl_minutes = int(os.getenv("SCRAPER_CACHE_TTL_MINUTES", "60"))
    throttle_seconds = float(os.getenv("SCRAPER_THROTTLE_SECONDS", "2.0"))
    max_backoff_seconds = float(os.getenv("SCRAPER_MAX_BACKOFF_SECONDS", "30.0"))
    raw_store_dir = Path(os.getenv("LOCAL_DATASET_STORE_DIR", "data/local_store"))

    return ScraperRuntime(
        RuntimeConfig(
            enabled=enabled,
            cache_dir=cache_dir,
            cache_ttl_seconds=max(ttl_minutes, 1) * 60,
            throttle_seconds=max(throttle_seconds, 0.0),
            max_backoff_seconds=max(max_backoff_seconds, 1.0),
            raw_store_dir=raw_store_dir,
        )
    )
