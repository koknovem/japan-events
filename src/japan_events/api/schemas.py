from __future__ import annotations

from datetime import date
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
    generated_at: str | None = None
    site_count: int = 0
    ok_count: int = 0
    event_count: int = 0
    events: list[EventOut] = Field(default_factory=list)
    sites: list[SiteStatusOut] = Field(default_factory=list)
    message: str | None = None


class ScrapeRequest(BaseModel):
    date: date
    prefecture: str | None = None


class ScrapeJobOut(BaseModel):
    id: str
    date: str
    prefecture: str | None = None
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    event_count: int = 0
    site_count: int = 0
    ok_count: int = 0


class DatesResponse(BaseModel):
    dates: list[str]


class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorBody(BaseModel):
    detail: str
    extras: dict[str, Any] | None = None
