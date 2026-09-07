from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import APIRequestContext, Browser, BrowserContext, Page, Playwright, async_playwright

from japan_events.models import SiteConfig
from japan_events.normalize import rewrite_date_query

DEFAULT_COOKIE_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "#onetrust-accept-btn-handler-handler",
    "button#onetrust-accept-btn-handler",
    ".onetrust-accept-btn-handler",
    "button:has-text('Accept All')",
    "button:has-text('Accept all')",
    "button:has-text('Accept Cookies')",
    "button:has-text('Accept cookies')",
    "button:has-text('I Agree')",
    "button:has-text('I agree')",
    "button:has-text('Agree')",
    "button:has-text('AGREE')",
    "button:has-text('Accept')",
    "button:has-text('Got it')",
    "button:has-text('OK')",
    "button:has-text('同意する')",
    "button:has-text('同意')",
    "button:has-text('許可')",
    "button:has-text('すべて同意')",
    "a:has-text('Accept All')",
    "a:has-text('Accept')",
    "[aria-label*='Accept']",
    "[data-testid*='accept']",
    ".cookie-accept",
    ".js-cookie-accept",
]

NAV_TIMEOUT_MS = 60_000
POLITE_DELAY_S = 1.0


def _jsonish_content_type(value: str) -> bool:
    ct = value.lower()
    return "json" in ct or "javascript" in ct and "json" in ct


def summarize_payload(obj: Any, *, max_list: int = 4, max_str: int = 180, depth: int = 0) -> Any:
    if depth > 5:
        return "..."
    if isinstance(obj, str):
        return obj if len(obj) <= max_str else obj[: max_str - 3] + "..."
    if isinstance(obj, list):
        preview = [summarize_payload(x, max_list=max_list, max_str=max_str, depth=depth + 1) for x in obj[:max_list]]
        if len(obj) > max_list:
            preview.append(f"... +{len(obj) - max_list} more")
        return preview
    if isinstance(obj, dict):
        return {
            str(k): summarize_payload(v, max_list=max_list, max_str=max_str, depth=depth + 1)
            for k, v in list(obj.items())[:40]
        }
    return obj


class JsonCapture:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def attach(self, page: Page) -> None:
        page.on("response", lambda response: asyncio.create_task(self._on_response(response)))

    async def _on_response(self, response: Any) -> None:
        try:
            url = response.url
            status = response.status
            headers = {k.lower(): v for k, v in response.headers.items()}
            ct = headers.get("content-type", "")
            if status >= 400:
                return
            if not (_jsonish_content_type(ct) or _looks_like_api(url)):
                return
            body: Any
            try:
                body = await response.json()
            except Exception:
                text = await response.text()
                text = text.strip()
                if not text or text[0] not in "[{":
                    return
                try:
                    body = json.loads(text)
                except json.JSONDecodeError:
                    return
            self.records.append(
                {
                    "url": url,
                    "status": status,
                    "content_type": ct,
                    "body": body,
                }
            )
        except Exception:
            return

    def eventish(self) -> list[dict[str, Any]]:
        from japan_events.normalize import extract_eventish_dicts

        out = []
        for rec in self.records:
            items = extract_eventish_dicts(rec["body"])
            if items:
                out.append({**rec, "event_items": items})
        return out


def _looks_like_api(url: str) -> bool:
    u = url.lower()
    return any(
        token in u
        for token in (
            ".json",
            "/api/",
            "/ajax",
            "graphql",
            "/wp-json/",
            "action=event",
            "event_search",
            "getevent",
        )
    )


@dataclass
class BrowserSession:
    page: Page
    context: BrowserContext
    request: APIRequestContext
    capture: JsonCapture
    site: SiteConfig
    headed: bool = False
    cookie_hits: list[str] = field(default_factory=list)

    async def goto(self, url: str, *, wait: str = "domcontentloaded") -> None:
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                await self.page.goto(url, wait_until=wait, timeout=NAV_TIMEOUT_MS)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                await self.page.wait_for_timeout(1200)
        if last_exc:
            raise last_exc
        title = ""
        try:
            title = await self.page.title()
        except Exception:
            title = ""
        if "request could not be satisfied" in title.lower() or "access denied" in title.lower():
            await self.page.wait_for_timeout(1500)
            await self.page.reload(wait_until=wait, timeout=NAV_TIMEOUT_MS)
        await accept_cookies(self.page, extra=self.site.cookie_selectors, hits=self.cookie_hits)
        await self.page.wait_for_timeout(700)
        try:
            await self.page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass

    async def fetch_json(self, url: str, target: date | None = None) -> Any:
        final = rewrite_date_query(url, target) if target else url
        response = await self.request.get(final, timeout=NAV_TIMEOUT_MS)
        try:
            return await response.json()
        except Exception:
            return json.loads(await response.text())

    async def click_calendar_date(self, target: date) -> bool:
        return await click_calendar_date(self.page, target)


