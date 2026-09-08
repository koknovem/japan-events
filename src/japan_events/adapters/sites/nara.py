from __future__ import annotations

from datetime import date
from typing import Any

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.configured import _apply_api_date
from japan_events.adapters.generic import harvest_events
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.normalize import dedupe_events, dict_to_event, filter_events, parse_date_range
from japan_events.registry import register

API_URL = "https://www.visitnara.jp/travel-directory/api/data/"
VISITNARA_CALENDAR = "https://www.visitnara.jp/event-calendar/?from={date}&to={date}"


def _nara_fields(item: dict[str, Any]) -> dict[str, Any]:
    fields = item.get("fields")
    if isinstance(fields, dict):
        merged = dict(item)
        merged.update(fields)
        return merged
    return item


def _nara_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return str(first.get("name") or first.get("title") or "")
        return str(first)
    if isinstance(value, dict):
        return str(value.get("name") or value.get("title") or "")
    return ""


def _payload_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "venues", "lists"):
        items = payload.get(key)
        if isinstance(items, list) and items:
            return items
    return []


@register("nara")
class NaraAdapter(BaseAdapter):
    """Visit Nara travel-directory JSON plus prefecture calendar.cgi day view."""

    name = "nara"

    def _listing_url(self, target: date) -> str:
        listing = self.site.event_url or VISITNARA_CALENDAR
        listing = _apply_api_date(listing, target, {})
        if "event_cal_multi/calendar.cgi" in listing and "year=" not in listing:
            sep = "&" if "?" in listing else "?"
            listing = (
                f"{listing}{sep}type=3&year={target.year}"
                f"&month={target.month}&day={target.day}"
            )
        return listing

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        listing = self._listing_url(target)
        notes: list[str] = []
        host = listing.lower()
        html_hosts = (
            "pref.nara.lg.jp",
            "nara-kankou.or.jp",
            "narashikanko.or.jp",
        )
        if any(h in host for h in html_hosts):
            await session.goto(listing)
            if "pref.nara.lg.jp" in host:
                await session.click_calendar_date(target)
            events, html_notes = await harvest_events(session, target, source_label=listing)
            session.page_notes = html_notes  # type: ignore[attr-defined]
            return events
        try:
            payload = await session.fetch_json(API_URL, target)
        except Exception as exc:
            notes.append(f"api_error:{exc}")
            await session.goto(listing)
            events, html_notes = await harvest_events(session, target, source_label=listing)
            session.page_notes = "; ".join(notes + [html_notes])  # type: ignore[attr-defined]
            return events

        items = _payload_items(payload)
        collected: list[Event] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            row = _nara_fields(item)
            period = row.get("eventDatePeriod") or row.get("event_date") or ""
            category = _nara_text(row.get("category") or row.get("detailType") or "")
            looks_event = bool(period) or "event" in category.lower()
            if not looks_event:
                continue
            start, end = parse_date_range(period, default_year=target.year)
            raw = {
                "title": row.get("name") or row.get("getName") or row.get("nameJp"),
                "start_date": start.isoformat() if start else None,
                "end_date": end.isoformat() if end else None,
                "period": period,
                "venue": _nara_text(row.get("location")) or row.get("adress") or row.get("addressJp"),
                "area": _nara_text(row.get("subLocation")),
                "category": category or None,
                "url": row.get("url") or row.get("link"),
                "image": row.get("photo"),
            }
            event = dict_to_event(
                raw,
                prefecture=self.site.name,
                source=f"{API_URL}#api",
                default_year=target.year,
            )
            if event:
                collected.append(event)
        notes.append(f"api:{len(items)}")
        matched = filter_events(dedupe_events(collected), target)
        if not matched:
            await session.goto(listing)
            extra, html_notes = await harvest_events(session, target, source_label=listing)
            notes.append(html_notes)
            matched = dedupe_events(matched + extra)
        session.page_notes = "; ".join(notes)  # type: ignore[attr-defined]
        return matched
