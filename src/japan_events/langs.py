"""Multi-language scrape targets for tourism sources.

Default set matches common Japan DMO menus:
English, Japanese, Traditional Chinese, Simplified Chinese.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

if TYPE_CHECKING:
    from japan_events.adapter_config import SiteAdapterConfig
    from japan_events.models import SiteConfig

# UI / API language codes
SCRAPE_LANGS = ("en", "ja", "zh-TW", "zh-CN")

# Path segment substitutions tried in order for each language.
_LANG_PATHS: dict[str, list[str]] = {
    "en": ["/en/", "/english/", "/eng/", "/e/"],
    "ja": ["/ja/", "/jp/", "/japanese/", "/j/"],
    "zh-TW": ["/zh-tw/", "/zh_tw/", "/zh-hant/", "/tw/", "/tc/", "/cht/", "/zh-HK/", "/hk/"],
    "zh-CN": ["/zh-cn/", "/zh_cn/", "/zh-hans/", "/cn/", "/sc/", "/chs/", "/zh/"],
}

_KNOWN_SEG = re.compile(
    r"/(en|english|eng|e|ja|jp|japanese|j|zh-tw|zh_tw|zh-hant|tw|tc|cht|zh-hk|hk|"
    r"zh-cn|zh_cn|zh-hans|cn|sc|chs|zh)(/|$)",
    re.I,
)


def detect_lang_from_url(url: str) -> str | None:
    path = urlsplit(url).path.lower()
    for lang, markers in _LANG_PATHS.items():
        for m in markers:
            if m.rstrip("/") in path or path.startswith(m) or f"{m}" in f"{path}/":
                # Prefer more specific zh-TW / zh-CN over bare /zh/
                if lang == "zh-CN" and any(x in path for x in ("zh-tw", "zh_tw", "zh-hant", "/tw/", "/tc/", "/cht/", "/hk/")):
                    continue
                return lang
    if "/jp/" in path or path.rstrip("/").endswith("/jp"):
        return "ja"
    return None


def _replace_lang_segment(url: str, target_lang: str) -> str | None:
    """Rewrite a URL's language path segment to target_lang. None if no segment found."""
    parts = urlsplit(url)
    path = parts.path
    match = _KNOWN_SEG.search(path)
    if not match:
        return None
    new_seg = _LANG_PATHS[target_lang][0]  # canonical, includes trailing slash style
    # match.group(0) may be '/en/' or '/en'
    old = match.group(0)
    if old.endswith("/") and not new_seg.endswith("/"):
        new_seg = new_seg
    elif not old.endswith("/") and new_seg.endswith("/"):
        new_seg = new_seg.rstrip("/")
        if match.group(2) == "/":
            new_seg = new_seg + "/"
    # Use first canonical form without forcing double slashes
    canon = {
        "en": "en",
        "ja": "ja",
        "zh-TW": "zh-tw",
        "zh-CN": "zh-cn",
    }[target_lang]
    replacement = f"/{canon}{match.group(2)}"
    new_path = path[: match.start()] + replacement + path[match.end() :]
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))


def _insert_lang_segment(url: str, target_lang: str) -> str:
    """Insert /{lang}/ after the domain path root when no language segment exists."""
    parts = urlsplit(url)
    path = parts.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    seg = {"en": "en", "ja": "ja", "zh-TW": "zh-tw", "zh-CN": "zh-cn"}[target_lang]
    if path == "/":
        new_path = f"/{seg}/"
    else:
        new_path = f"/{seg}{path}" if not path.startswith(f"/{seg}") else path
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))


def resolve_lang_urls(
    site: SiteConfig,
    config: SiteAdapterConfig | None = None,
) -> dict[str, str]:
    """
    Return {lang: event_url} for langs we should scrape.
    Explicit urls_by_lang wins; otherwise rewrite / guess from primary listing URL.
    Duplicate URLs collapse to a single lang (prefer ja, then en, then first).
    """
    explicit: dict[str, str] = {}
    if config and getattr(config, "urls_by_lang", None):
        explicit.update({k: v for k, v in config.urls_by_lang.items() if v})
    if site.extra.get("urls_by_lang"):
        explicit.update({k: v for k, v in site.extra["urls_by_lang"].items() if v})

    primary = None
    if config and config.event_url:
        primary = config.event_url
    primary = primary or site.event_url or site.home_url

    out: dict[str, str] = {}
    for lang in SCRAPE_LANGS:
        if lang in explicit:
            out[lang] = explicit[lang]
            continue
        rewritten = _replace_lang_segment(primary, lang)
        if rewritten and rewritten != primary:
            out[lang] = rewritten
        elif detect_lang_from_url(primary) == lang:
            out[lang] = primary

    # If primary has no lang marker (typical 観光協会 JP-only), scrape once as Japanese.
    # Do not invent /en/ paths that 404 — sites can opt in via urls_by_lang.
    if not out:
        detected = detect_lang_from_url(primary) or "ja"
        out[detected] = primary
        return out

    # Collapse identical URLs onto one language label
    by_url: dict[str, list[str]] = {}
    for lang, url in out.items():
        by_url.setdefault(url, []).append(lang)
    collapsed: dict[str, str] = {}
    priority = ["ja", "en", "zh-TW", "zh-CN"]
    for url, langs in by_url.items():
        langs_sorted = sorted(langs, key=lambda L: priority.index(L) if L in priority else 99)
        collapsed[langs_sorted[0]] = url

    return collapsed


def map_ui_lang_to_scrape(ui_lang: str) -> str:
    """Map react-i18next language codes onto scrape lang tags."""
    key = (ui_lang or "en").replace("_", "-")
    lower = key.lower()
    if lower.startswith("zh-tw") or lower in {"zh-hant", "zh-hk"}:
        return "zh-TW"
    if lower.startswith("zh-cn") or lower in {"zh-hans", "zh"}:
        return "zh-CN"
    if lower.startswith("ja"):
        return "ja"
    if lower.startswith("en"):
        return "en"
    if key in SCRAPE_LANGS:
        return key
    return "en"
