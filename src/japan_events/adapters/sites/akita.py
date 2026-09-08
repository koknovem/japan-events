"""Akita event search — fill official date inputs (GET q[] returns 500)."""
from __future__ import annotations

from datetime import date

from japan_events.adapters.configured import ConfigurableAdapter
from japan_events.browser import BrowserSession
from japan_events.models import Event
from japan_events.normalize import dedupe_events, filter_events
from japan_events.registry import register


@register("akita")
class AkitaAdapter(ConfigurableAdapter):
    """akita-fun.jp/events date inputs: end_date >= day AND start_date <= day."""

    name = "akita"

    async def scrape(self, target: date, session: BrowserSession) -> list[Event]:
        cfg = self.config
        url = cfg.event_url or self.site.event_url or "https://akita-fun.jp/events"
        notes: list[str] = []
        try:
            await session.goto(url)
        except Exception as exc:
            notes.append(f"goto_error:{exc}")
            session.page_notes = "; ".join(notes)  # type: ignore[attr-defined]
            return []
        if cfg.wait_ms:
            await session.page.wait_for_timeout(cfg.wait_ms)
        iso = target.isoformat()
        try:
            filled = await session.page.evaluate(
                """(iso) => {
                  const end = document.querySelector(
                    '#q_event_terms_end_date_gteq, [name="q[event_terms_end_date_gteq]"]'
                  );
                  const start = document.querySelector(
                    '#q_event_terms_start_date_lteq, [name="q[event_terms_start_date_lteq]"]'
                  );
                  let n = 0;
                  if (end) {
                    end.value = iso;
                    end.dispatchEvent(new Event('input', {bubbles: true}));
                    end.dispatchEvent(new Event('change', {bubbles: true}));
                    n += 1;
                  }
                  if (start) {
                    start.value = iso;
                    start.dispatchEvent(new Event('input', {bubbles: true}));
                    start.dispatchEvent(new Event('change', {bubbles: true}));
                    n += 1;
                  }
                  const form = document.querySelector('form.event_search, #event_search');
                  if (form) {
                    form.submit();
                    n += 10;
                  }
                  return n;
                }""",
                iso,
            )
            notes.append(f"date_inputs:{filled}")
            await session.page.wait_for_timeout(2500)
        except Exception as exc:
            notes.append(f"filter_error:{exc}")

        page_events = await self._harvest_page(session, target, url, cfg, notes)
        matched = filter_events(dedupe_events(page_events), target)
        session.page_notes = "; ".join(n for n in notes if n) or (cfg.notes or "akita")  # type: ignore[attr-defined]
        return matched
