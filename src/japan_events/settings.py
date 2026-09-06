from __future__ import annotations

import os

# Parallel Playwright browser contexts per scrape (not OS threads).
# Cap exists because each context is a Chromium profile (~50–150MB) and
# tourism sites will throttle or block a burst of 48 concurrent browsers.
DEFAULT_SITE_CONCURRENCY = 8
MAX_SITE_CONCURRENCY = 16
SCAN_CONCURRENCY = 16
DEFAULT_SCAN_TTL_MINUTES = 30
DEFAULT_DEEP_REFRESH_HOURS = 12


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, min(maximum, int(raw)))
    except ValueError:
        return default


def site_concurrency(override: int | None = None) -> int:
    """How many prefecture sites to scrape at once."""
    if override is not None:
        value = override
    else:
        raw = os.environ.get("JAPAN_EVENTS_CONCURRENCY", "").strip()
        if not raw:
            return DEFAULT_SITE_CONCURRENCY
        try:
            value = int(raw)
        except ValueError:
            return DEFAULT_SITE_CONCURRENCY
    return max(1, min(MAX_SITE_CONCURRENCY, value))


def scan_ttl_seconds() -> int:
    return _env_int("JAPAN_EVENTS_SCAN_TTL_MINUTES", DEFAULT_SCAN_TTL_MINUTES, 5, 24 * 60) * 60


def deep_refresh_seconds() -> int:
    return _env_int("JAPAN_EVENTS_DEEP_REFRESH_HOURS", DEFAULT_DEEP_REFRESH_HOURS, 1, 168) * 3600
