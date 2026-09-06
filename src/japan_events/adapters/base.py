from __future__ import annotations

from datetime import date

from japan_events.browser import BrowserSession
from japan_events.models import Event, SiteConfig


class BaseAdapter:
    name = "base"

    def __init__(self, site: SiteConfig) -> None:
        self.site = site

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        raise NotImplementedError
