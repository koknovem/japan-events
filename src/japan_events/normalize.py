from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from dateutil import parser as date_parser

from japan_events.models import Event

_JP_FULL = re.compile(
    r"(?P<y>\d{4})\s*年\s*(?P<m>\d{1,2})\s*月\s*(?P<d>\d{1,2})\s*日?"
)
_JP_MD = re.compile(r"(?P<m>\d{1,2})\s*月\s*(?P<d>\d{1,2})\s*日")
_ISOISH = re.compile(
    r"(?P<y>\d{4})[-/.](?P<m>\d{1,2})[-/.](?P<d>\d{1,2})"
)
_REIWA = re.compile(
    r"令和\s*(?P<y>\d{1,2})\s*年\s*(?P<m>\d{1,2})\s*月\s*(?P<d>\d{1,2})\s*日?"
)
# e.g. 2026年9月5・6・13・19日  or  9月5・6日
_JP_MULTI_DAYS = re.compile(
    r"(?:(?P<y>\d{4})\s*年\s*)?(?P<m>\d{1,2})\s*月\s*"
    r"(?P<days>\d{1,2}(?:\s*[・･/,、]\s*\d{1,2})+)\s*日"
)
_RANGE_SEP = re.compile(
    r"(?:\s*[~～〜–—]\s*|(?<=\d)\s*-\s*(?=\d)|\s+-\s+|\s+(?:to|thru|through|until|至)\s+)",
    re.I,
)
# Strip weekday annotations like (Wed) / （土） before parsing.
_WEEKDAY_PAREN = re.compile(r"[（(][^）)]{0,8}[）)]")

TITLE_KEYS = (
    "title",
    "name",
    "event_name",
    "eventName",
    "event_title",
    "ttl",
    "headline",
    "subject",
    "eventTitle",
    "getName",
    "nameJp",
)
_MD_SLASH = re.compile(r"(?P<m>\d{1,2})/(?P<d>\d{1,2})")
DATE_START_KEYS = (
    "start_date",
    "startDate",
    "start",
    "from",
    "begin",
    "begin_date",
    "date_from",
    "dateFrom",
    "opendate",
    "open_date",
    "event_date",
    "eventDate",
    "date",
    "period_start",
    "periodStart",
    "event_start",
    "dtstart",
)
DATE_END_KEYS = (
    "end_date",
    "endDate",
    "end",
    "to",
    "until",
    "finish",
    "date_to",
    "dateTo",
    "closedate",
    "close_date",
    "period_end",
    "periodEnd",
    "event_end",
    "dtend",
)
TIME_START_KEYS = ("start_time", "startTime", "time_from", "open_time", "opentime")
TIME_END_KEYS = ("end_time", "endTime", "time_to", "close_time", "closetime")
VENUE_KEYS = ("venue", "place", "location", "spot", "facility", "hall", "address")
AREA_KEYS = ("area", "region", "city", "prefecture", "district", "area_name")
CATEGORY_KEYS = ("category", "cat", "genre", "type", "tag", "event_type")
DESC_KEYS = ("description", "desc", "summary", "body", "text", "content", "lead")
URL_KEYS = ("url", "link", "href", "permalink", "detail_url", "detailUrl", "pc_url")
IMAGE_KEYS = ("image", "image_url", "imageUrl", "thumbnail", "thumb", "img", "photo")


def _as_date(value: Any, default_year: int | None = None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        if 1e9 < ts < 2e10:
            try:
                return datetime.utcfromtimestamp(ts).date()
            except (OverflowError, OSError, ValueError):
                return None
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "undefined"}:
        return None
    text = _WEEKDAY_PAREN.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Normalize "Sep 2,2026" → "Sep 2, 2026"
    text = re.sub(r"([A-Za-z]{3,9}\s+\d{1,2}),(\d{4})", r"\1, \2", text)
    if text[:10].isdigit() is False and "T" in text:
        try:
            return date_parser.parse(text, fuzzy=True).date()
        except (ValueError, OverflowError, TypeError):
            pass
    reiwa = _REIWA.search(text)
    if reiwa:
        year = 2018 + int(reiwa.group("y"))
        return date(year, int(reiwa.group("m")), int(reiwa.group("d")))
    full = _JP_FULL.search(text)
    if full:
        return date(int(full.group("y")), int(full.group("m")), int(full.group("d")))
    iso = _ISOISH.search(text)
    if iso:
        y, m, d = int(iso.group("y")), int(iso.group("m")), int(iso.group("d"))
        if 1 <= m <= 12 and 1 <= d <= 31:
            try:
                return date(y, m, d)
            except ValueError:
                return None
    md = _JP_MD.search(text)
    if md and default_year:
        try:
            return date(default_year, int(md.group("m")), int(md.group("d")))
        except ValueError:
            return None
    slash_md = _MD_SLASH.search(text)
    if slash_md and default_year and not re.search(r"\d{4}", text):
        try:
            return date(default_year, int(slash_md.group("m")), int(slash_md.group("d")))
        except ValueError:
            return None
    try:
        parsed = date_parser.parse(text, fuzzy=True, default=datetime(default_year or 2000, 1, 1))
        if default_year is None and parsed.year == 2000 and not re.search(r"\d{4}", text):
            return None
        return parsed.date()
    except (ValueError, OverflowError, TypeError):
        return None


