from __future__ import annotations

from datetime import date

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.generic import harvest_events
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.registry import register


@register("tokyo")
class TokyoAdapter(BaseAdapter):
    """GO TOKYO event calendar / monthly calendar pages."""

    name = "tokyo"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        urls = [
            self.site.event_url or "https://www.gotokyo.org/en/event-calendar/index.html",
            "https://www.gotokyo.org/en/calendar/index.html",
        ]
        merged: list[Event] = []
        notes: list[str] = []
        seen = set()
        for url in urls:
            try:
                await session.goto(url)
            except Exception as exc:
                notes.append(f"goto_error:{exc}")
                continue
            await session.click_calendar_date(target)
            events, note = await harvest_events(session, target, source_label=url)
            notes.append(note)
            for event in events:
                key = (event.title, event.start_date, event.url)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(event)
        session.page_notes = "; ".join(notes)  # type: ignore[attr-defined]
        return merged
