from datetime import date

from japan_events.models import Event, SiteConfig, SiteResult
from japan_events.storage import (
    clear_pending_refresh,
    list_cached_dates,
    list_incomplete_dates,
    live_combined,
    load_combined,
    load_pending_refresh,
    missing_site_ids,
    save_pending_refresh,
    site_result_ids,
    write_combined,
    write_site_result,
)


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


def _two_sites():
    return [
        SiteConfig(id="tokyo", name="Tokyo", region="kanto", home_url="https://tokyo.example"),
        SiteConfig(id="kyoto", name="Kyoto", region="kansai", home_url="https://kyoto.example"),
    ]


def test_missing_site_ids_and_incomplete_dates(tmp_path, monkeypatch):
    monkeypatch.setattr("japan_events.storage.load_sites", _two_sites)
    target = date(2099, 6, 2)
    write_site_result(_site("tokyo", "A"), target, root=tmp_path)
    assert site_result_ids(target, root=tmp_path) == {"tokyo"}
    assert missing_site_ids(target, root=tmp_path) == ["kyoto"]
    assert list_incomplete_dates(root=tmp_path) == [target]
    write_site_result(_site("kyoto", "B"), target, root=tmp_path)
    assert missing_site_ids(target, root=tmp_path) == []
    assert list_incomplete_dates(root=tmp_path) == []


def test_list_cached_dates_skips_incomplete_all_json(tmp_path, monkeypatch):
    monkeypatch.setattr("japan_events.storage.load_sites", _two_sites)
    target = date(2099, 6, 3)
    write_combined([_site("tokyo", "Only")], target, root=tmp_path)
    assert list_cached_dates(root=tmp_path) == []
    write_site_result(_site("tokyo", "A"), target, root=tmp_path)
    write_site_result(_site("kyoto", "B"), target, root=tmp_path)
    assert list_cached_dates(root=tmp_path) == ["2099-06-03"]


def test_pending_refresh_roundtrip(tmp_path):
    target = date(2099, 6, 4)
    save_pending_refresh(target, ["tokyo", "osaka"], root=tmp_path)
    assert load_pending_refresh(target, root=tmp_path) == ["tokyo", "osaka"]
    clear_pending_refresh(target, root=tmp_path)
    assert load_pending_refresh(target, root=tmp_path) == []
