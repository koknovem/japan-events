from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AdapterFieldSelectors(BaseModel):
    title: list[str] = Field(default_factory=lambda: ["h1", "h2", "h3", "h4", ".title", "a"])
    period: list[str] = Field(default_factory=lambda: ["time", ".date", "[class*='date']", "[class*='period']"])
    venue: list[str] = Field(default_factory=lambda: [".venue", ".place", ".location", "[class*='venue']"])
    area: list[str] = Field(default_factory=lambda: [".area", "[class*='area']", "h2 span", ".city"])
    category: list[str] = Field(default_factory=lambda: [".category", "[class*='category']"])
    url: list[str] = Field(default_factory=lambda: ["a[href]"])
    image: list[str] = Field(default_factory=lambda: ["img"])
    description: list[str] = Field(default_factory=list)


class SiteAdapterConfig(BaseModel):
    """Declarative per-site scrape model loaded from data/adapters/{id}.yaml."""

    id: str
    strategy: str = "harvest"  # harvest | html | api | calendar
    event_url: str | None = None
    listing_urls: list[str] = Field(default_factory=list)
    api_url: str | None = None
    api_date_keys: dict[str, str] = Field(default_factory=dict)
    date_picker: bool = False
    wait_ms: int = 1200
    wait_for: str | None = None
    card_selectors: list[str] = Field(default_factory=list)
    fields: AdapterFieldSelectors = Field(default_factory=AdapterFieldSelectors)
    use_card_text_as_period: bool = True
    harvest_fallback: bool = True
    notes: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
