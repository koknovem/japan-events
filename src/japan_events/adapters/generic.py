from __future__ import annotations

from datetime import date
from typing import Any

from japan_events.adapters.base import BaseAdapter
from japan_events.browser import BrowserSession, extract_page_events, find_event_links
from japan_events.models import Event
from japan_events.normalize import (
    dedupe_events,
    dict_to_event,
    extract_eventish_dicts,
    filter_events,
    parse_date_range,
    parse_jp_multi_days,
)
from japan_events.registry import register


def _raw_to_events(
    items: list[dict[str, Any]],
    *,
    prefecture: str,
    source: str,
    default_year: int,
    page_url: str,
) -> list[Event]:
    events: list[Event] = []
    for item in items:
        data = dict(item)
        if data.get("period") and not (data.get("start_date") or data.get("startDate")):
            start, end = parse_date_range(data["period"], default_year=default_year)
            if start:
                data["start_date"] = start.isoformat()
            if end:
                data["end_date"] = end.isoformat()
        if data.get("start_date") and not data.get("end_date") and data.get("period"):
            _, end = parse_date_range(str(data["period"]), default_year=default_year)
            if end:
                data["end_date"] = end.isoformat()

        period_text = str(data.get("period") or data.get("start_date") or "")
        multi = parse_jp_multi_days(period_text, default_year=default_year)
        if len(multi) > 1:
            for day in multi:
                day_data = dict(data)
                day_data["start_date"] = day.isoformat()
                day_data["end_date"] = day.isoformat()
                event = dict_to_event(
                    day_data, prefecture=prefecture, source=source, default_year=default_year
                )
                if not event:
                    continue
                if event.url and event.url.startswith("/"):
                    from urllib.parse import urljoin

                    event.url = urljoin(page_url, event.url)
                if event.image_url and event.image_url.startswith("//"):
                    event.image_url = "https:" + event.image_url
                events.append(event)
            continue

        event = dict_to_event(data, prefecture=prefecture, source=source, default_year=default_year)
        if not event:
            continue
        if event.url and event.url.startswith("/"):
            from urllib.parse import urljoin

            event.url = urljoin(page_url, event.url)
        if event.image_url and event.image_url.startswith("//"):
            event.image_url = "https:" + event.image_url
        events.append(event)
    return events


async def harvest_events(session: BrowserSession, target: date, source_label: str | None = None) -> tuple[list[Event], str]:
    """JSON XHR → JSON-LD → HTML cards. Returns (events, notes)."""
    site = session.site
    prefecture = site.name
    notes: list[str] = []
    collected: list[Event] = []
    page_url = session.page.url
    label = source_label or site.listing_url

    if site.api_url:
        try:
            payload = await session.fetch_json(site.api_url, target)
            items = extract_eventish_dicts(payload)
            collected.extend(
                _raw_to_events(
                    items,
                    prefecture=prefecture,
                    source=f"{label}#api",
                    default_year=target.year,
                    page_url=site.api_url,
                )
            )
            notes.append(f"api:{len(items)}")
        except Exception as exc:
            notes.append(f"api_error:{exc}")

    for rec in session.capture.records:
        items = extract_eventish_dicts(rec.get("body"))
        if not items:
            continue
        collected.extend(
            _raw_to_events(
                items,
                prefecture=prefecture,
                source=rec.get("url") or f"{label}#xhr",
                default_year=target.year,
                page_url=rec.get("url") or page_url,
            )
        )
        notes.append(f"xhr:{len(items)}")

    extracted = await extract_page_events(session.page)
    page_url = extracted.get("url") or page_url
    ld_items = extracted.get("json_ld") or []
    if ld_items:
        collected.extend(
            _raw_to_events(
                ld_items,
                prefecture=prefecture,
                source=f"{page_url}#json-ld",
                default_year=target.year,
                page_url=page_url,
            )
        )
        notes.append(f"jsonld:{len(ld_items)}")

    cards = extracted.get("cards") or []
    if cards:
        collected.extend(
            _raw_to_events(
                cards,
                prefecture=prefecture,
                source=f"{page_url}#html",
                default_year=target.year,
                page_url=page_url,
            )
        )
        notes.append(f"html:{len(cards)}")

    dated_links = extracted.get("dated_links") or []
    if dated_links:
        collected.extend(
            _raw_to_events(
                dated_links,
                prefecture=prefecture,
                source=f"{page_url}#links",
                default_year=target.year,
                page_url=page_url,
            )
        )
        notes.append(f"links:{len(dated_links)}")

    collected = dedupe_events(collected)
    matched = filter_events(collected, target)
    if collected and not matched:
        notes.append(f"none_on_date:{len(collected)}_parsed")
    if not collected:
        notes.append("no_event_listing")
    return matched, "; ".join(notes) if notes else "ok"


@register("generic")
class GenericAdapter(BaseAdapter):
    name = "generic"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        url = self.site.listing_url
        await session.goto(url)
        if not self.site.event_url:
            links = await find_event_links(session.page, limit=8)
            for link in links:
                href = link.get("href") or ""
                if href and href.rstrip("/") != url.rstrip("/"):
                    try:
                        await session.goto(href)
                        break
                    except Exception:
                        continue

        if self.site.date_picker:
            await session.click_calendar_date(target)

        events, notes = await harvest_events(session, target)
        session.page_notes = notes  # type: ignore[attr-defined]
        return events
