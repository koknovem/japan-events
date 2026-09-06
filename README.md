# Japan Prefecture Event Scraper

Expandable Playwright + Python pipeline that discovers each official prefecture tourism site’s event API or rendered listing, then scrapes events that occur on a single date.

Sites do **not** share one public events API. The registry in `data/sites.yaml` maps all 47 prefectures plus JNTO to an adapter. New sites are YAML plus an optional adapter class — no core rewrite.

## Install (Windows / PowerShell)

```powershell
cd C:\Users\brian\Downloads\japan_tourist_web
python -m pip install -e .
python -m playwright install chromium
```

## Commands

Discover event pages and JSON/XHR endpoints (writes `discoveries/{id}.json` and `discoveries/summary.json`):

```powershell
japan-events discover
japan-events discover --prefecture tokyo,kyoto
```

Scrape events whose date range includes `--date` (writes `output/{date}/{id}.json` and `output/{date}/all.json`):

```powershell
japan-events scrape --date 2026-09-06
japan-events scrape --date 2026-09-06 --prefecture tokyo,kyoto,hokkaido
japan-events scrape --date 2026-09-06 --headed --concurrency 3
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

## How to add a site

1. Append a block to `data/sites.yaml` (`id`, `name`, `region`, `home_url`, optional `event_url` / `adapter` / `api_url` / `date_picker`).
2. Run `japan-events discover --prefecture <id>` and inspect `discoveries/<id>.json`.
3. If a stable JSON API appears, set `api_url` and/or add `src/japan_events/adapters/<id>.py` decorated with `@register("<id>")`.
4. Point `adapter:` at that name. Everything else can stay on `generic`.

The generic adapter visits `event_url` (or follows `/event|/events|/calendar` from the home page), accepts cookie banners, optionally clicks a calendar date, then harvests **JSON XHR → Schema.org JSON-LD → HTML cards**. Events match if `start_date <= --date <= end_date` (a single date is treated as a one-day range). Dates are parsed from English and Japanese strings.

## Discovery notes (2026-09-06)

Most official sites render HTML calendars rather than a public JSON API. Named adapters were added where discovery found a stable feed:

- **Hiroshima** — `cms.dive-hiroshima.com/.../wp-json/api/v1/events-index/filter/data/`
- **Nara** — `visitnara.jp/travel-directory/api/data/`
- **Hokkaido / Tokyo / Kyoto / JNTO** — HTML calendar or listing pages (date picker on Hokkaido and GO TOKYO)

A few listed hostnames no longer resolve (`visit-iwate.com`, `tokyodaytrip.com`, `visit-fukuoka-japan.com`, `visitokinawa.jp`, `tourismtokushima.jp`). The registry now points at the current official replacements (`iwatetabi.jp`, `visitkanagawa.jp`, `crossroadfukuoka.jp`, `visitokinawajapan.com`, `discovertokushima.net`). JNTO’s events page is often blocked by CloudFront from automated browsers; the site stays in the registry and returns `[]` plus notes rather than failing the run.

## Limits

A single generic adapter will not perfectly parse every CMS. v1 is a complete, expandable pipeline over every listed official site, plus named adapters where discovery finds a stable pattern. Be polite: default concurrency is 3. Sites with no calendar for `--date` write `[]` and a short `notes` field.
