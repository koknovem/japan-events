"""Date-listing URL placeholders for Hokkaido–Tochigi official calendars."""
from datetime import date

from japan_events.adapters.configured import _apply_api_date
from japan_events.adapters.loader import load_adapter_yaml
from japan_events.adapters.sites.ibaraki import _dated_event_php
from japan_events.adapters.sites.tochigi import _with_month
from japan_events.langs import SCRAPE_LANGS


def test_hokkaido_days_ymd_placeholder():
    url = "https://www.visit-hokkaido.jp/event/index_1_2____1____.html?days={ymd}"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == "https://www.visit-hokkaido.jp/event/index_1_2____1____.html?days=20270313"


def test_aomori_ymd_in_filename():
    url = "https://aomori-tourism.com/event/index_1_2_____{ymd}____.html"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == "https://aomori-tourism.com/event/index_1_2_____20270313____.html"


def test_yamagata_days_ymd_placeholder():
    url = "https://yamagatakanko.com/festivals/index_1_2______1____.html?days={ymd}"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == "https://yamagatakanko.com/festivals/index_1_2______1____.html?days=20270313"


def test_iwate_ondate_start_end():
    url = "https://iwatetabi.jp/events/?ondate_start={date}&ondate_end={date}"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert "ondate_start=2027-03-13" in dated
    assert "ondate_end=2027-03-13" in dated


def test_miyagi_ymd_query():
    url = "https://www.miyagi-kankou.or.jp/calendar/?ymd={ymd}"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == "https://www.miyagi-kankou.or.jp/calendar/?ymd=20270313"


def test_fukushima_event_start_end():
    url = (
        "https://www.tif.ne.jp/jp/entry/?type=event"
        "&eventStart={date}&eventEnd={date}&search=on"
    )
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert "eventStart=2027-03-13" in dated
    assert "eventEnd=2027-03-13" in dated
    assert "search=on" in dated


def test_ibaraki_event_php_ymd_split():
    url = _dated_event_php("https://www.ibarakiguide.jp/event.php", date(2027, 3, 13))
    assert "search_start_year=2027" in url
    assert "search_start_month=3" in url
    assert "search_start_day=13" in url
    assert "search_end_year=2027" in url


def test_tochigi_month_yyyy_mm():
    url = _with_month("https://www.tochigiji.or.jp/event/", "2027-03")
    assert url == "https://www.tochigiji.or.jp/event/?month=2027-03"
    # EN visit-tochigi listings are left alone
    en = "https://www.visit-tochigi.com/seasons-in-tochigi/events/"
    assert _with_month(en, "2027-03") == en


def test_assigned_sites_keep_unique_lang_urls():
    for site_id in (
        "hokkaido",
        "aomori",
        "iwate",
        "miyagi",
        "akita",
        "yamagata",
        "fukushima",
        "ibaraki",
        "tochigi",
    ):
        cfg = load_adapter_yaml(site_id)
        assert cfg is not None
        urls = [cfg.urls_by_lang[lang] for lang in SCRAPE_LANGS]
        assert len(set(urls)) == 4, f"{site_id} urls_by_lang not unique: {urls}"