def parse_jp_multi_days(text: str, *, default_year: int | None = None) -> list[date]:
    """Parse 2026年9月5・6・13・19日 into discrete dates."""
    match = _JP_MULTI_DAYS.search(text)
    if not match:
        return []
    year = int(match.group("y")) if match.group("y") else default_year
    if not year:
        return []
    month = int(match.group("m"))
    days = [int(x) for x in re.findall(r"\d{1,2}", match.group("days"))]
    out: list[date] = []
    for day in days:
        try:
            out.append(date(year, month, day))
        except ValueError:
            continue
    return out


def parse_date_range(
    text: Any,
    *,
    default_year: int | None = None,
) -> tuple[date | None, date | None]:
    if text is None:
        return None, None
    if not isinstance(text, str):
        d = _as_date(text, default_year)
        return d, d
    raw = text.strip()
    if not raw:
        return None, None
    multi = parse_jp_multi_days(raw, default_year=default_year)
    if multi:
        return min(multi), max(multi)
    parts = _RANGE_SEP.split(raw, maxsplit=1)
    if len(parts) == 2 and parts[0] and parts[1]:
        start = _as_date(parts[0], default_year)
        end = _as_date(parts[1], default_year or (start.year if start else None))
        # When the left side is a long title+date blob, search for a date token
        if start is None:
            for match in re.finditer(
                r"([A-Z][a-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}"
                r"|\d{4}\s*[年./-]\s*\d{1,2}\s*[月./-]\s*\d{1,2}"
                r"|\d{4}[-/.]\d{1,2}[-/.]\d{1,2})",
                parts[0],
            ):
                start = _as_date(match.group(1), default_year)
                if start:
                    break
        if start and end and end < start and end.year == start.year:
            # e.g. 2026/12/20-1/5
            try:
                end = date(start.year + 1, end.month, end.day)
            except ValueError:
                pass
        if start or end:
            return start, end or start
    single = _as_date(raw, default_year)
    return single, single


def first_value(obj: dict[str, Any], keys: tuple[str, ...]) -> Any:
    lower = {str(k).lower(): v for k, v in obj.items()}
    for key in keys:
        if key in obj and obj[key] not in (None, "", []):
            return obj[key]
        lk = key.lower()
        if lk in lower and lower[lk] not in (None, "", []):
            return lower[lk]
    return None


