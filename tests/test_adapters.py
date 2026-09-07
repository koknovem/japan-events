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
