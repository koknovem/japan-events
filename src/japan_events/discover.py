from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from japan_events.browser import (
    close_session,
    find_event_links,
    launch_browser,
    open_session,
    playwright_runtime,
    summarize_payload,
)
from japan_events.models import SiteConfig
from japan_events.normalize import extract_eventish_dicts
from japan_events.registry import filter_sites, load_sites, project_root


def discoveries_dir(root: Path | None = None) -> Path:
    path = (root or project_root()) / "discoveries"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def discover_site(site: SiteConfig, session) -> dict[str, Any]:
    report: dict[str, Any] = {
        "id": site.id,
        "name": site.name,
        "region": site.region,
        "home_url": site.home_url,
        "configured_event_url": site.event_url,
        "ok": True,
        "error": None,
        "cookie_hits": [],
        "event_links": [],
        "chosen_event_url": site.event_url,
        "json_endpoints": [],
        "likely_event_apis": [],
        "page_title": None,
        "final_url": None,
    }
    try:
        await session.goto(site.home_url)
        report["page_title"] = await session.page.title()
        report["final_url"] = session.page.url
        report["cookie_hits"] = list(session.cookie_hits)
        links = await find_event_links(session.page)
        report["event_links"] = links
        target_url = site.event_url
        if not target_url and links:
            target_url = links[0]["href"]
        if target_url and target_url.rstrip("/") != site.home_url.rstrip("/"):
            report["chosen_event_url"] = target_url
            session.capture.records.clear()
            await session.goto(target_url)
            extra = await find_event_links(session.page, limit=10)
            existing = {x["href"] for x in report["event_links"]}
            for item in extra:
                if item["href"] not in existing:
                    report["event_links"].append(item)
            report["final_url"] = session.page.url
            report["page_title"] = await session.page.title()

        for rec in session.capture.records:
            items = extract_eventish_dicts(rec.get("body"))
            entry = {
                "url": rec.get("url"),
                "status": rec.get("status"),
                "content_type": rec.get("content_type"),
                "event_item_count": len(items),
                "sample": summarize_payload(rec.get("body")),
            }
            report["json_endpoints"].append(entry)
            if items:
                report["likely_event_apis"].append(
                    {
                        "url": rec.get("url"),
                        "event_item_count": len(items),
                        "sample_keys": sorted({k for it in items[:3] for k in it.keys()}),
                    }
                )
        if not report["chosen_event_url"]:
            report["chosen_event_url"] = site.home_url
        if not report["event_links"] and not report["likely_event_apis"]:
            report["notes"] = "no event listing or JSON API detected from home page"
        elif report["likely_event_apis"]:
            report["notes"] = f"stable JSON candidates: {len(report['likely_event_apis'])}"
        else:
            report["notes"] = "HTML event links found; no JSON API captured"
    except Exception as exc:
        report["ok"] = False
        report["error"] = f"{type(exc).__name__}: {exc}"
    report["discovered_at"] = datetime.now(timezone.utc).isoformat()
    return report


async def run_discover(
    *,
    prefecture: str | None = None,
    headed: bool = False,
    concurrency: int = 3,
) -> list[dict[str, Any]]:
    sites = filter_sites(load_sites(), prefecture)
    out_dir = discoveries_dir()
    sem = asyncio.Semaphore(max(1, concurrency))
    results: list[dict[str, Any]] = []

    async with playwright_runtime() as playwright:
        browser = await launch_browser(playwright, headed=headed)

        async def one(site: SiteConfig) -> dict[str, Any]:
            async with sem:
                print(f"[discover] {site.id}: {site.home_url}", flush=True)
                session = await open_session(browser, site, headed=headed)
                try:
                    report = await discover_site(site, session)
                finally:
                    await close_session(session)
                path = out_dir / f"{site.id}.json"
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                status = "ok" if report.get("ok") else f"ERR {report.get('error')}"
                apis = len(report.get("likely_event_apis") or [])
                links = len(report.get("event_links") or [])
                print(
                    f"[discover] {site.id}: {status}  links={links} apis={apis} -> {path}",
                    flush=True,
                )
                return report

        results = await asyncio.gather(*[one(site) for site in sites])
        await browser.close()

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site_count": len(results),
        "ok_count": sum(1 for r in results if r.get("ok")),
        "with_api": sum(1 for r in results if r.get("likely_event_apis")),
        "sites": [
            {
                "id": r.get("id"),
                "ok": r.get("ok"),
                "chosen_event_url": r.get("chosen_event_url"),
                "api_count": len(r.get("likely_event_apis") or []),
                "event_link_count": len(r.get("event_links") or []),
                "notes": r.get("notes"),
                "error": r.get("error"),
            }
            for r in results
        ],
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[discover] wrote {summary_path}", flush=True)
    return list(results)
