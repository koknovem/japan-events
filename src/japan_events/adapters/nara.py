from __future__ import annotations

from datetime import date

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.generic import harvest_events
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.normalize import dedupe_events, dict_to_event, filter_events, parse_date_range
from japan_events.registry import register

API_URL = "https://www.visitnara.jp/travel-directory/api/data/"


@register("nara")
class NaraAdapter(BaseAdapter):
    """Visit Nara travel-directory JSON (includes eventDatePeriod)."""

    name = "nara"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        listing = self.site.event_url or "https://www.visitnara.jp/event-calendar/"
        notes: list[str] = []
        if "nara-kankou.or.jp" in listing:
            await session.goto(listing)
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

        items = payload if isinstance(payload, list) else (payload or {}).get("data") or []
        collected: list[Event] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            period = item.get("eventDatePeriod") or item.get("event_date") or ""
            category = str(item.get("category") or item.get("detailType") or "")
            looks_event = bool(period) or "event" in category.lower()
            if not looks_event:
                continue
            start, end = parse_date_range(period, default_year=target.year)
            raw = {
                "title": item.get("name") or item.get("getName") or item.get("nameJp"),
                "start_date": start.isoformat() if start else None,
                "end_date": end.isoformat() if end else None,
                "period": period,
                "venue": item.get("location") or item.get("adress") or item.get("addressJp"),
                "area": item.get("subLocation"),
                "category": category or None,
                "url": item.get("url") or item.get("link"),
                "image": item.get("photo"),
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
