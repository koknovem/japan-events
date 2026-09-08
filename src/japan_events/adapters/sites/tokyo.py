from __future__ import annotations

from datetime import date

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.configured import _apply_api_date
from japan_events.adapters.generic import harvest_events
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.registry import register

_DEFAULT_LISTING = (
    "https://www.gotokyo.org/en/travel-directory/result/index/"
    "template/152,153,154,155,156,157,158,159,160,161,222,259/"
    "event_date_st/{date}/event_date_ed/{date}"
)


def _is_date_scoped(url: str) -> bool:
    return any(token in url for token in ("{date}", "{ymd}", "{start}", "{end}", "event_date_st", "event_date_ed"))


@register("tokyo")
class TokyoAdapter(BaseAdapter):
    """GO TOKYO travel-directory date search (follows site.event_url)."""

    name = "tokyo"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        raw = self.site.event_url or _DEFAULT_LISTING
        listing = _apply_api_date(raw, target, {})
        urls = [listing]
        if not _is_date_scoped(raw):
            alt = listing.replace("/calendar/", "/event-calendar/").replace("/calendar", "/event-calendar")
            if alt != listing:
                urls.append(alt)
        merged: list[Event] = []
        notes: list[str] = []
        seen = set()
        for url in urls:
            try:
                await session.goto(url)
            except Exception as exc:
                notes.append(f"goto_error:{exc}")
                continue
            if not _is_date_scoped(raw):
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
