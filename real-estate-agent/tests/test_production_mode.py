import tempfile
import unittest
from pathlib import Path

from src.production_mode import RuntimeConfig, ScraperRuntime


class ProductionModeTests(unittest.TestCase):
    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ScraperRuntime(
                RuntimeConfig(
                    enabled=True,
                    cache_dir=Path(tmp) / "cache",
                    cache_ttl_seconds=60,
                    throttle_seconds=0,
                    max_backoff_seconds=1,
                    raw_store_dir=Path(tmp) / "raw",
                )
            )
            rows = [{"price": 1, "sqft": 1, "beds": 0, "baths": 0.0}]
            runtime.set_cache("k", rows)
            self.assertEqual(runtime.get_cache("k"), rows)

    def test_retry_with_backoff_eventual_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ScraperRuntime(
                RuntimeConfig(
                    enabled=True,
                    cache_dir=Path(tmp) / "cache",
                    cache_ttl_seconds=60,
                    throttle_seconds=0,
                    max_backoff_seconds=1,
                    raw_store_dir=Path(tmp) / "raw",
                )
            )
            state = {"calls": 0}

            def flaky():
                state["calls"] += 1
                if state["calls"] < 2:
                    raise RuntimeError("429")
                return "ok"

            self.assertEqual(runtime.retry_with_backoff(flaky, retries=3, label="x"), "ok")


if __name__ == "__main__":
    unittest.main()
