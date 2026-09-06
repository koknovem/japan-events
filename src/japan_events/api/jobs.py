from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any

from japan_events.models import CombinedOutput, SiteResult
from japan_events.progress import JobProgress
from japan_events.registry import load_sites
from japan_events.scan import cache_age_seconds, load_scan, save_scan, scan_age_seconds, scan_sites
from japan_events.settings import SCAN_CONCURRENCY, deep_refresh_seconds, scan_ttl_seconds, site_concurrency
from japan_events.storage import load_combined, rebuild_combined_from_files


def _run_scrape_in_thread(
    target: date,
    prefecture: str | None,
    progress: JobProgress,
) -> list[SiteResult]:
    """Run the async Playwright scrape inside a dedicated OS thread."""
    from japan_events.scrape import run_scrape

    def on_progress(event: str, payload: dict[str, Any]) -> None:
        progress.handle(event, payload)

    try:
        return asyncio.run(
            run_scrape(
                target,
                prefecture=prefecture,
                headed=False,
                concurrency=site_concurrency(),
                on_progress=on_progress,
            )
        )
    except Exception as exc:
        progress.handle("error", {"error": f"{type(exc).__name__}: {exc}"})
        raise


def _refresh_due(target: date, combined: CombinedOutput) -> bool:
    if target < date.today() - timedelta(days=14):
        return False
    age = cache_age_seconds(combined)
    if age < scan_ttl_seconds():
        return False
    scan = load_scan(target)
    scanned_ago = scan_age_seconds(scan)
    if scanned_ago is not None and scanned_ago < scan_ttl_seconds() and age < deep_refresh_seconds():
        return False
    return True


def _run_refresh_in_thread(target: date, progress: JobProgress) -> None:
    """Cheap HTTP scan first; Playwright only dirty (or all, if the cache is old)."""
    from japan_events.scrape import run_scrape

    sites = load_sites()
    previous = (load_scan(target) or {}).get("sites") or {}
    progress.handle(
        "init",
        {
            "phase": "scanning",
            "concurrency": SCAN_CONCURRENCY,
            "sites": [{"id": site.id, "prefecture": site.name} for site in sites],
        },
    )

    def on_site(site, fp, changed) -> None:
        progress.handle("site_start", {"id": site.id, "prefecture": site.name, "phase": "scanning"})
        progress.handle(
            "site_done",
            {
                "id": site.id,
                "prefecture": site.name,
                "ok": not fp.get("error"),
                "event_count": 1 if changed else 0,
                "error": fp.get("error"),
            },
        )

    fingerprints, dirty = scan_sites(sites, target, previous, on_site=on_site)
    save_scan(target, fingerprints)

    combined = load_combined(target) or rebuild_combined_from_files(target)
    age = cache_age_seconds(combined) if combined else deep_refresh_seconds()
    deep = age >= deep_refresh_seconds()
    if not dirty and not deep:
        progress.handle("done", {"ok_count": len(sites), "event_count": combined.event_count if combined else 0})
        print(f"[scan] {target.isoformat()} unchanged sites={len(sites)}", flush=True)
        return

    prefecture = None if deep or not dirty else ",".join(dirty)
    print(
        f"[scan] {target.isoformat()} dirty={len(dirty)} deep={deep} -> scrape {prefecture or 'all'}",
        flush=True,
    )

    def on_progress(event: str, payload: dict[str, Any]) -> None:
        progress.handle(event, payload)

    try:
        asyncio.run(
            run_scrape(
                target,
                prefecture=prefecture,
                headed=False,
                concurrency=site_concurrency(),
                on_progress=on_progress,
            )
        )
    except Exception as exc:
        progress.handle("error", {"error": f"{type(exc).__name__}: {exc}"})
        raise


class ThreadedScrapeService:
    """Serialize scrapes per date in worker threads; callers block until finished."""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="japan-scrape")
        self._guard = threading.Lock()
        self._inflight: dict[str, Future] = {}
        self._progress: dict[str, JobProgress] = {}

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
                progress = JobProgress(key)
                fut = self._executor.submit(_run_scrape_in_thread, target, None, progress)
                self._inflight[key] = fut
                self._progress[key] = progress

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

    def maybe_refresh(self, target: date) -> bool:
        """Start a background scan/refresh. Never blocks. True if a job is running."""
        key = target.isoformat()
        combined = load_combined(target) or rebuild_combined_from_files(target)
        if combined is None:
            return False

        with self._guard:
            if key in self._inflight:
                return True
            if not _refresh_due(target, combined):
                return False
            progress = JobProgress(key)
            fut = self._executor.submit(_run_refresh_in_thread, target, progress)
            self._inflight[key] = fut
            self._progress[key] = progress

            def _cleanup(done: Future) -> None:
                with self._guard:
                    if self._inflight.get(key) is done:
                        self._inflight.pop(key, None)

            fut.add_done_callback(_cleanup)
        return True

    def status(self, date_key: str | None = None) -> dict[str, Any]:
        with self._guard:
            inflight = list(self._inflight.keys())
            workers = self._executor._max_workers  # noqa: SLF001
            if date_key:
                progress = self._progress.get(date_key)
                job = progress.snapshot() if progress else None
            else:
                job = None
            jobs = [item.snapshot() for item in self._progress.values()]
        return {
            "inflight_dates": inflight,
            "workers": workers,
            "job": job,
            "jobs": jobs,
        }


scrape_service = ThreadedScrapeService()
