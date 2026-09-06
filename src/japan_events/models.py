from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
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


class SiteConfig(BaseModel):
    id: str
    name: str
    region: str
    home_url: str
    event_url: str | None = None
    adapter: str = "generic"
    date_picker: bool = False
    cookie_selectors: list[str] = Field(default_factory=list)
    api_url: str | None = None
    source_org: str | None = None
    replaced_from: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def listing_url(self) -> str:
        return self.event_url or self.home_url


class SiteResult(BaseModel):
    prefecture: str
    id: str
    ok: bool
    date: str | None = None
    error: str | None = None
    notes: str | None = None
    event_count: int = 0
    source_url: str | None = None
    adapter: str | None = None
    events: list[Event] = Field(default_factory=list)


class CombinedOutput(BaseModel):
    date: str
    generated_at: str
    site_count: int
    ok_count: int
    event_count: int
    sites: list[SiteResult]
