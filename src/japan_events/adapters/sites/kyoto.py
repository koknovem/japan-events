from __future__ import annotations

from datetime import date

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.generic import harvest_events
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.registry import register


@register("kyoto")
class KyotoAdapter(BaseAdapter):
    """Kyoto Travel /en/events/ listing."""

    name = "kyoto"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        url = self.site.event_url or "https://kyoto.travel/en/events/"
        await session.goto(url)
        events, notes = await harvest_events(session, target, source_label=url)
        session.page_notes = notes  # type: ignore[attr-defined]
        return events
