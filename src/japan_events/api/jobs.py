from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date
from typing import Any

from japan_events.models import CombinedOutput, SiteResult
from japan_events.storage import load_combined, rebuild_combined_from_files


def _run_scrape_in_thread(target: date, prefecture: str | None = None) -> list[SiteResult]:
    """Run the async Playwright scrape inside a dedicated OS thread."""
    from japan_events.scrape import run_scrape

    return asyncio.run(
        run_scrape(
            target,
            prefecture=prefecture,
            headed=False,
            concurrency=3,
        )
    )


class ThreadedScrapeService:
    """Serialize scrapes per date in worker threads; callers block until finished."""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="japan-scrape")
        self._guard = threading.Lock()
        self._inflight: dict[str, Future[list[SiteResult]]] = {}

    def ensure_cached(
        self,
        target: date,
        *,
        prefecture: str | None = None,
        force: bool = False,
    ) -> tuple[CombinedOutput | None, bool]:
        """
        Return (combined, scraped_now).
        If cache is missing (or force), scrape in a worker thread and wait.
        Concurrent requests for the same date share one scrape future.
        """
        key = target.isoformat()
        if not force:
            combined = load_combined(target) or rebuild_combined_from_files(target)
            if combined is not None:
                return combined, False

        with self._guard:
            fut = self._inflight.get(key)
            if fut is None:
                fut = self._executor.submit(_run_scrape_in_thread, target, None)
                self._inflight[key] = fut

        try:
            fut.result()
        except Exception:
            with self._guard:
                self._inflight.pop(key, None)
            raise
        else:
            with self._guard:
                if self._inflight.get(key) is fut:
                    self._inflight.pop(key, None)

        combined = load_combined(target) or rebuild_combined_from_files(target)
        return combined, True

    def status(self) -> dict[str, Any]:
        with self._guard:
            return {
                "inflight_dates": list(self._inflight.keys()),
                "workers": self._executor._max_workers,  # noqa: SLF001
            }


scrape_service = ThreadedScrapeService()
