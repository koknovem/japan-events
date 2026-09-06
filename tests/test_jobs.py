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

    service = ThreadedScrapeService(max_workers=1)
    try:
        service.start_scrape(date(2099, 3, 1))
        assert started.wait(timeout=2)
        assert service.maybe_refresh(date(2026, 9, 6)) is False
        assert service.status()["inflight_dates"] == ["2099-03-01"]
    finally:
        release.set()
        service._executor.shutdown(wait=True)
