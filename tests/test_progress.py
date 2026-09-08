from japan_events.progress import JobProgress


def test_new_job_is_queued_until_sites_start():
    progress = JobProgress("2026-09-06")
    snap = progress.snapshot()
    assert snap["queued"] is True
    assert snap["phase"] == "starting"
    assert snap["percent"] == 0

    progress.handle(
        "init",
        {"sites": [{"id": "tokyo", "prefecture": "Tokyo"}], "concurrency": 8},
    )
    snap = progress.snapshot()
    assert snap["queued"] is False
    assert snap["phase"] == "scraping"


def test_percent_only_moves_when_sites_finish():
    progress = JobProgress("2026-09-06")
    progress.handle(
        "init",
        {
            "sites": [
                {"id": "tokyo", "prefecture": "Tokyo"},
                {"id": "kyoto", "prefecture": "Kyoto"},
            ],
            "concurrency": 8,
        },
    )
    snap = progress.snapshot()
    assert snap["phase"] == "scraping"
    assert snap["total"] == 2
    assert snap["percent"] == 0
    assert snap["concurrency"] == 8

    progress.handle("site_start", {"id": "tokyo", "prefecture": "Tokyo"})
    snap = progress.snapshot()
    assert snap["running"] == ["tokyo"]
    assert snap["percent"] == 0
    assert snap["sites"][0]["status"] == "running"

    progress.handle("site_done", {"id": "tokyo", "ok": True, "event_count": 12})
    snap = progress.snapshot()
    assert snap["done"] == 1
    assert snap["percent"] == 50
    assert snap["events_so_far"] == 12
    assert snap["ok_count"] == 1
    assert "tokyo" not in snap["running"]

    progress.handle("site_start", {"id": "kyoto"})
    progress.handle("site_done", {"id": "kyoto", "ok": False, "event_count": 0, "error": "Timeout"})
    snap = progress.snapshot()
    assert snap["done"] == 2
    assert snap["percent"] == 99
    assert snap["ok_count"] == 1
    assert snap["sites"][1]["status"] == "error"

    progress.handle("combining", {})
    assert progress.snapshot()["phase"] == "combining"
    assert progress.snapshot()["percent"] == 99

    progress.handle("done", {"ok_count": 1, "event_count": 12})
    snap = progress.snapshot()
    assert snap["phase"] == "done"
    assert snap["percent"] == 100
    assert snap["events_so_far"] == 12
    assert snap["queued"] is False

    from japan_events.api.schemas import ScrapeStatusOut

    ScrapeStatusOut.model_validate(
        {
            "inflight_dates": ["2026-09-06"],
            "workers": 2,
            "job": snap,
            "jobs": [snap],
        }
    )


def test_status_exposes_job_snapshot():
    from japan_events.api.jobs import ThreadedScrapeService

    service = ThreadedScrapeService()
    job = JobProgress("2027-01-01")
    job.handle("init", {"sites": [{"id": "osaka", "prefecture": "Osaka"}]})
    job.handle("site_done", {"id": "osaka", "ok": True, "event_count": 3})
    service._progress["2027-01-01"] = job

    try:
        idle = service.status("2026-01-01")
        assert idle["job"] is None
        assert idle["inflight_dates"] == []

        active = service.status("2027-01-01")
        assert active["job"]["done"] == 1
        assert active["job"]["events_so_far"] == 3
        assert active["jobs"][0]["date"] == "2027-01-01"
        assert "running_dates" in active
        assert "queued_dates" in active
    finally:
        service._executor.shutdown(wait=False)


def test_site_concurrency_env_and_cap(monkeypatch):
    from japan_events.settings import DEFAULT_SITE_CONCURRENCY, MAX_SITE_CONCURRENCY, site_concurrency

    monkeypatch.delenv("JAPAN_EVENTS_CONCURRENCY", raising=False)
    assert site_concurrency() == DEFAULT_SITE_CONCURRENCY
    monkeypatch.setenv("JAPAN_EVENTS_CONCURRENCY", "3")
    assert site_concurrency() == 3
    monkeypatch.setenv("JAPAN_EVENTS_CONCURRENCY", "99")
    assert site_concurrency() == MAX_SITE_CONCURRENCY
    assert site_concurrency(2) == 2
    assert site_concurrency(8) == MAX_SITE_CONCURRENCY
    assert site_concurrency(0) == 1


def test_chromium_args_relax_sandbox_in_docker(monkeypatch):
    from japan_events.browser import _chromium_launch_args

    monkeypatch.setenv("JAPAN_EVENTS_DOCKER", "1")
    args = _chromium_launch_args()
    assert "--no-sandbox" in args
    assert "--disable-dev-shm-usage" in args
