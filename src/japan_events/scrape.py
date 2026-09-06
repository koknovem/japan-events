from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date
from typing import Any

from japan_events.browser import close_session, launch_browser, open_session, playwright_runtime
from japan_events.langs import resolve_lang_urls
from japan_events.models import Event, SiteConfig, SiteResult
from japan_events.normalize import dedupe_events
from japan_events.registry import filter_sites, get_adapter, load_sites
from japan_events.storage import write_combined, write_site_result

ProgressCallback = Callable[[str, dict[str, Any]], None]


def _emit(on_progress: ProgressCallback | None, event: str, **payload: Any) -> None:
    if on_progress is None:
        return
    try:
        on_progress(event, payload)
    except Exception as exc:
        print(f"[scrape] progress callback failed: {type(exc).__name__}: {exc}", flush=True)


async def scrape_site(site: SiteConfig, target: date, session) -> SiteResult:
    """Scrape each configured language URL and tag events with ``lang``."""
    adapter = get_adapter(site)
    config = getattr(adapter, "config", None)
    lang_urls = resolve_lang_urls(site, config)

    collected: list[Event] = []
    note_parts: list[str] = []
    last_url = site.listing_url

    orig_site_event = site.event_url
    orig_cfg_event = getattr(config, "event_url", None) if config is not None else None

    try:
        for lang, url in lang_urls.items():
            site.event_url = url
            if config is not None:
                config.event_url = url
            print(f"[scrape]   {site.id} lang={lang} -> {url}", flush=True)
            try:
                events = await adapter.scrape(target, session)
                for ev in events:
                    ev.lang = lang
                collected.extend(events)
                adapter_notes = getattr(session, "page_notes", None)
                note_parts.append(f"{lang}:{len(events)}" + (f"({adapter_notes})" if adapter_notes else ""))
                last_url = session.page.url if session.page else url
            except Exception as exc:
                note_parts.append(f"{lang}:ERR:{type(exc).__name__}")
                print(f"[scrape]   {site.id} lang={lang} failed: {exc}", flush=True)
    finally:
        site.event_url = orig_site_event
        if config is not None:
            config.event_url = orig_cfg_event

    events = dedupe_events(collected)
    notes = "; ".join(note_parts) if note_parts else "no matching events"
    return SiteResult(
        prefecture=site.name,
        id=site.id,
        ok=True,
        date=target.isoformat(),
        notes=notes,
        event_count=len(events),
        source_url=last_url,
        adapter=getattr(adapter, "name", site.adapter),
        events=events,
    )


async def run_scrape(
    target: date,
    *,
    prefecture: str | None = None,
    headed: bool = False,
    concurrency: int = 3,
    on_progress: ProgressCallback | None = None,
) -> list[SiteResult]:
    sites = filter_sites(load_sites(), prefecture)
    sem = asyncio.Semaphore(max(1, concurrency))
    _emit(
        on_progress,
        "init",
        sites=[{"id": site.id, "prefecture": site.name} for site in sites],
    )

    async with playwright_runtime() as playwright:
        browser = await launch_browser(playwright, headed=headed)

        async def one(site: SiteConfig) -> SiteResult:
            async with sem:
                print(f"[scrape] {site.id} via {site.adapter}: {site.listing_url}", flush=True)
                _emit(on_progress, "site_start", id=site.id, prefecture=site.name)
                session = None
                try:
                    session = await open_session(browser, site, headed=headed)
                    result = await scrape_site(site, target, session)
                except Exception as exc:
                    result = SiteResult(
                        prefecture=site.name,
                        id=site.id,
                        ok=False,
                        date=target.isoformat(),
                        error=f"{type(exc).__name__}: {exc}",
                        event_count=0,
                        source_url=site.listing_url,
                        adapter=site.adapter,
                        events=[],
                    )
                finally:
                    if session is not None:
                        await close_session(session)
                write_site_result(result, target)
                flag = "ok" if result.ok else "ERR"
                print(
                    f"[scrape] {site.id}: {flag} events={result.event_count}"
                    + (f" error={result.error}" if result.error else ""),
                    flush=True,
                )
                _emit(
                    on_progress,
                    "site_done",
                    id=result.id,
                    prefecture=result.prefecture,
                    ok=result.ok,
                    event_count=result.event_count,
                    error=result.error,
                )
                return result

        try:
            results = list(await asyncio.gather(*[one(site) for site in sites]))
            await browser.close()
        except Exception as exc:
            _emit(on_progress, "error", error=f"{type(exc).__name__}: {exc}")
            raise

    _emit(on_progress, "combining")
    write_combined(results, target)
    ok = sum(1 for r in results if r.ok)
    total_events = sum(r.event_count for r in results)
    print(
        f"[scrape] done date={target.isoformat()} sites={ok}/{len(results)} events={total_events}",
        flush=True,
    )
    _emit(on_progress, "done", ok_count=ok, event_count=total_events)
    return results
