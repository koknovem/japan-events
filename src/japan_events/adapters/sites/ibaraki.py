"""Ibaraki event search — dated GET on event.php (search_start_*/search_end_*)."""
from __future__ import annotations

from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from japan_events.adapters.configured import ConfigurableAdapter
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.normalize import dedupe_events, filter_events
from japan_events.registry import register


def _dated_event_php(url: str, target: date) -> str:
    if "event.php" not in url or "ibarakiguide.jp" not in url:
        return url
    parts = urlsplit(url)
    pairs = dict(parse_qsl(parts.query, keep_blank_values=True))
    pairs.update(
        {
            "search_start_year": str(target.year),
            "search_start_month": str(target.month),
            "search_start_day": str(target.day),
            "search_end_year": str(target.year),
            "search_end_month": str(target.month),
            "search_end_day": str(target.day),
        }
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), parts.fragment))


@register("ibaraki")
class IbarakiAdapter(ConfigurableAdapter):
    """ibarakiguide.jp/event.php GET date filters (Y/M/D selects)."""

    name = "ibaraki"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        cfg = self.config
        url = _dated_event_php(
            self.site.event_url or cfg.event_url or "https://www.ibarakiguide.jp/event.php",
            target,
        )
        notes: list[str] = [f"dated:{url}"]
        try:
            await session.goto(url)
        except Exception as exc:
            notes.append(f"goto_error:{exc}")
            session.page_notes = "; ".join(notes)  # type: ignore[attr-defined]
            return []
        if cfg.wait_for:
            try:
                await session.page.wait_for_selector(cfg.wait_for, timeout=8000)
            except Exception:
                pass
        if cfg.wait_ms:
            await session.page.wait_for_timeout(cfg.wait_ms)

        page_events = await self._harvest_page(session, target, url, cfg, notes)
        matched = filter_events(dedupe_events(page_events), target)
        session.page_notes = "; ".join(n for n in notes if n) or (cfg.notes or "ibaraki")  # type: ignore[attr-defined]
        return matched
