# Japan Prefecture Event Scraper

Expandable Playwright + Python pipeline that discovers each official prefecture tourism site’s event API or rendered listing, then scrapes events that occur on a single date.

Every site has a **dedicated adapter model**: declarative YAML in `data/adapters/{id}.yaml`, optional custom Python in `src/japan_events/adapters/sites/{id}.py`, registered from `data/sites.yaml`. The generic HTML harvester remains a shared fallback — not the only parser.

## Install (Windows / PowerShell)

```powershell
cd C:\Users\brian\Downloads\japan_tourist_web
python -m pip install -e .
python -m playwright install chromium
```

## Docker Compose

Needs Docker Engine with Compose v2. Scrapes persist in `./output`. UI is on port 5173; the API is on 8000.

```powershell
docker compose build
docker compose up -d
```

Open http://127.0.0.1:5173 and http://127.0.0.1:8000/docs

```powershell
docker compose run --rm --no-deps api python -m pytest -q
docker compose logs -f
docker compose down
```

The API image is based on Playwright’s official Chromium image (large first pull). Jenkins uses the same compose file.

## Jenkins

The agent must have Docker (mount `/var/run/docker.sock` if Jenkins itself is a container). Create a Pipeline job with **Pipeline script from SCM** pointing at this repo; it will run `Jenkinsfile`: build images, pytest, `docker compose up -d`, then smoke `/api/health` and the UI.

## API server (FastAPI)

```powershell
cd C:\Users\brian\Downloads\japan_tourist_web
python -m pip install -e .
japan-events-api
# or: python -m japan_events.api.main
```

Open docs at http://127.0.0.1:8000/docs

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Health check |
| GET | `/api/sites` | Registry of prefectures |
| GET | `/api/dates` | Cached scrape dates under `output/` |
| GET | `/api/events?date=YYYY-MM-DD` | Events for a date (auto-scrapes if missing; optional `prefecture=`, `lang=en\|ja\|zh-TW\|zh-CN`) |
| GET | `/api/langs` | Supported scrape/UI languages |
| GET | `/api/scrape/status` | In-flight scrape dates |

`GET /api/events` serves cached JSON immediately when present. If the date is missing, the API runs Playwright in a **thread**, blocks until finished, then returns the result (the UI just waits on the request).

### Multi-language sources

Scrapes tag each event with `lang` (`en` / `ja` / `zh-TW` / `zh-CN`). Declare URLs in `data/adapters/{id}.yaml`:

```yaml
urls_by_lang:
  en: https://example.jp/en/event/
  ja: https://example.jp/ja/event/
  zh-TW: https://example.jp/zh-tw/event/
  zh-CN: https://example.jp/zh-cn/event/
```

If omitted, `/en/`-style paths are rewritten when possible; JP-only 観光協会 calendars scrape once as `ja`. The UI sends `?lang=` from the language switcher and falls back to ja → en when that locale has no rows.

## Web UI (React + TypeScript)

```powershell
cd web
npm install
npm run dev
```

UI: http://127.0.0.1:5173 (Vite proxies `/api` → FastAPI `:8000`)

Structure:

- `web/src/components/calendar/` — month calendar for date selection
- `web/src/components/events/` — list, card, prefecture filter, scrape controls
- `web/src/hooks/useEvents.ts` — data loading + scrape polling
- `web/src/api/client.ts` — typed API client

## CLI commands

Discover event pages and JSON/XHR endpoints (writes `discoveries/{id}.json` and `discoveries/summary.json`):

```powershell
japan-events discover
japan-events discover --prefecture tokyo,kyoto
```

Scrape events whose date range includes `--date` (writes `output/{date}/{id}.json` and `output/{date}/all.json`):

```powershell
japan-events scrape --date 2026-09-06
japan-events scrape --date 2026-09-06 --prefecture tokyo,kyoto,hokkaido
japan-events scrape --date 2026-09-06 --headed --concurrency 8
```

`python -m japan_events` is equivalent to `japan-events`.

## Output

Each prefecture file:

