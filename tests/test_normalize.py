from datetime import date

from japan_events.models import Event
from japan_events.normalize import event_overlaps, parse_date_range, rewrite_date_query


def test_parse_japanese_range():
    start, end = parse_date_range("2026年9月1日〜2026年9月10日")
    assert start == date(2026, 9, 1)
    assert end == date(2026, 9, 10)


def test_parse_slash_range_cross_year():
    start, end = parse_date_range("2026/12/20-1/5", default_year=2026)
    assert start == date(2026, 12, 20)
    assert end == date(2027, 1, 5)


def test_overlap_inclusive():
    event = Event(
        prefecture="Tokyo",
        title="Fest",
        start_date="2026-09-01",
        end_date="2026-09-10",
        source="test",
    )
    assert event_overlaps(event, date(2026, 9, 6))
    assert not event_overlaps(event, date(2026, 9, 11))


def test_parse_english_month_range():
    start, end = parse_date_range("Apr 1, 2026 - Mar 31, 2027")
    assert start == date(2026, 4, 1)
    assert end == date(2027, 3, 31)


def test_parse_aichi_weekday_paren_range():
    start, end = parse_date_range(
        "Nagoya-City Film Fest 2026 Sep 2,2026(Wed) ～ Sep 6(Sun)",
        default_year=2026,
    )
    assert start == date(2026, 9, 2)
    assert end == date(2026, 9, 6)


def test_parse_jp_multi_days():
    from japan_events.normalize import parse_jp_multi_days

    days = parse_jp_multi_days("2026年9月5・6・13・19日", default_year=2026)
    assert days == [
        date(2026, 9, 5),
        date(2026, 9, 6),
        date(2026, 9, 13),
        date(2026, 9, 19),
    ]


def test_rewrite_date_query():
    url = "https://example.com/api?date=2024-01-01&q=fest"
    assert "date=2026-09-06" in rewrite_date_query(url, date(2026, 9, 6))


def test_rewrite_date_query_from_to():
    url = "https://www.okinawastory.jp/event/list?from=2020-01-01&to=2020-01-01"
    rewritten = rewrite_date_query(url, date(2027, 3, 13))
    assert "from=2027-03-13" in rewritten
    assert "to=2027-03-13" in rewritten


def test_apply_api_date_placeholders():
    from japan_events.adapters.configured import _apply_api_date

    url = "https://www.okinawastory.jp/event/list?from={date}&to={date}"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == "https://www.okinawastory.jp/event/list?from=2027-03-13&to=2027-03-13"


def test_apply_api_date_slash_placeholder():
    from japan_events.adapters.configured import _apply_api_date

    url = "https://kochi-tabi.jp/search_event.html?type=event&start_date={date_slash}&end_date={date_slash}"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == (
        "https://kochi-tabi.jp/search_event.html?type=event&start_date=2027/03/13&end_date=2027/03/13"
    )


def test_apply_api_date_year_month_day():
    from japan_events.adapters.configured import _apply_api_date

    url = "https://www.yamanashi-kankou.jp/search/event.php?y={year}&m={month}&d={day}&mode=event"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == (
        "https://www.yamanashi-kankou.jp/search/event.php?y=2027&m=03&d=13&mode=event"
    )


def test_apply_api_date_month_underscore():
    from japan_events.adapters.configured import _apply_api_date

    url = "https://www.awanavi.jp/event/?event-yearmonth[]={month_underscore}"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert "event-yearmonth%5B%5D=2027_03" in dated or "event-yearmonth[]=2027_03" in dated


def test_apply_api_date_path_event_date_st_ed():
    from japan_events.adapters.configured import _apply_api_date

    url = (
        "https://www.gotokyo.org/en/travel-directory/result/index/"
        "event_date_st/{date}/event_date_ed/{date}"
    )
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == (
        "https://www.gotokyo.org/en/travel-directory/result/index/"
        "event_date_st/2027-03-13/event_date_ed/2027-03-13"
    )


def test_apply_api_date_ymd_days_param():
    from japan_events.adapters.configured import _apply_api_date

    url = "https://www.hot-ishikawa.jp/event/index_1_2____1____.html?days={ymd}"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == "https://www.hot-ishikawa.jp/event/index_1_2____1____.html?days=20270313"


def test_apply_api_date_aichi_s_term():
    from japan_events.adapters.configured import _apply_api_date

    url = "https://aichinow.pref.aichi.jp/events/?s_term_from={date}&s_term_to={date}&search_flg=1"
    dated = _apply_api_date(url, date(2027, 3, 13), {})
    assert dated == (
        "https://aichinow.pref.aichi.jp/events/?s_term_from=2027-03-13"
        "&s_term_to=2027-03-13&search_flg=1"
    )
