from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from typing import Any, Callable

from japan_events.models import CombinedOutput, SiteConfig
from japan_events.normalize import rewrite_date_query
from japan_events.registry import project_root
from japan_events.settings import SCAN_CONCURRENCY

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
MAX_BODY = 1_500_000
REQUEST_TIMEOUT_S = 8

_SCRIPT_RE = re.compile(r"<script[\s\S]*?</script>", re.I)
_STYLE_RE = re.compile(r"<style[\s\S]*?</style>", re.I)
_HIDDEN_RE = re.compile(r"<input[^>]*type=['\"]hidden['\"][^>]*>", re.I)
_SPACE_RE = re.compile(r"\s+")


def scan_path(target: date, root=None):
    return (root or project_root()) / "output" / target.isoformat() / "_scan.json"


def load_scan(target: date, root=None) -> dict[str, Any] | None:
    path = scan_path(target, root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_scan(target: date, sites: dict[str, dict[str, Any]], root=None) -> None:
    folder = (root or project_root()) / "output" / target.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": target.isoformat(),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "sites": sites,
    }
    scan_path(target, root).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cache_age_seconds(combined: CombinedOutput) -> float:
    raw = combined.generated_at.replace("Z", "+00:00")
    generated = datetime.fromisoformat(raw)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - generated).total_seconds())


def scan_age_seconds(scan: dict[str, Any] | None) -> float | None:
    if not scan or not scan.get("scanned_at"):
        return None
    raw = str(scan["scanned_at"]).replace("Z", "+00:00")
    try:
        scanned = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if scanned.tzinfo is None:
        scanned = scanned.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - scanned).total_seconds())


def normalize_body(content_type: str, body: bytes) -> bytes:
    ctype = (content_type or "").lower()
    if "json" in ctype:
        try:
            obj = json.loads(body.decode("utf-8", errors="ignore"))
            return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except Exception:
            pass
    text = body.decode("utf-8", errors="ignore")
    text = _SCRIPT_RE.sub("", text)
    text = _STYLE_RE.sub("", text)
    text = _HIDDEN_RE.sub("", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text.encode("utf-8", errors="ignore")


def is_dirty(previous: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    """True only when we have a prior fingerprint and a successful fetch that differs."""
    if not previous or current.get("error"):
        return False
    if current.get("status") and int(current["status"]) >= 400:
        return False
    if previous.get("etag") and current.get("etag"):
        return previous["etag"] != current["etag"]
    if previous.get("last_modified") and current.get("last_modified"):
        return previous["last_modified"] != current["last_modified"]
    if previous.get("sha256") and current.get("sha256"):
        return previous["sha256"] != current["sha256"]
    return False


def fingerprint_url(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            raw = resp.read(MAX_BODY)
            headers = {str(k).lower(): v for k, v in resp.headers.items()}
            ctype = headers.get("content-type", "")
            digest = hashlib.sha256(normalize_body(ctype, raw)).hexdigest()
            return {
                "url": url,
                "status": getattr(resp, "status", 200),
                "etag": headers.get("etag"),
                "last_modified": headers.get("last-modified"),
                "sha256": digest,
                "length": len(raw),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "url": url,
            "status": exc.code,
            "etag": None,
            "last_modified": None,
            "sha256": None,
            "length": 0,
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:
        return {
            "url": url,
            "status": None,
            "etag": None,
            "last_modified": None,
            "sha256": None,
            "length": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }


def site_scan_url(site: SiteConfig, target: date) -> str:
    url = site.api_url or site.listing_url
    return rewrite_date_query(url, target)


OnSite = Callable[[SiteConfig, dict[str, Any], bool], None]


def scan_sites(
    sites: list[SiteConfig],
    target: date,
    previous: dict[str, dict[str, Any]] | None,
    *,
    on_site: OnSite | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """HTTP-fingerprint each listing/API URL. Returns (fingerprints, dirty site ids)."""
    prior = previous or {}
    fingerprints: dict[str, dict[str, Any]] = {}
    dirty: list[str] = []

    def one(site: SiteConfig) -> tuple[SiteConfig, dict[str, Any], bool]:
        fp = fingerprint_url(site_scan_url(site, target))
        changed = is_dirty(prior.get(site.id), fp)
        return site, fp, changed

    workers = max(1, min(SCAN_CONCURRENCY, len(sites) or 1))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="japan-scan") as pool:
        futs = [pool.submit(one, site) for site in sites]
        for fut in as_completed(futs):
            site, fp, changed = fut.result()
            fingerprints[site.id] = fp
            if changed:
                dirty.append(site.id)
            if on_site is not None:
                on_site(site, fp, changed)

    dirty.sort()
    return fingerprints, dirty
