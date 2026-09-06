from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from japan_events.models import SiteConfig

if TYPE_CHECKING:
    from japan_events.adapters.base import BaseAdapter

ADAPTERS: dict[str, type[BaseAdapter]] = {}


def register(name: str):
    def decorator(cls: type[BaseAdapter]) -> type[BaseAdapter]:
        ADAPTERS[name] = cls
        cls.name = name
        return cls

    return decorator


def project_root() -> Path:
    env = os.environ.get("JAPAN_EVENTS_ROOT")
    if env:
        return Path(env)
    for candidate in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (candidate / "data" / "sites.yaml").exists():
            return candidate
    return Path.cwd()


def sites_yaml_path() -> Path:
    env = os.environ.get("JAPAN_EVENTS_SITES")
    if env:
        return Path(env)
    return project_root() / "data" / "sites.yaml"


def load_sites(path: Path | None = None) -> list[SiteConfig]:
    yaml_path = path or sites_yaml_path()
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    raw = data.get("sites", data) if isinstance(data, dict) else data
    sites = [SiteConfig.model_validate(item) for item in raw]
    return sites


def filter_sites(sites: list[SiteConfig], prefecture: str | None) -> list[SiteConfig]:
    if not prefecture:
        return sites
    wanted = {part.strip().lower() for part in prefecture.split(",") if part.strip()}
    return [s for s in sites if s.id.lower() in wanted or s.name.lower() in wanted]


def get_adapter(site: SiteConfig) -> BaseAdapter:
    # Imported here so adapter modules can register themselves.
    from japan_events.adapters import load_adapters
    from japan_events.adapters.configured import ConfigurableAdapter
    from japan_events.adapters.loader import load_adapter_yaml

    load_adapters()
    if site.adapter in ADAPTERS and site.adapter not in {"configured", "generic"}:
        return ADAPTERS[site.adapter](site)

    # Prefer declarative YAML model for this site id / adapter name.
    for key in (site.adapter, site.id):
        if key in {"configured", "generic"}:
            continue
        cfg = load_adapter_yaml(key)
        if cfg is not None:
            return ConfigurableAdapter(site, cfg)

    if site.adapter == "configured":
        return ConfigurableAdapter(site, load_adapter_yaml(site.id))

    cls = ADAPTERS.get(site.adapter) or ADAPTERS["generic"]
    return cls(site)
