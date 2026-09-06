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