async def accept_cookies(page: Page, extra: list[str] | None = None, hits: list[str] | None = None) -> None:
    selectors = list(extra or []) + DEFAULT_COOKIE_SELECTORS
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            if await locator.is_visible(timeout=400):
                await locator.click(timeout=1500)
                if hits is not None:
                    hits.append(selector)
                await page.wait_for_timeout(300)
                return
        except Exception:
            continue


async def click_calendar_date(page: Page, target: date) -> bool:
    iso = target.isoformat()
    compact = target.strftime("%Y%m%d")
    candidates = [
        f'[data-date="{iso}"]',
        f'[data-date="{compact}"]',
        f'[data-ymd="{iso}"]',
        f'[data-ymd="{compact}"]',
        f'[datetime="{iso}"]',
        f'a[href*="{iso}"]',
        f'a[href*="date={iso}"]',
        f'button[data-date="{iso}"]',
        f'td[data-date="{iso}"]',
        f'[aria-label*="{iso}"]',
        f'[aria-label*="{target.strftime("%B")}"][aria-label*="{target.day}"]',
    ]
    for selector in candidates:
        try:
            loc = page.locator(selector).first
            if await loc.count() and await loc.is_visible(timeout=300):
                await loc.click(timeout=2000)
                await page.wait_for_timeout(800)
                return True
        except Exception:
            continue

    # Generic calendar cell: visible day number in a table/grid that looks like a month view.
    try:
        clicked = await page.evaluate(
            """(day) => {
                const nodes = Array.from(document.querySelectorAll(
                    'td, button, a, span, div[role="gridcell"]'
                ));
                const hit = nodes.find((el) => {
                    const t = (el.textContent || '').trim();
                    if (t !== String(day) && t !== String(day).padStart(2, '0')) return false;
                    const cls = (el.className || '').toString().toLowerCase();
                    const parent = (el.parentElement && el.parentElement.className || '').toString().toLowerCase();
                    return /cal|day|date/.test(cls + parent) || el.getAttribute('data-day') === String(day);
                });
                if (!hit) return false;
                hit.click();
                return true;
            }""",
            target.day,
        )
        if clicked:
            await page.wait_for_timeout(800)
            return True
    except Exception:
        pass
    return False


def _junk_link(href: str) -> bool:
    low = href.lower()
    return any(
        token in low
        for token in (
            "facebook.com",
            "twitter.com",
            "x.com/share",
            "mailto:",
            "line.me",
            "instagram.com",
            "javascript:",
            "#tmp_",
        )
    )


EVENT_LINK_RE = re.compile(
    r"/(en/)?(events?|event-calendar|calendar|festival|festivals|whatson|whats-on)(/|$|\?)",
    re.I,
)


async def find_event_links(page: Page, limit: int = 20) -> list[dict[str, str]]:
    raw = await page.evaluate(
        """() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            return links.map((a) => ({
                text: (a.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 120),
                href: a.href,
            }));
        }"""
    )
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for item in raw:
        href = (item.get("href") or "").strip()
        if not href or href in seen or href.startswith("javascript:"):
            continue
        if _junk_link(href):
            continue
        if EVENT_LINK_RE.search(href) or EVENT_LINK_RE.search(item.get("text") or ""):
            seen.add(href)
            out.append({"text": item.get("text") or "", "href": href})
        if len(out) >= limit:
            break
    if not out:
        for item in raw:
            href = (item.get("href") or "").lower()
            text = (item.get("text") or "").lower()
            if _junk_link(item.get("href") or ""):
                continue
            if any(tok in href or tok in text for tok in ("event", "calendar", "festival", "イベント")):
                full = item.get("href") or ""
                if full in seen:
                    continue
                seen.add(full)
                out.append({"text": item.get("text") or "", "href": full})
            if len(out) >= limit:
                break
    return out


