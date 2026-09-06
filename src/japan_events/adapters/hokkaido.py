from __future__ import annotations

from datetime import date

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.generic import harvest_events
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.registry import register


@register("hokkaido")
class HokkaidoAdapter(BaseAdapter):
    """HOKKAIDO LOVE! event index uses a JS calendar date picker."""

    name = "hokkaido"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        url = self.site.event_url or "https://www.visit-hokkaido.jp/en/event/"
        await session.goto(url)
        await session.click_calendar_date(target)
        # Re-click the exact day if the widget exposes numbered cells.
        try:
            day = str(target.day)
            loc = session.page.locator("table td, .calendar td, [class*='cal'] a, [class*='cal'] td").filter(
                has_text=day
            )
            if await loc.count():
                await loc.first.click(timeout=2000)
                await session.page.wait_for_timeout(900)
        except Exception:
            pass
        events, notes = await harvest_events(session, target, source_label=url)
        session.page_notes = notes  # type: ignore[attr-defined]
        return events
