from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from japan_events.api.jobs import scrape_service
from japan_events.api.schemas import (
    DatesResponse,
    EventOut,
    EventsResponse,
    HealthResponse,
    ScrapeStatusOut,
    SiteOut,
    SiteStatusOut,
)
from japan_events.langs import SCRAPE_LANGS, map_ui_lang_to_scrape
from japan_events.normalize import event_overlaps
from japan_events.registry import load_sites
from japan_events.storage import list_cached_dates, load_combined


def _filter_events_by_lang(events: list[EventOut], lang: str | None) -> tuple[list[EventOut], str | None]:
    """Prefer requested lang; fall back ja → en → any if empty."""
    if not lang:
        return events, None
    wanted = map_ui_lang_to_scrape(lang)
    matched = [e for e in events if (e.lang or "ja") == wanted]
    if matched:
        return matched, wanted
    for fallback in ("ja", "en", "zh-TW", "zh-CN"):
        if fallback == wanted:
            continue
        matched = [e for e in events if (e.lang or "ja") == fallback]
        if matched:
            return matched, fallback
    return events, wanted


def _build_events_response(
    combined,
    *,
    prefecture: str | None,
    scraped: bool,
    lang: str | None,
    target: date | None = None,
    refreshing: bool = False,
    scraping: bool = False,
) -> EventsResponse:
    site_filter = None
    if prefecture:
        site_filter = {p.strip().lower() for p in prefecture.split(",") if p.strip()}
    wanted = target or date.fromisoformat(combined.date)

    events: list[EventOut] = []
    sites_out: list[SiteStatusOut] = []
    for site in combined.sites:
        if site_filter and site.id.lower() not in site_filter and site.prefecture.lower() not in site_filter:
            continue
        on_date = [ev for ev in site.events if event_overlaps(ev, wanted)]
        sites_out.append(
            SiteStatusOut(
                id=site.id,
                prefecture=site.prefecture,
                ok=site.ok,
                event_count=len(on_date),
                error=site.error,
                notes=site.notes,
                source_url=site.source_url,
                adapter=site.adapter,
            )
        )
        for ev in on_date:
            payload = ev.model_dump()
            payload.setdefault("lang", "ja")
            events.append(EventOut(**payload, site_id=site.id))

    events, used_lang = _filter_events_by_lang(events, lang)
    msg = "Fresh scrape completed." if scraped else None
    if lang and used_lang and map_ui_lang_to_scrape(lang) != used_lang:
        msg = (msg + " " if msg else "") + f"Showing {used_lang} (requested language had no events)."

    return EventsResponse(
        date=combined.date,
        cached=not scraped and not scraping,
        scraped=scraped,
        generated_at=combined.generated_at,
        site_count=len(sites_out) if site_filter else combined.site_count,
        ok_count=sum(1 for s in sites_out if s.ok),
        event_count=len(events),
        events=events,
        sites=sites_out,
        message=msg,
        refreshing=refreshing,
        scraping=scraping,
    )


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        scrape_service.resume_incomplete()
        yield

    app = FastAPI(
        title="Japan Events API",
        description="Prefecture tourism event calendars scraped via Playwright adapters.",
        version="0.4.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version="0.4.0")

    @app.get("/api/sites", response_model=list[SiteOut])
    def list_sites() -> list[SiteOut]:
        return [
            SiteOut(
                id=s.id,
                name=s.name,
                region=s.region,
                home_url=s.home_url,
                event_url=s.event_url,
                source_org=s.source_org,
                adapter=s.adapter,
            )
            for s in load_sites()
        ]

    @app.get("/api/dates", response_model=DatesResponse)
    def cached_dates() -> DatesResponse:
        return DatesResponse(dates=list_cached_dates())

    @app.get("/api/langs")
    def list_langs() -> dict:
        return {"langs": list(SCRAPE_LANGS)}

    @app.get("/api/events", response_model=EventsResponse)
    def get_events(
        date_str: str = Query(..., alias="date", description="YYYY-MM-DD"),
        prefecture: str | None = Query(None, description="Comma-separated site ids"),
        lang: str | None = Query(
            None,
            description="UI/scrape language: en | ja | zh-TW | zh-CN (falls back if empty)",
        ),
        force: bool = Query(False, description="Force a fresh scrape even if cached"),
    ) -> EventsResponse:
        """Return cached events immediately. If missing, start a server scrape and return scraping=true."""
        try:
            target = date.fromisoformat(date_str)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD") from exc

        try:
            combined, busy = scrape_service.get_or_start(
                target,
                force=force,
                prefecture=prefecture,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Scrape failed: {type(exc).__name__}: {exc}",
            ) from exc

        if busy:
            if combined is None:
                return EventsResponse(
                    date=date_str,
                    cached=False,
                    scraped=False,
                    scraping=True,
                    message="Scrape running in a server worker.",
                )
            had_complete = load_combined(target) is not None
            return _build_events_response(
                combined,
                prefecture=prefecture,
                scraped=False,
                lang=lang,
                target=target,
                scraping=not had_complete,
                refreshing=had_complete,
            )

        refreshing = False
        if not force and not prefecture:
            refreshing = scrape_service.maybe_refresh(target)

        if combined is None:
            raise HTTPException(status_code=502, detail="Scrape finished but no output was written")

        return _build_events_response(
            combined,
            prefecture=prefecture,
            scraped=False,
            lang=lang,
            target=target,
            refreshing=refreshing,
        )

    @app.get("/api/scrape/status", response_model=ScrapeStatusOut)
    def scrape_status(
        date_str: str | None = Query(None, alias="date", description="YYYY-MM-DD"),
    ) -> dict:
        return scrape_service.status(date_str)

    return app


app = create_app()