```json
{
  "prefecture": "Tokyo",
  "id": "tokyo",
  "ok": true,
  "date": "2026-09-06",
  "notes": "html:12",
  "event_count": 3,
  "events": [
    {
      "prefecture": "Tokyo",
      "title": "Example festival",
      "start_date": "2026-09-01",
      "end_date": "2026-09-10",
      "venue": null,
      "url": "https://...",
      "source": "https://www.gotokyo.org/en/event-calendar/index.html#html"
    }
  ]
}
```

A broken site never aborts the run. Failures appear in `all.json` as `{ "prefecture", "ok": false, "error" }`. Sites with no calendar return `[]` plus a short `notes` field.

## Architecture

| Layer | Role |
| --- | --- |
| `data/sites.yaml` | Registry: id, home/event URLs, `adapter: <id>` |
| `data/adapters/{id}.yaml` | Per-site scrape model: selectors, API URL templates, wait/date-picker |
| `adapters/configured.py` | Loads YAML → site-specific card/API harvest |
| `adapters/sites/{id}.py` | Custom Python when YAML is not enough (API quirks, calendars, form filters) |
| `adapters/generic.py` | Shared JSON-LD / XHR / HTML harvester used as fallback |

Resolution order for `adapter: aichi`:

1. `@register("aichi")` class under `adapters/sites/` (or legacy top-level module)
2. Else `data/adapters/aichi.yaml` via `ConfigurableAdapter`
3. Else `generic`

## How to add a site-specific adapter

### A. YAML-only (most CMS HTML listings)

1. Add/update the site block in `data/sites.yaml` (`adapter: <id>`).
2. Create `data/adapters/<id>.yaml`:

```yaml
id: aichi
strategy: html
event_url: https://aichinow.pref.aichi.jp/en/events/
card_selectors:
  - "div.list"
fields:
  title: ["h2 a", "h2"]
  period: [".left"]
  area: ["h2 span"]
  url: ["h2 a"]
use_card_text_as_period: true
wait_for: "div.list"
wait_ms: 2000
harvest_fallback: true
```

3. Run `japan-events discover --prefecture <id>` and refine `event_url` / `card_selectors` from `discoveries/<id>.json`.
4. Test: `japan-events scrape --date 2026-09-06 --prefecture <id>`

Useful YAML fields: `api_url` (supports `{date}` / `{start}` / `{end}`), `api_date_keys`, `date_picker`, `listing_urls`, `notes`.

### B. Custom Python (APIs, calendars, search forms)

1. Add `src/japan_events/adapters/sites/<id>.py`:

```python
from japan_events.adapters.base import BaseAdapter
from japan_events.registry import register

@register("mypref")
class MyPrefAdapter(BaseAdapter):
    name = "mypref"

    async def scrape(self, target, session):
        ...
```

2. Keep a YAML model for URLs/selectors even when Python owns the flow.
3. Point `adapter: mypref` in `sites.yaml`. Modules under `adapters/sites/` are auto-imported.

Existing custom adapters: **hiroshima**, **nara**, **hokkaido**, **tokyo**, **kyoto**, **jnto**, **ibaraki**.

## Discovery notes

Most official sites render HTML calendars rather than a public JSON API. Named/YAML adapters encode the CMS shape found by discovery + live probing.

A few hostnames historically failed DNS; the registry uses current official domains (`iwatetabi.jp`, `visitkanagawa.jp`, `crossroadfukuoka.jp`, `visitokinawajapan.com`, `discovertokushima.net`). JNTO’s events page is often blocked by CloudFront from automated browsers — it stays in the registry and returns `[]` plus notes.

## Limits

Be polite: default concurrency is 8 parallel Playwright browser contexts (not OS threads), capped at 16. Override with `--concurrency` or `JAPAN_EVENTS_CONCURRENCY`. Opening all 48 prefectures at once would burn RAM and get tourism sites to throttle. Cached dates are shown immediately; a background HTTP scan (ETag / Last-Modified / body fingerprint) checks for updates about every 30 minutes and only re-scrapes prefectures that changed. A full Playwright pass still runs if the cache is older than 12 hours (`JAPAN_EVENTS_SCAN_TTL_MINUTES`, `JAPAN_EVENTS_DEEP_REFRESH_HOURS`). Sites that only publish seasonal festival guides (no day-level calendar for `--date`) correctly return `[]`. Per-site failures never abort the full run.
