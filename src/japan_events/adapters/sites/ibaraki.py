"""Ibaraki event search — fill start/end date dropdowns then harvest."""
from __future__ import annotations

from datetime import date

from japan_events.adapters.base import BaseAdapter
from japan_events.adapters.configured import CARD_EXTRACT_JS
from japan_events.adapters.generic import _raw_to_events, harvest_events
from japan_events.adapters.loader import load_adapter_yaml
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.normalize import dedupe_events, filter_events
from japan_events.registry import register


@register("ibaraki")
class IbarakiAdapter(BaseAdapter):
    """ibarakiguide.jp/event.php with JP date select filters."""

    name = "ibaraki"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        cfg = load_adapter_yaml("ibaraki")
        url = (cfg.event_url if cfg else None) or self.site.event_url or "https://www.ibarakiguide.jp/event.php"
        await session.goto(url)
        notes: list[str] = []
        try:
            selects = session.page.locator("select")
            count = await selects.count()
            # Typical order: start Y/M/D, end Y/M/D among the date selects
            wanted = [
                str(target.year),
                str(target.month),
                str(target.day),
                str(target.year),
                str(target.month),
                str(target.day),
            ]
            wi = 0
            filled = 0
            for i in range(count):
                if wi >= len(wanted):
                    break
                sel = selects.nth(i)
                if not await sel.is_visible():
                    continue
                options = [o.strip() for o in await sel.locator("option").all_text_contents()]
                values = await sel.locator("option").evaluate_all(
                    "els => els.map(e => e.value)"
                )
                v = wanted[wi]
                if v in options or v in values or v.zfill(2) in options:
                    try:
                        await sel.select_option(value=v, timeout=2000)
                    except Exception:
                        try:
                            await sel.select_option(label=v, timeout=2000)
                        except Exception:
                            continue
                    filled += 1
                    wi += 1
            # Force-set hidden selects via JS (search form may be collapsed)
            if filled < 6:
                forced = await session.page.evaluate(
                    """(t) => {
                      const names = [
                        'search_start_year','search_start_month','search_start_day',
                        'search_end_year','search_end_month','search_end_day'
                      ];
                      const vals = [String(t.y), String(t.m), String(t.d), String(t.y), String(t.m), String(t.d)];
                      let n = 0;
                      names.forEach((name, i) => {
                        const el = document.querySelector(`select[name="${name}"]`);
                        if (!el) return;
                        el.value = vals[i];
                        el.dispatchEvent(new Event('change', {bubbles:true}));
                        n += 1;
                      });
                      return n;
                    }""",
                    {"y": target.year, "m": target.month, "d": target.day},
                )
                notes.append(f"js_date_force:{forced}")
            notes.append(f"date_selects:{filled}")
            for sel in ("button:has-text('検索')", "input[type='submit']", "button[type='submit']"):
                btn = session.page.locator(sel)
                if await btn.count():
                    await btn.first.click()
                    await session.page.wait_for_timeout(2500)
                    notes.append("search_clicked")
                    break
        except Exception as exc:
            notes.append(f"filter_error:{exc}")

        fields = {
            "title": (cfg.fields.title if cfg else ["a", "h2", "h3"]),
            "period": (cfg.fields.period if cfg else ["time", ".date"]),
            "venue": (cfg.fields.venue if cfg else []),
            "area": (cfg.fields.area if cfg else [".area"]),
            "category": (cfg.fields.category if cfg else []),
            "url": (cfg.fields.url if cfg else ["a"]),
            "image": (cfg.fields.image if cfg else ["img"]),
        }
        raw_cards = await session.page.evaluate(
            CARD_EXTRACT_JS,
            {
                "cardSelectors": [
                    ".eventList li",
                    ".resultList li",
                    "#event_list li",
                    "div.list",
                    "li",
                ],
                "fields": fields,
                "useCardTextAsPeriod": True,
            },
        )
        collected = _raw_to_events(
            raw_cards,
            prefecture=self.site.name,
            source=f"{url}#site-card",
            default_year=target.year,
            page_url=url,
        )
        notes.append(f"site_cards:{len(raw_cards)}")
        extra, hnotes = await harvest_events(session, target, source_label=url)
        notes.append(hnotes)
        matched = filter_events(dedupe_events(collected + extra), target)
        session.page_notes = "; ".join(notes)  # type: ignore[attr-defined]
        return matched
