from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from japan_events.models import CombinedOutput, SiteResult
from japan_events.registry import project_root


def output_dir(target: date, root: Path | None = None) -> Path:
    path = (root or project_root()) / "output" / target.isoformat()
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_site_result(result: SiteResult, target: date, root: Path | None = None) -> Path:
    path = output_dir(target, root) / f"{result.id}.json"
    payload = result.model_dump()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_combined(results: list[SiteResult], target: date, root: Path | None = None) -> Path:
    now = datetime.now(timezone.utc).isoformat()
    combined = CombinedOutput(
        date=target.isoformat(),
        generated_at=now,
        site_count=len(results),
        ok_count=sum(1 for r in results if r.ok),
        event_count=sum(r.event_count for r in results),
        sites=results,
    )
    path = output_dir(target, root) / "all.json"
    path.write_text(
        json.dumps(combined.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def list_cached_dates(root: Path | None = None) -> list[str]:
    base = (root or project_root()) / "output"
    if not base.exists():
        return []
    dates: list[str] = []
    for child in sorted(base.iterdir()):
        if child.is_dir() and (child / "all.json").exists():
            dates.append(child.name)
    return dates


def load_combined(target: date, root: Path | None = None) -> CombinedOutput | None:
    path = (root or project_root()) / "output" / target.isoformat() / "all.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return CombinedOutput.model_validate(data)


def load_site_result(target: date, site_id: str, root: Path | None = None) -> SiteResult | None:
    path = (root or project_root()) / "output" / target.isoformat() / f"{site_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SiteResult.model_validate(data)


def rebuild_combined_from_files(target: date, root: Path | None = None) -> CombinedOutput | None:
    """Assemble all.json from per-prefecture files when all.json is missing or stale."""
    folder = (root or project_root()) / "output" / target.isoformat()
    if not folder.exists():
        return None
    results: list[SiteResult] = []
    for path in sorted(folder.glob("*.json")):
        if path.name == "all.json" or path.name.startswith("_"):
            continue
        try:
            results.append(SiteResult.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except Exception:
            continue
    if not results:
        return None
    write_combined(results, target, root)
    return load_combined(target, root)
