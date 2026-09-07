from datetime import date

from japan_events.models import Event, SiteResult
from japan_events.storage import live_combined, load_combined, write_combined, write_site_result


def _site(site_id: str, title: str, count: int = 1) -> SiteResult:
    events = [
        Event(prefecture=site_id, title=f"{title}-{i}", source="https://example.test")
        for i in range(count)
    ]
    return SiteResult(
        prefecture=site_id,
        id=site_id,
        ok=True,
        date="2099-06-01",
        event_count=len(events),
        events=events,
    )


def test_live_combined_shows_finished_sites_without_writing_all_json(tmp_path):
    target = date(2099, 6, 1)
    write_site_result(_site("tokyo", "Matsuri", 2), target, root=tmp_path)
    snap = live_combined(target, root=tmp_path)
    assert snap is not None
    assert snap.event_count == 2
    assert {site.id for site in snap.sites} == {"tokyo"}
    assert not (tmp_path / "output" / "2099-06-01" / "all.json").exists()


def test_live_combined_overlays_refreshed_site_on_cached_all_json(tmp_path):
    target = date(2099, 6, 1)
    old_tokyo = _site("tokyo", "Old", 1)
    kyoto = _site("kyoto", "Gion", 3)
    write_combined([old_tokyo, kyoto], target, root=tmp_path)

    write_site_result(_site("tokyo", "New", 5), target, root=tmp_path)
    snap = live_combined(target, root=tmp_path)
    assert snap is not None
    by_id = {site.id: site for site in snap.sites}
    assert by_id["tokyo"].event_count == 5
    assert by_id["tokyo"].events[0].title.startswith("New")
    assert by_id["kyoto"].event_count == 3
    cached = load_combined(target, root=tmp_path)
    assert cached is not None
    assert {site.id: site.event_count for site in cached.sites}["tokyo"] == 1
