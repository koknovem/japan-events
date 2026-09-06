from __future__ import annotations

from pathlib import Path

import yaml

from japan_events.adapter_config import SiteAdapterConfig
from japan_events.registry import project_root


def adapters_dir() -> Path:
    return project_root() / "data" / "adapters"


def load_adapter_yaml(site_id: str) -> SiteAdapterConfig | None:
    path = adapters_dir() / f"{site_id}.yaml"
    if not path.exists():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    raw.setdefault("id", site_id)
    return SiteAdapterConfig.model_validate(raw)


def list_adapter_yaml_ids() -> list[str]:
    root = adapters_dir()
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.yaml"))
