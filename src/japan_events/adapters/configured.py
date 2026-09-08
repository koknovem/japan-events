from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from japan_events.adapter_config import SiteAdapterConfig
from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.generic import _raw_to_events, harvest_events
from japan_events.adapters.loader import load_adapter_yaml
from japan_events.browser import BrowserSession, find_event_links
from japan_events.models import Event, SiteConfig
from japan_events.normalize import dedupe_events, extract_eventish_dicts, filter_events
from japan_events.registry import register


CARD_EXTRACT_JS = r"""
(args) => {
  const { cardSelectors, fields, useCardTextAsPeriod } = args;
  const abs = (href) => {
    if (!href) return null;
    try { return new URL(href, location.href).href; } catch { return href; }
  };
  const text = (el) => (el && (el.innerText || el.textContent) || '').trim().replace(/\s+/g, ' ');
  const pick = (root, sels) => {
    for (const sel of (sels || [])) {
      try {
        const n = root.querySelector(sel);
        if (n) return n;
      } catch (e) {}
    }
    return null;
  };
  const DATE_RE = /(\d{4}\s*[年./-]\s*\d{1,2}\s*[月./-]?\s*\d{0,2}\s*日?|令和\s*\d{1,2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日?|\d{4}[-/]\d{1,2}[-/]\d{1,2}|[A-Z][a-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}|\d{1,2}\s+[A-Z][a-z]{2,9},?\s*\d{4}|\d{1,2}\s*月\s*\d{1,2}(?:\s*[・･/,、]\s*\d{1,2})*\s*日)/;
  const RANGE_RE = /((?:[A-Z][a-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}|\d{1,2}\s+[A-Z][a-z]{2,9}(?:,?\s*\d{4})?|\d{4}\s*[年./-]\s*\d{1,2}\s*[月./-]\s*\d{1,2}\s*日?|令和\s*\d{1,2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日?|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}[-/]\d{1,2})(?:\s*[（(][^）)]{0,12}[）)])?\s*[-–~〜～to]+\s*(?:[A-Z][a-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}|\d{1,2}\s+[A-Z][a-z]{2,9}(?:,?\s*\d{4})?|\d{4}\s*[年./-]\s*\d{1,2}\s*[月./-]\s*\d{1,2}\s*日?|令和\s*\d{1,2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日?|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}[-/]\d{1,2}(?:\s*\d{4})?)(?:\s*[（(][^）)]{0,12}[）)])?)/i;

  const cards = [];
  const seen = new Set();
  for (const sel of (cardSelectors || [])) {
    let nodes = [];
    try { nodes = [...document.querySelectorAll(sel)]; } catch (e) { continue; }
    for (const el of nodes) {
      if (seen.has(el) || cards.length > 150) continue;
      seen.add(el);
      const titleEl = pick(el, fields.title);
      let title = text(titleEl);
      const blob = text(el).slice(0, 700);
      if (!title || title.length < 2) {
        title = blob.slice(0, 160);
      }
      if (!title || title.length < 3 || title.length > 220) continue;
      const periodEl = pick(el, fields.period);
      const periodText = text(periodEl) || (useCardTextAsPeriod ? blob : '');
      const rangeHit = periodText.match(RANGE_RE) || blob.match(RANGE_RE);
      const dateHit = periodText.match(DATE_RE) || blob.match(DATE_RE);
      const timeEl = el.querySelector('time');
      const hrefEl = pick(el, fields.url);
      const imgEl = pick(el, fields.image);
      const venueEl = pick(el, fields.venue);
      const areaEl = pick(el, fields.area);
      const catEl = pick(el, fields.category);
      cards.push({
        title,
        period: (rangeHit && rangeHit[0]) || (dateHit && dateHit[0]) || (periodText.slice(0, 120) || null),
        start_date: (timeEl && (timeEl.getAttribute('datetime') || text(timeEl))) || (rangeHit && rangeHit[0]) || (dateHit && dateHit[0]) || null,
        venue: text(venueEl) || null,
        area: text(areaEl) || null,
        category: text(catEl) || null,
        description: blob.slice(0, 400),
        url: hrefEl ? abs(hrefEl.getAttribute('href')) : null,
        image: imgEl ? abs(imgEl.getAttribute('src') || imgEl.getAttribute('data-src')) : null,
        source: 'site-card',
      });
    }
  }
  return cards;
}
"""


def _apply_api_date(url: str, target: date, keys: dict[str, str]) -> str:
    iso = target.isoformat()
    compact = target.strftime("%Y%m%d")
    dated = (
        url.replace("{date}", iso)
        .replace("{start}", iso)
        .replace("{end}", iso)
        .replace("{ymd}", compact)
    )
    if not keys:
        return dated
    parts = urlsplit(dated)
    pairs = dict(parse_qsl(parts.query, keep_blank_values=True))
    for logical, param in keys.items():
        if logical in {"date", "start", "start_date", "from"}:
            pairs[param] = iso
        elif logical in {"end", "end_date", "to"}:
            pairs[param] = iso
        else:
            pairs[param] = iso
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), parts.fragment))


