"""Tochigi event list — official filter is month=YYYY-MM, not a day URL."""
from __future__ import annotations

from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from japan_events.adapters.configured import ConfigurableAdapter
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.registry import register


def _with_month(url: str, month: str) -> str:
    if not url or "tochigiji.or.jp" not in url:
        return url
    parts = urlsplit(url)
    pairs = dict(parse_qsl(parts.query, keep_blank_values=True))
    pairs["month"] = month
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), parts.fragment))


@register("tochigi")
class TochigiAdapter(ConfigurableAdapter):
    """とちぎ旅ネット GET month=YYYY-MM (checkbox filter)."""

    name = "tochigi"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        month = target.strftime("%Y-%m")
        if self.config.event_url:
            self.config.event_url = _with_month(self.config.event_url, month)
        if self.site.event_url:
            self.site.event_url = _with_month(self.site.event_url, month)
        return await super().scrape(target, session)
