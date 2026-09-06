from __future__ import annotations

import os

# Parallel Playwright browser contexts per scrape (not OS threads).
# Cap exists because each context is a Chromium profile (~50–150MB) and
# tourism sites will throttle or block a burst of 48 concurrent browsers.
DEFAULT_SITE_CONCURRENCY = 8
MAX_SITE_CONCURRENCY = 16


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
