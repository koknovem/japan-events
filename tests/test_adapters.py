from japan_events.adapters.loader import list_adapter_yaml_ids, load_adapter_yaml
from japan_events.langs import SCRAPE_LANGS, resolve_lang_urls
from japan_events.registry import get_adapter, load_sites


def test_each_site_has_unique_named_adapter():
    sites = load_sites()
    ids = [site.id for site in sites]
    assert len(ids) == len(set(ids))
    yaml_ids = set(list_adapter_yaml_ids())
    seen_adapters: set[str] = set()
    for site in sites:
        assert site.adapter == site.id, f"{site.id} must use its own adapter id"
        assert site.id in yaml_ids, f"missing data/adapters/{site.id}.yaml"
        assert site.adapter not in seen_adapters
        seen_adapters.add(site.adapter)
        adapter = get_adapter(site)
        assert adapter.name == site.id


def test_each_adapter_lists_all_scrape_languages():
    for site in load_sites():
        cfg = load_adapter_yaml(site.id)
        assert cfg is not None
        langs = cfg.urls_by_lang
        missing = [lang for lang in SCRAPE_LANGS if lang not in langs]
        assert not missing, f"{site.id} missing urls_by_lang: {missing}"
        resolved = resolve_lang_urls(site, cfg)
        assert set(SCRAPE_LANGS) <= set(resolved), (
            f"{site.id} resolve_lang_urls dropped languages: {resolved}"
        )


def test_tokyo_language_urls_are_distinct():
    cfg = load_adapter_yaml("tokyo")
    assert cfg is not None
    urls = list(cfg.urls_by_lang.values())
    assert len(set(urls)) == 4


ASSIGNED_DATED_SITES = (
    "nara",
    "wakayama",
    "tottori",
    "shimane",
    "okayama",
    "hiroshima",
    "yamaguchi",
    "tokushima",
    "kagawa",
    "ehime",
)


def test_assigned_sites_language_urls_are_distinct():
    for site_id in ASSIGNED_DATED_SITES:
        cfg = load_adapter_yaml(site_id)
        assert cfg is not None, site_id
        urls = list(cfg.urls_by_lang.values())
        assert len(urls) == 4, site_id
        assert len(set(urls)) == 4, f"{site_id} duplicate urls_by_lang: {urls}"
        resolved = resolve_lang_urls(
            next(s for s in load_sites() if s.id == site_id),
            cfg,
        )
        assert set(SCRAPE_LANGS) <= set(resolved), f"{site_id} collapsed langs: {resolved}"


def test_nara_adapter_honors_dated_listing_url():
    from datetime import date

    from japan_events.adapters.sites.nara import NaraAdapter
    from japan_events.models import SiteConfig

    site = SiteConfig(
        id="nara",
        name="Nara",
        region="Tokai & Kansai",
        home_url="https://www.visitnara.jp/",
        event_url="https://www.visitnara.jp/event-calendar/?from={date}&to={date}",
        adapter="nara",
    )
    adapter = NaraAdapter(site)
    listing = adapter._listing_url(date(2027, 3, 13))
    assert listing == "https://www.visitnara.jp/event-calendar/?from=2027-03-13&to=2027-03-13"

    site.event_url = "https://www.pref.nara.lg.jp/cgi-bin/event_cal_multi/calendar.cgi"
    listing = adapter._listing_url(date(2027, 3, 13))
    assert "year=2027" in listing
    assert "month=3" in listing
    assert "day=13" in listing


def test_assigned_sites_dated_placeholders():
    from datetime import date

    from japan_events.adapters.configured import _apply_api_date

    target = date(2027, 3, 13)
    kagawa = load_adapter_yaml("kagawa")
    assert kagawa is not None
    dated = _apply_api_date(kagawa.urls_by_lang["ja"], target, {})
    assert "program_date[]=20270313" in dated

    ehime = load_adapter_yaml("ehime")
    assert ehime is not None
    dated = _apply_api_date(ehime.urls_by_lang["ja"], target, {})
    assert "program_date[]=20270313" in dated

    shimane = load_adapter_yaml("shimane")
    assert shimane is not None
    dated = _apply_api_date(shimane.urls_by_lang["ja"], target, {})
    assert "date_start=2027-03-13" in dated
    assert "date_end=2027-03-13" in dated

    hiroshima = load_adapter_yaml("hiroshima")
    assert hiroshima is not None
    dated = _apply_api_date(hiroshima.urls_by_lang["en"], target, hiroshima.api_date_keys)
    assert "start_date=2027-03-13" in dated
    assert "end_date=2027-03-13" in dated