PAGE_EXTRACT_JS = r"""
() => {
  const abs = (href) => {
    if (!href) return null;
    try { return new URL(href, location.href).href; } catch { return href; }
  };
  const text = (el) => (el && (el.innerText || el.textContent) || '').trim().replace(/\s+/g, ' ');
  const DATE_RE = /(\d{4}\s*[年./-]\s*\d{1,2}\s*[月./-]?\s*\d{0,2}\s*日?|令和\s*\d{1,2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日?|\d{4}[-/]\d{1,2}[-/]\d{1,2}|[A-Z][a-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}|\d{1,2}\s+[A-Z][a-z]{2,9},?\s*\d{4}|\d{1,2}\s*月\s*\d{1,2}(?:\s*[・･/,、]\s*\d{1,2})*\s*日)/;
  const RANGE_RE = /((?:[A-Z][a-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}|\d{1,2}\s+[A-Z][a-z]{2,9}(?:,?\s*\d{4})?|\d{4}\s*[年./-]\s*\d{1,2}\s*[月./-]\s*\d{1,2}\s*日?|令和\s*\d{1,2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日?|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}[-/]\d{1,2})(?:\s*[（(][^）)]{0,12}[）)])?\s*[-–~〜～to]+\s*(?:[A-Z][a-z]{2,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{0,4}|\d{1,2}\s+[A-Z][a-z]{2,9}(?:,?\s*\d{4})?|\d{4}\s*[年./-]\s*\d{1,2}\s*[月./-]\s*\d{1,2}\s*日?|令和\s*\d{1,2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日?|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}[-/]\d{1,2}(?:\s*\d{4})?)(?:\s*[（(][^）)]{0,12}[）)])?)/i;

  const ldEvents = [];
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const data = JSON.parse(s.textContent || 'null');
      const walk = (o) => {
        if (!o || typeof o !== 'object') return;
        if (Array.isArray(o)) { o.forEach(walk); return; }
        const t = o['@type'];
        const types = (Array.isArray(t) ? t : [t]).map((x) => String(x || '').toLowerCase());
        if (types.includes('event')) {
          const loc = o.location;
          ldEvents.push({
            title: o.name || null,
            start_date: o.startDate || null,
            end_date: o.endDate || null,
            venue: (loc && (loc.name || loc.address)) || (typeof loc === 'string' ? loc : null),
            description: o.description || null,
            url: o.url || null,
            image: typeof o.image === 'string' ? o.image : (o.image && o.image.url) || null,
            source: 'json-ld',
          });
        }
        if (o['@graph']) walk(o['@graph']);
      };
      walk(data);
    } catch (e) {}
  }

  const pick = (root, sels) => {
    for (const sel of sels) {
      const n = root.querySelector(sel);
      if (n) return n;
    }
    return null;
  };

  const cards = [];
  const cardSels = [
    '[itemtype*="Event"]',
    'article.event', 'article[class*="event"]',
    '.event-item', '.event-card', '.eventCard', '.event_item', '.eventItem',
    '.c-event', '.p-event', '.m-event',
    'li.event', 'li[class*="event"]',
    '[class*="event-list"] > *', '[class*="eventList"] > *',
    '[class*="EventList"] > *', '[class*="event_list"] > *',
    '.post-event', '.card-event',
  ];
  const seen = new Set();
  for (const sel of cardSels) {
    for (const el of document.querySelectorAll(sel)) {
      if (seen.has(el) || cards.length > 80) continue;
      seen.add(el);
      const titleEl = pick(el, ['h1','h2','h3','h4','.title','.event-title','[class*="title"]','a']);
      const title = text(titleEl);
      if (!title || title.length < 2 || title.length > 220) continue;
      const blob = text(el).slice(0, 600);
      const rangeHit = blob.match(RANGE_RE);
      const dateHit = blob.match(DATE_RE);
      const timeEl = el.querySelector('time');
      const hrefEl = pick(el, ['a[href]']);
      const img = el.querySelector('img');
      cards.push({
        title,
        start_date: (timeEl && (timeEl.getAttribute('datetime') || text(timeEl))) || (rangeHit && rangeHit[0]) || (dateHit && dateHit[0]) || null,
        end_date: timeEl && timeEl.getAttribute('datetime') ? null : null,
        period: (rangeHit && rangeHit[0]) || (dateHit && dateHit[0]) || (blob.match(/\d{4}[./-]\d{1,2}[./-]\d{1,2}\s*[-~～〜–]\s*\d{1,2}[./-]\d{1,2}/) || [null])[0],
        venue: text(pick(el, ['.venue','.place','.location','[class*="venue"]','[class*="place"]'])),
        area: text(pick(el, ['.area','[class*="area"]'])),
        category: text(pick(el, ['.category','.cat','[class*="category"]'])),
        description: blob.slice(0, 400),
        url: hrefEl ? abs(hrefEl.getAttribute('href')) : null,
        image: img ? abs(img.getAttribute('src') || img.getAttribute('data-src')) : null,
        source: 'html-card',
      });
    }
  }

  for (const a of document.querySelectorAll('a[href*="detail_"], a[href*="/event/"], a[href*="/events/"]')) {
    const href = a.href || '';
    if (!/detail_\d+|\/event\/|\/events\//i.test(href)) continue;
    if (/\/events?\/?(index\.html)?$/i.test(href.replace(/\/$/, ''))) continue;
    let block = a.parentElement;
    for (let i = 0; i < 6 && block; i++) {
      const tlen = text(block).length;
      if (tlen > 30 && tlen < 480) break;
      if (!block.parentElement) break;
      const parentLen = text(block.parentElement).length;
      if (parentLen > 800 && tlen >= 20) break;
      block = block.parentElement;
    }
    if (!block || seen.has(block) || cards.length > 120) continue;
    const blob = text(block).slice(0, 700);
    if (blob.length < 8) continue;
    seen.add(block);
    const titleEl = pick(block, ['h1','h2','h3','h4','.title','[class*="title"]','img[alt]']);
    let title = text(titleEl);
    if (!title) {
      const img = block.querySelector('img[alt]');
      title = img ? (img.getAttribute('alt') || '') : '';
    }
    if (!title || title.length < 2) {
      const cleaned = blob.replace(RANGE_RE, ' ').replace(DATE_RE, ' ').replace(/more|detail_\d+\.html/ig, ' ').replace(/\s+/g, ' ').trim();
      title = cleaned.slice(0, 160);
    }
    if (!title || title.length < 3) continue;
    const rangeHit = blob.match(RANGE_RE);
    const dateHit = blob.match(DATE_RE);
    cards.push({
      title: title.slice(0, 220),
      period: (rangeHit && rangeHit[0]) || (dateHit && dateHit[0]) || null,
      start_date: (rangeHit && rangeHit[0]) || (dateHit && dateHit[0]) || null,
      description: blob.slice(0, 400),
      url: abs(href),
      image: (block.querySelector('img') && abs(block.querySelector('img').getAttribute('src') || block.querySelector('img').getAttribute('data-src'))) || null,
      source: 'detail-block',
    });
  }

  const datedLinks = [];
  const seenHref = new Set();
  for (const a of document.querySelectorAll('a[href]')) {
    const t = text(a);
    const href = a.href || '';
    if (!t || t.length < 8 || t.length > 260 || seenHref.has(href)) continue;
    if (/facebook|twitter|x\.com\/share|mailto:|instagram|line\.me|#tmp_/i.test(href)) continue;
    const rangeHit = t.match(RANGE_RE);
    const dateHit = t.match(DATE_RE);
    if (!rangeHit && !dateHit) continue;
    if (!/event|festival|calendar|detail_|matsuri|イベント/i.test(href + ' ' + t) && !rangeHit) continue;
    seenHref.add(href);
    const period = (rangeHit && rangeHit[0]) || (dateHit && dateHit[0]);
    const titleFromText = t.replace(RANGE_RE, ' ').replace(DATE_RE, ' ').replace(/\s+/g, ' ').trim();
    datedLinks.push({
      title: titleFromText || t,
      period,
      start_date: period,
      url: abs(href),
      source: 'dated-link',
    });
  }

  return { json_ld: ldEvents, cards, dated_links: datedLinks, url: location.href, title: document.title };
}
"""


