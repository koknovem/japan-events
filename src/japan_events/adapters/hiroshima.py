from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.generic import harvest_events
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.normalize import dedupe_events, dict_to_event, filter_events
from japan_events.registry import register

API_BASE = "https://cms.dive-hiroshima.com/en/wp-json/api/v1/events-index/filter/data/"


@register("hiroshima")
class HiroshimaAdapter(BaseAdapter):
    """dive-hiroshima.com WordPress events-index JSON API."""

    name = "hiroshima"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        listing = self.site.event_url or "https://dive-hiroshima.com/en/events/"
        collected: list[Event] = []
        offset = 0
        notes: list[str] = []
        try:
            await session.goto(listing)
        except Exception as exc:
            notes.append(f"goto_error:{exc}")
        try:
            while offset < 200:
                query = urlencode(
                    {
                        "offset": offset,
                        "start_date": target.isoformat(),
                        "end_date": target.isoformat(),
                        "order": "date",
                        "site": "en",
                        "page_status": "production",
                    }
                )
                payload = await session.fetch_json(f"{API_BASE}?{query}")
                posts = ((payload or {}).get("list_data") or {}).get("posts") or []
                if not posts:
                    break
                for post in posts:
                    event_dates = post.get("event_date") or []
                    start = end = None
                    if event_dates and isinstance(event_dates, list):
                        first = event_dates[0] or {}
                        start = first.get("start_date")
                        end = first.get("end_date")
                    tags = post.get("tags") or []
                    category = None
                    if tags and isinstance(tags[0], dict):
                        category = tags[0].get("name")
                    image = post.get("image") or {}
                    raw = {
                        "title": post.get("title"),
                        "start_date": start,
                        "end_date": end,
                        "description": post.get("summary") or post.get("sub_title"),
                        "url": (post.get("url") or "").replace(
                            "https://cms.dive-hiroshima.com",
                            "https://dive-hiroshima.com",
                        ),
                        "image": image.get("url") if isinstance(image, dict) else None,
                        "category": category,
                    }
                    event = dict_to_event(
                        raw,
                        prefecture=self.site.name,
                        source=f"{API_BASE}#api",
                        default_year=target.year,
                    )
                    if event:
                        collected.append(event)
                notes.append(f"api_page:{len(posts)}")
                total = int(((payload.get("list_data") or {}).get("total") or 0))
                offset += len(posts)
                if offset >= total or not posts:
                    break
        except Exception as exc:
            notes.append(f"api_error:{exc}")
            await session.goto(listing)
            events, html_notes = await harvest_events(session, target, source_label=listing)
            session.page_notes = "; ".join(notes + [html_notes])  # type: ignore[attr-defined]
            return events

        matched = filter_events(dedupe_events(collected), target)
        session.page_notes = "; ".join(notes) if notes else "hiroshima-api"  # type: ignore[attr-defined]
        return matched
