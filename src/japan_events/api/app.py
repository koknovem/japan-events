from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from japan_events.api.jobs import jobs
from japan_events.api.schemas import (
    DatesResponse,
    EventOut,
    EventsResponse,
    HealthResponse,
    ScrapeJobOut,
    ScrapeRequest,
    SiteOut,
    SiteStatusOut,
)
from japan_events.registry import filter_sites, load_sites
from japan_events.storage import (
    list_cached_dates,
    load_combined,
    rebuild_combined_from_files,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Japan Events API",
        description="Prefecture tourism event calendars scraped via Playwright adapters.",
        version="0.2.0",
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
        return HealthResponse(status="ok", version="0.2.0")

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
        rebuild: bool = Query(False, description="Rebuild all.json from per-site files"),
    ) -> EventsResponse:
        try:
            target = date.fromisoformat(date_str)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD") from exc

        combined = load_combined(target)
        if combined is None or rebuild:
            combined = rebuild_combined_from_files(target) or combined

        if combined is None:
            return EventsResponse(
                date=target.isoformat(),
                cached=False,
                message="No cached scrape for this date. POST /api/scrape to fetch.",
            )

        site_filter = None
        if prefecture:
            wanted = {p.strip().lower() for p in prefecture.split(",") if p.strip()}
            site_filter = wanted

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
                events.append(
                    EventOut(
                        **ev.model_dump(),
                        site_id=site.id,
                    )
                )

        return EventsResponse(
            date=combined.date,
            cached=True,
            generated_at=combined.generated_at,
            site_count=len(sites_out) if site_filter else combined.site_count,
            ok_count=sum(1 for s in sites_out if s.ok),
            event_count=len(events),
            events=events,
            sites=sites_out,
        )

    @app.post("/api/scrape", response_model=ScrapeJobOut, status_code=202)
    async def start_scrape(body: ScrapeRequest) -> ScrapeJobOut:
        if body.prefecture:
            matched = filter_sites(load_sites(), body.prefecture)
            if not matched:
                raise HTTPException(status_code=400, detail=f"Unknown prefecture filter: {body.prefecture}")
        job = await jobs.enqueue(body.date, body.prefecture)
        return ScrapeJobOut(**jobs.to_dict(job))

    @app.get("/api/scrape/{job_id}", response_model=ScrapeJobOut)
    def scrape_status(job_id: str) -> ScrapeJobOut:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return ScrapeJobOut(**jobs.to_dict(job))

    @app.get("/api/scrape", response_model=list[ScrapeJobOut])
    def list_scrape_jobs() -> list[ScrapeJobOut]:
        return [ScrapeJobOut(**jobs.to_dict(j)) for j in jobs.list_jobs()[:50]]

    return app


app = create_app()