def looks_like_event_dict(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    title = first_value(obj, TITLE_KEYS)
    date_val = first_value(obj, DATE_START_KEYS + DATE_END_KEYS + ("period", "term", "schedule"))
    if not title:
        return False
    if date_val:
        return True
    keys = {str(k).lower() for k in obj}
    return bool(keys & {"venue", "place", "location", "event_id", "eventid", "event"})


def extract_eventish_dicts(payload: Any, limit: int = 400) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if len(found) >= limit:
            return
        if isinstance(node, list):
            event_items = [x for x in node if looks_like_event_dict(x)]
            if event_items and len(event_items) >= max(1, len(node) // 3):
                for item in event_items:
                    if len(found) >= limit:
                        return
                    found.append(item)
                return
            for item in node:
                walk(item)
            return
        if isinstance(node, dict):
            if looks_like_event_dict(node):
                found.append(node)
            for key, value in node.items():
                if str(key).lower() in {"html", "css", "script"}:
                    continue
                walk(value)

    walk(payload)
    return found


def dict_to_event(
    obj: dict[str, Any],
    *,
    prefecture: str,
    source: str,
    default_year: int | None = None,
) -> Event | None:
    title = first_value(obj, TITLE_KEYS)
    if not title:
        return None
    title_s = str(title).strip()
    if not title_s or len(title_s) > 300:
        return None

    period = first_value(obj, ("period", "term", "schedule", "date_text", "dateText", "hold_date", "eventDatePeriod"))
    start = _as_date(first_value(obj, DATE_START_KEYS), default_year)
    end = _as_date(first_value(obj, DATE_END_KEYS), default_year)
    nested = obj.get("event_date") or obj.get("eventDate")
    if isinstance(nested, list) and nested and isinstance(nested[0], dict):
        start = start or _as_date(nested[0].get("start_date") or nested[0].get("startDate"), default_year)
        end = end or _as_date(nested[0].get("end_date") or nested[0].get("endDate"), default_year)
    elif isinstance(nested, dict):
        start = start or _as_date(nested.get("start_date") or nested.get("startDate"), default_year)
        end = end or _as_date(nested.get("end_date") or nested.get("endDate"), default_year)
    # start_date fields often contain a full range string from HTML extractors
    raw_start = first_value(obj, DATE_START_KEYS)
    if not (start and end) and isinstance(raw_start, str) and _RANGE_SEP.search(raw_start):
        p_start, p_end = parse_date_range(raw_start, default_year=default_year)
        start = start or p_start
        end = end or p_end
    if period and not (start and end):
        p_start, p_end = parse_date_range(period, default_year=default_year)
        start = start or p_start
        end = end or p_end
    # Last resort: scan title/description for a date range
    if not (start and end):
        for blob_key in ("description", "title", "name"):
            blob = obj.get(blob_key)
            if isinstance(blob, str) and _RANGE_SEP.search(blob):
                p_start, p_end = parse_date_range(blob, default_year=default_year)
                if p_start or p_end:
                    start = start or p_start
                    end = end or p_end
                    break
            elif isinstance(blob, str):
                # Try to extract a recognizable range substring first
                import re as _re
                m = _re.search(
                    r"([A-Z][a-z]{2,9}\s+\d{1,2},?\s*\d{4}.*?[~～〜–-].*?[A-Z][a-z]{2,9}\s+\d{1,2}"
                    r"|\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日?.*?[~～〜–-].*?\d{1,2}\s*月?\s*\d{1,2}\s*日?)",
                    blob,
                )
                if m:
                    p_start, p_end = parse_date_range(m.group(0), default_year=default_year)
                    start = start or p_start
                    end = end or p_end
                    if start or end:
                        break
    if start and not end:
        end = start
    if end and not start:
        start = end

    venue = first_value(obj, VENUE_KEYS)
    if isinstance(venue, dict):
        venue = first_value(venue, ("name", "title", "address") + VENUE_KEYS)
    image = first_value(obj, IMAGE_KEYS)
    if isinstance(image, dict):
        image = first_value(image, ("url", "src", "href"))
    elif isinstance(image, list) and image:
        image = image[0] if isinstance(image[0], str) else first_value(image[0], ("url", "src"))

    url = first_value(obj, URL_KEYS)
    if isinstance(url, dict):
        url = first_value(url, ("href", "url"))

    desc = first_value(obj, DESC_KEYS)
    if isinstance(desc, str) and len(desc) > 800:
        desc = desc[:797] + "..."

    return Event(
        prefecture=prefecture,
        title=title_s,
        start_date=start.isoformat() if start else None,
        end_date=end.isoformat() if end else None,
        start_time=_stringify(first_value(obj, TIME_START_KEYS)),
        end_time=_stringify(first_value(obj, TIME_END_KEYS)),
        venue=_stringify(venue),
        area=_stringify(first_value(obj, AREA_KEYS)),
        category=_stringify(first_value(obj, CATEGORY_KEYS)),
        description=_stringify(desc),
        url=_stringify(url),
        image_url=_stringify(image),
        source=source,
    )


def event_overlaps(event: Event, target: date) -> bool:
    start, end = None, None
    if event.start_date:
        start = _as_date(event.start_date)
    if event.end_date:
        end = _as_date(event.end_date)
    if start is None and end is None:
        return False
    if start is None:
        start = end
    if end is None:
        end = start
    assert start is not None and end is not None
    if end < start:
        start, end = end, start
    return start <= target <= end


def filter_events(events: list[Event], target: date) -> list[Event]:
    return [e for e in events if event_overlaps(e, target)]


def dedupe_events(events: list[Event]) -> list[Event]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[Event] = []
    for event in events:
        key = (
            event.title.strip().lower(),
            event.start_date or "",
            (event.url or "").split("?")[0],
            event.lang or "ja",
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(event)
    return out


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text or None


def rewrite_date_query(url: str, target: date) -> str:
    """Replace common date query params with the scrape target."""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    if not parts.query:
        return url
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    replacements = {
        "date",
        "day",
        "ymd",
        "target_date",
        "targetdate",
        "event_date",
        "eventdate",
        "start",
        "start_date",
        "startdate",
        "from",
        "from_date",
        "to",
        "to_date",
        "ymd1",
        "calendar_date",
    }
    changed = False
    new_pairs: list[tuple[str, str]] = []
    iso = target.isoformat()
    compact = target.strftime("%Y%m%d")
    slash = target.strftime("%Y/%m/%d")
    for key, value in pairs:
        lk = key.lower()
        if lk in replacements or lk.endswith("date") or lk.endswith("_day"):
            sample = value.replace("-", "").replace("/", "")
            if len(sample) == 8 and sample.isdigit():
                new_pairs.append((key, compact if "-" not in value and "/" not in value else (
                    slash if "/" in value else iso
                )))
                changed = True
                continue
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                new_pairs.append((key, iso))
                changed = True
                continue
            if re.fullmatch(r"\d{4}/\d{1,2}/\d{1,2}", value):
                new_pairs.append((key, slash))
                changed = True
                continue
        new_pairs.append((key, value))
    if not changed:
        return url
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(new_pairs, doseq=True), parts.fragment))
