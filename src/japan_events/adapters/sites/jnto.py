from __future__ import annotations

from datetime import date

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.generic import harvest_events
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.registry import register


@register("jnto")
class JntoAdapter(BaseAdapter):
    """JNTO japan.travel events listing (local-government list is a directory, not a feed)."""

    name = "jnto"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        url = self.site.event_url or "https://www.japan.travel/en/events/"
        await session.goto(url)
        events, notes = await harvest_events(session, target, source_label=url)
        session.page_notes = notes  # type: ignore[attr-defined]
        return events
