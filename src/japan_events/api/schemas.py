from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SiteOut(BaseModel):
    id: str
    name: str
    region: str
    home_url: str
    event_url: str | None = None
    source_org: str | None = None
    adapter: str


class EventOut(BaseModel):
    prefecture: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    venue: str | None = None
    area: str | None = None
    category: str | None = None
    description: str | None = None
    url: str | None = None
    image_url: str | None = None
    source: str
    lang: str = "ja"
    site_id: str | None = None


class SiteStatusOut(BaseModel):
    id: str
    prefecture: str
    ok: bool
    event_count: int
    error: str | None = None
    notes: str | None = None
    source_url: str | None = None
    adapter: str | None = None


class EventsResponse(BaseModel):
    date: str
    cached: bool
    scraped: bool = False
    generated_at: str | None = None
    site_count: int = 0
    ok_count: int = 0
    event_count: int = 0
    events: list[EventOut] = Field(default_factory=list)
    sites: list[SiteStatusOut] = Field(default_factory=list)
    message: str | None = None
    refreshing: bool = False


class DatesResponse(BaseModel):
    dates: list[str]


class HealthResponse(BaseModel):
    status: str
    version: str


class ScrapeSiteProgressOut(BaseModel):
    id: str
    prefecture: str
    status: str
    event_count: int = 0
    error: str | None = None


class ScrapeJobOut(BaseModel):
    date: str
    phase: str
    total: int = 0
    done: int = 0
    ok_count: int = 0
    events_so_far: int = 0
    percent: int = 0
    running: list[str] = Field(default_factory=list)
    sites: list[ScrapeSiteProgressOut] = Field(default_factory=list)
    error: str | None = None
    concurrency: int = 0


class ScrapeStatusOut(BaseModel):
    inflight_dates: list[str] = Field(default_factory=list)
    workers: int = 0
    job: ScrapeJobOut | None = None
    jobs: list[ScrapeJobOut] = Field(default_factory=list)


class ErrorBody(BaseModel):
    detail: str
    extras: dict[str, Any] | None = None
