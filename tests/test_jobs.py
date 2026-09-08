import threading
from datetime import date

from japan_events.api.jobs import ThreadedScrapeService
from japan_events.progress import JobProgress


def test_get_or_start_does_not_block(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def fake_scrape(target, prefecture, progress: JobProgress):
        progress.handle(
            "init",
            {"sites": [{"id": "tokyo", "prefecture": "Tokyo"}], "concurrency": 1},
        )
        started.set()
        if not release.wait(timeout=5):
            raise TimeoutError("test scrape was not released")
        progress.handle("site_done", {"id": "tokyo", "ok": True, "event_count": 1})
        progress.handle("done", {"ok_count": 1, "event_count": 1})
        return []

    monkeypatch.setattr("japan_events.api.jobs._run_scrape_in_thread", fake_scrape)
    service = ThreadedScrapeService(max_workers=1)
    try:
        combined, scraping = service.get_or_start(date(2099, 1, 1))
        assert combined is None
        assert scraping is True
        assert started.wait(timeout=2)

        combined2, scraping2 = service.get_or_start(date(2099, 1, 2))
        assert combined2 is None
        assert scraping2 is True

        status = service.status()
        assert set(status["inflight_dates"]) == {"2099-01-01", "2099-01-02"}
        assert status["running_dates"] == ["2099-01-01"]
        assert status["queued_dates"] == ["2099-01-02"]
        queued = next(job for job in status["jobs"] if job["date"] == "2099-01-02")
        assert queued["queued"] is True
        assert queued["phase"] == "queued"

        same, still = service.get_or_start(date(2099, 1, 1))
        assert still is True
        assert same is None
        assert len(status["inflight_dates"]) == 2
    finally:
        release.set()
        service._executor.shutdown(wait=True)


def test_maybe_refresh_does_not_steal_scrape_workers(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def fake_scrape(target, prefecture, progress: JobProgress):
        started.set()
        release.wait(timeout=5)
        return []

    monkeypatch.setattr("japan_events.api.jobs._run_scrape_in_thread", fake_scrape)
    monkeypatch.setattr("japan_events.api.jobs.load_combined", lambda target: object())
    monkeypatch.setattr("japan_events.api.jobs._refresh_due", lambda target, combined: True)
    monkeypatch.setattr("japan_events.api.jobs.missing_site_ids", lambda target: [])
    monkeypatch.setattr("japan_events.api.jobs.load_pending_refresh", lambda target: [])

    service = ThreadedScrapeService(max_workers=1)
    try:
        service.start_scrape(date(2099, 3, 1))
        assert started.wait(timeout=2)
        assert service.maybe_refresh(date(2026, 9, 6)) is False
        assert service.status()["inflight_dates"] == ["2099-03-01"]
    finally:
        release.set()
        service._executor.shutdown(wait=True)


def test_refresh_due_recent_scan_blocks_even_if_cache_is_old(monkeypatch):
    from japan_events.api import jobs

    class Cache:
        generated_at = "2020-01-01T00:00:00Z"

    monkeypatch.setattr(jobs, "cache_age_seconds", lambda combined: 20 * 3600)
    monkeypatch.setattr(jobs, "load_scan", lambda target: {"scanned_at": "now"})
    monkeypatch.setattr(jobs, "scan_age_seconds", lambda scan: 60)
    monkeypatch.setattr(jobs, "scan_ttl_seconds", lambda: 6 * 3600)
    assert jobs._refresh_due(date.today(), Cache()) is False


def test_refresh_due_old_scan_allows_check(monkeypatch):
    from japan_events.api import jobs

    class Cache:
        generated_at = "2020-01-01T00:00:00Z"

    monkeypatch.setattr(jobs, "cache_age_seconds", lambda combined: 20 * 3600)
    monkeypatch.setattr(jobs, "load_scan", lambda target: {"scanned_at": "old"})
    monkeypatch.setattr(jobs, "scan_age_seconds", lambda scan: 10 * 3600)
    monkeypatch.setattr(jobs, "scan_ttl_seconds", lambda: 6 * 3600)
    assert jobs._refresh_due(date.today(), Cache()) is True


def test_get_or_start_resumes_only_missing_sites(monkeypatch):
    started = threading.Event()
    captured: dict[str, str | None] = {}

    def fake_scrape(target, prefecture, progress: JobProgress):
        captured["prefecture"] = prefecture
        progress.handle("done", {"ok_count": 1, "event_count": 0})
        started.set()
        return []

    monkeypatch.setattr("japan_events.api.jobs._run_scrape_in_thread", fake_scrape)
    monkeypatch.setattr("japan_events.api.jobs.missing_site_ids", lambda target: ["kyoto"])
    monkeypatch.setattr("japan_events.api.jobs.site_result_ids", lambda target: {"tokyo"})
    monkeypatch.setattr("japan_events.api.jobs.load_pending_refresh", lambda target: [])
    monkeypatch.setattr("japan_events.api.jobs.load_combined", lambda target: object())
    monkeypatch.setattr("japan_events.api.jobs.live_combined", lambda target: None)

    service = ThreadedScrapeService(max_workers=1)
    try:
        combined, busy = service.get_or_start(date(2099, 1, 1))
        assert combined is None
        assert busy is True
        assert started.wait(timeout=2)
        assert captured["prefecture"] == "kyoto"
    finally:
        service._executor.shutdown(wait=True)


def test_resume_incomplete_skips_far_dates_but_keeps_pending(monkeypatch):
    far = date(2099, 1, 1)
    nearby = date.today()
    pending_date = date(2099, 12, 1)
    monkeypatch.setattr("japan_events.api.jobs.list_incomplete_dates", lambda: [far, nearby])
    monkeypatch.setattr(
        "japan_events.api.jobs.list_pending_refreshes",
        lambda: [(pending_date, ["osaka"])],
    )

    service = ThreadedScrapeService(max_workers=1)
    started: list[tuple[date, str | None]] = []

    def fake_start(target, *, prefecture=None, force=False):
        started.append((target, prefecture))
        return True

    service.start_scrape = fake_start  # type: ignore[method-assign]
    resumed = service.resume_incomplete()
    assert nearby.isoformat() in resumed
    assert far.isoformat() not in resumed
    assert pending_date.isoformat() in resumed
    assert any(target == pending_date and prefecture == "osaka" for target, prefecture in started)


def test_get_or_start_scrapes_only_requested_prefecture(monkeypatch):
    started: dict[str, str | None] = {}

    def fake_start(target, *, prefecture=None, force=False):
        started["prefecture"] = prefecture
        return True

    monkeypatch.setattr("japan_events.api.jobs.site_result_ids", lambda target: set())
    monkeypatch.setattr("japan_events.api.jobs.live_combined", lambda target: None)

    service = ThreadedScrapeService(max_workers=1)
    service.start_scrape = fake_start  # type: ignore[method-assign]
    combined, busy = service.get_or_start(date(2099, 1, 1), prefecture="okinawa")
    assert combined is None
    assert busy is True
    assert started["prefecture"] == "okinawa"


def test_get_or_start_reuses_existing_prefecture_file(monkeypatch):
    started: list[int] = []

    def fake_start(target, *, prefecture=None, force=False):
        started.append(1)
        return True

    monkeypatch.setattr("japan_events.api.jobs.site_result_ids", lambda target: {"okinawa"})
    monkeypatch.setattr("japan_events.api.jobs.live_combined", lambda target: object())

    service = ThreadedScrapeService(max_workers=1)
    service.start_scrape = fake_start  # type: ignore[method-assign]
    combined, busy = service.get_or_start(date(2099, 1, 1), prefecture="okinawa")
    assert busy is False
    assert combined is not None
    assert started == []