async def extract_page_events(page: Page) -> dict[str, Any]:
    return await page.evaluate(PAGE_EXTRACT_JS)


def resolve_url(base: str, maybe: str | None) -> str | None:
    if not maybe:
        return None
    return urljoin(base, maybe)


def _chromium_launch_args() -> list[str]:
    args = ["--disable-blink-features=AutomationControlled"]
    docker = os.environ.get("JAPAN_EVENTS_DOCKER", "").strip().lower() in {"1", "true", "yes"}
    if docker or os.path.exists("/.dockerenv"):
        args.extend(["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    return args


async def launch_browser(playwright: Playwright, headed: bool = False) -> Browser:
    return await playwright.chromium.launch(
        headless=not headed,
        args=_chromium_launch_args(),
    )


async def new_site_context(browser: Browser, site: SiteConfig) -> BrowserContext:
    return await browser.new_context(
        locale="en-US",
        viewport={"width": 1365, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9,ja;q=0.8"},
    )


async def open_session(browser: Browser, site: SiteConfig, headed: bool = False) -> BrowserSession:
    context = await new_site_context(browser, site)
    page = await context.new_page()
    capture = JsonCapture()
    capture.attach(page)
    return BrowserSession(
        page=page,
        context=context,
        request=context.request,
        capture=capture,
        site=site,
        headed=headed,
    )


async def close_session(session: BrowserSession) -> None:
    try:
        await session.context.close()
    except Exception:
        pass
    await asyncio.sleep(POLITE_DELAY_S)


def playwright_runtime():
    return async_playwright()
