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
    """Queue scrapes per date in a small thread pool. HTTP handlers never wait."""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="japan-scrape")
        self._guard = threading.Lock()
        self._inflight: dict[str, Future] = {}
        self._progress: dict[str, JobProgress] = {}

    def _cleanup(self, key: str, done: Future) -> None:
        with self._guard:
            if self._inflight.get(key) is done:
                self._inflight.pop(key, None)

    def _is_inflight(self, key: str) -> bool:
        with self._guard:
            return key in self._inflight

    def _load_complete_cache(self, target: date) -> CombinedOutput | None:
        """Serve finished all.json even during a refresh; never rebuild partial files while inflight."""
        combined = load_combined(target)
        if combined is not None:
            return combined
        if self._is_inflight(target.isoformat()):
            return None
        return rebuild_combined_from_files(target)

    def start_scrape(self, target: date) -> bool:
        """Submit a full scrape if one is not already queued/running. Never waits."""
        key = target.isoformat()
        with self._guard:
            if key in self._inflight:
                return True
            progress = JobProgress(key)
            fut = self._executor.submit(_run_scrape_in_thread, target, None, progress)
            self._inflight[key] = fut
            self._progress[key] = progress
            fut.add_done_callback(lambda done, k=key: self._cleanup(k, done))
        return True

    def get_or_start(self, target: date, *, force: bool = False) -> tuple[CombinedOutput | None, bool]:
        """
        Return (combined, scraping).
        If cache is ready, combined is set and scraping is False.
        Otherwise kick off a worker (or join the existing queue) and return immediately.
        """
        if not force:
            combined = self._load_complete_cache(target)
            if combined is not None:
                return combined, False
        self.start_scrape(target)
        return None, True

    def ensure_cached(
        self,
        target: date,
        *,
        prefecture: str | None = None,
        force: bool = False,
    ) -> tuple[CombinedOutput | None, bool]:
        """Wait for a scrape when callers truly need the file (tests / CLI)."""
        combined, scraping = self.get_or_start(target, force=force)
        if combined is not None:
            return combined, False
        key = target.isoformat()
        with self._guard:
            fut = self._inflight.get(key)
        if fut is not None:
            fut.result()
        combined = load_combined(target) or rebuild_combined_from_files(target)
        return combined, scraping or combined is not None

    def maybe_refresh(self, target: date) -> bool:
        """Start a background scan/refresh. Never blocks. True if a job is running."""
        key = target.isoformat()
        combined = load_combined(target) or rebuild_combined_from_files(target)
        if combined is None:
            return False

        with self._guard:
            if self._inflight:
                return key in self._inflight
            if not _refresh_due(target, combined):
                return False
            progress = JobProgress(key)
            fut = self._executor.submit(_run_refresh_in_thread, target, progress)
            self._inflight[key] = fut
            self._progress[key] = progress
            fut.add_done_callback(lambda done, k=key: self._cleanup(k, done))
        return True

    def status(self, date_key: str | None = None) -> dict[str, Any]:
        with self._guard:
            inflight = list(self._inflight.keys())
            running_dates = [key for key, fut in self._inflight.items() if fut.running()]
            queued_dates = [
                key for key, fut in self._inflight.items() if not fut.done() and not fut.running()
            ]
            workers = self._executor._max_workers  # noqa: SLF001
            if date_key:
                progress = self._progress.get(date_key)
                job = progress.snapshot() if progress else None
            else:
                job = None
            jobs = [item.snapshot() for item in self._progress.values()]
        if job and date_key in queued_dates:
            job["queued"] = True
            job["phase"] = "queued"
        for item in jobs:
            if item["date"] in queued_dates:
                item["queued"] = True
                if item["phase"] == "starting":
                    item["phase"] = "queued"
        return {
            "inflight_dates": inflight,
            "running_dates": running_dates,
            "queued_dates": queued_dates,
            "workers": workers,
            "job": job,
            "jobs": jobs,
        }


scrape_service = ThreadedScrapeService()
