from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from japan_events.api.jobs import scrape_service
from japan_events.api.schemas import (
    DatesResponse,
    EventOut,
    EventsResponse,
    HealthResponse,
    SiteOut,
    SiteStatusOut,
)
from japan_events.registry import load_sites
from japan_events.storage import list_cached_dates


def _build_events_response(
    combined,
    *,
    prefecture: str | None,
    scraped: bool,
) -> EventsResponse:
    site_filter = None
    if prefecture:
        site_filter = {p.strip().lower() for p in prefecture.split(",") if p.strip()}

    events: list[EventOut] = []
    sites_out: list[SiteStatusOut] = []
    for site in combined.sites:
        if site_filter and site.id.lower() not in site_filter and site.prefecture.lower() not in site_filter:
            continue
        sites_out.append(
            SiteStatusOut(
                id=site.id,
                prefecture=site.prefecture,
                ok=site.ok,
                event_count=site.event_count,
                error=site.error,
                notes=site.notes,
                source_url=site.source_url,
                adapter=site.adapter,
            )
        )
        for ev in site.events:
            events.append(EventOut(**ev.model_dump(), site_id=site.id))

    return EventsResponse(
        date=combined.date,
        cached=not scraped,
        scraped=scraped,
        generated_at=combined.generated_at,
        site_count=len(sites_out) if site_filter else combined.site_count,
        ok_count=sum(1 for s in sites_out if s.ok),
        event_count=len(events),
        events=events,
        sites=sites_out,
        message="Fresh scrape completed." if scraped else None,
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Japan Events API",
        description="Prefecture tourism event calendars scraped via Playwright adapters.",
        version="0.3.0",
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
        return HealthResponse(status="ok", version="0.3.0")

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

    @app.get("/api/events", response_model=EventsResponse)
    def get_events(
        date_str: str = Query(..., alias="date", description="YYYY-MM-DD"),
        prefecture: str | None = Query(None, description="Comma-separated site ids"),
        force: bool = Query(False, description="Force a fresh scrape even if cached"),
    ) -> EventsResponse:
        """Return events for a date. If not cached, scrape in a worker thread and wait."""
        try:
            target = date.fromisoformat(date_str)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD") from exc

        try:
            combined, scraped = scrape_service.ensure_cached(target, force=force)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Scrape failed: {type(exc).__name__}: {exc}",
            ) from exc

        if combined is None:
            raise HTTPException(status_code=502, detail="Scrape finished but no output was written")

        return _build_events_response(combined, prefecture=prefecture, scraped=scraped)

    @app.get("/api/scrape/status")
    def scrape_status() -> dict:
        return scrape_service.status()

    return app


app = create_app()
