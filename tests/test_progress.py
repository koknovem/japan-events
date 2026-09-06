from japan_events.progress import JobProgress


def test_percent_only_moves_when_sites_finish():
    progress = JobProgress("2026-09-06")
    progress.handle(
        "init",
        {
            "sites": [
                {"id": "tokyo", "prefecture": "Tokyo"},
                {"id": "kyoto", "prefecture": "Kyoto"},
            ]
        },
    )
    snap = progress.snapshot()
    assert snap["phase"] == "scraping"
    assert snap["total"] == 2
    assert snap["percent"] == 0

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
    finally:
        service._executor.shutdown(wait=False)