@register("configured")
class ConfigurableAdapter(BaseAdapter):
    """YAML-driven adapter: site-specific URLs, selectors, and optional API."""

    name = "configured"

    def __init__(self, site: SiteConfig, config: SiteAdapterConfig | None = None) -> None:
        super().__init__(site)
        self.config = config or load_adapter_yaml(site.id) or SiteAdapterConfig(id=site.id)
        self.name = site.id

    def _listing_urls(self) -> list[str]:
        urls: list[str] = []
        primary = self.config.event_url or self.site.event_url
        if primary:
            urls.append(primary)
        # Extra listing_urls are often a single language; skip them during multi-lang scrapes.
        if not self.config.urls_by_lang:
            for u in [*self.config.listing_urls, self.site.home_url]:
                if u and u not in urls:
                    urls.append(u)
        return urls

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        cfg = self.config
        notes: list[str] = []
        collected: list[Event] = []
        urls = self._listing_urls()

        if cfg.api_url or self.site.api_url:
            api = cfg.api_url or self.site.api_url
            assert api
            api = _apply_api_date(api, target, cfg.api_date_keys)
            try:
                payload = await session.fetch_json(api, target)
                items = extract_eventish_dicts(payload)
                collected.extend(
                    _raw_to_events(
                        items,
                        prefecture=self.site.name,
                        source=f"{api}#api",
                        default_year=target.year,
                        page_url=api,
                    )
                )
                notes.append(f"api:{len(items)}")
            except Exception as exc:
                notes.append(f"api_error:{exc}")

        dated_urls = [_apply_api_date(url, target, cfg.api_date_keys) for url in urls[:4]]
        for url in dated_urls:
            try:
                await session.goto(url)
            except Exception as exc:
                notes.append(f"goto_error:{exc}")
                continue
            if cfg.wait_for:
                try:
                    await session.page.wait_for_selector(cfg.wait_for, timeout=8000)
                except Exception:
                    pass
            if cfg.wait_ms:
                await session.page.wait_for_timeout(cfg.wait_ms)
            if cfg.date_picker or self.site.date_picker:
                await session.click_calendar_date(target)

            page_events = await self._harvest_page(session, target, url, cfg, notes)
            collected.extend(page_events)

            # If this page yielded date matches, stop early
            if filter_events(dedupe_events(page_events), target):
                break

        matched = filter_events(dedupe_events(collected), target)

        # Follow event-ish links from the first reachable page when still empty
        if not matched and dated_urls:
            try:
                await session.goto(dated_urls[0])
                links = await find_event_links(session.page, limit=6)
                for link in links:
                    href = link.get("href") or ""
                    if not href or href.rstrip("/") == dated_urls[0].rstrip("/"):
                        continue
                    try:
                        await session.goto(href)
                    except Exception:
                        continue
                    if cfg.wait_ms:
                        await session.page.wait_for_timeout(min(cfg.wait_ms, 1500))
                    page_events = await self._harvest_page(session, target, href, cfg, notes)
                    collected.extend(page_events)
                    matched = filter_events(dedupe_events(collected), target)
                    if matched:
                        notes.append(f"followed:{href}")
                        break
            except Exception as exc:
                notes.append(f"follow_error:{exc}")

        matched = filter_events(dedupe_events(collected), target)
        if collected and not matched:
            notes.append(f"none_on_date:{len(dedupe_events(collected))}_parsed")
        session.page_notes = "; ".join(n for n in notes if n) or (cfg.notes or "configured")  # type: ignore[attr-defined]
        return matched

    async def _harvest_page(
        self,
        session: BrowserSession,
        target: date,
        url: str,
        cfg: SiteAdapterConfig,
        notes: list[str],
    ) -> list[Event]:
        page_events: list[Event] = []
        if cfg.card_selectors:
            fields = {
                "title": cfg.fields.title,
                "period": cfg.fields.period,
                "venue": cfg.fields.venue,
                "area": cfg.fields.area,
                "category": cfg.fields.category,
                "url": cfg.fields.url,
                "image": cfg.fields.image,
            }
            raw_cards: list[dict[str, Any]] = await session.page.evaluate(
                CARD_EXTRACT_JS,
                {
                    "cardSelectors": cfg.card_selectors,
                    "fields": fields,
                    "useCardTextAsPeriod": cfg.use_card_text_as_period,
                },
            )
            page_events.extend(
                _raw_to_events(
                    raw_cards,
                    prefecture=self.site.name,
                    source=f"{url}#site-card",
                    default_year=target.year,
                    page_url=url,
                )
            )
            notes.append(f"site_cards:{len(raw_cards)}")

        if cfg.harvest_fallback or cfg.strategy in {"harvest", "calendar"} or not cfg.card_selectors:
            events, harvest_notes = await harvest_events(session, target, source_label=url)
            notes.append(harvest_notes)
            page_events.extend(events)
        return page_events
