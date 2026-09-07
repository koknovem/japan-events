from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from japan_events.models import CombinedOutput, SiteResult
from japan_events.registry import load_sites, project_root

_PENDING_REFRESH = "_pending_refresh.json"


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


def expected_site_ids() -> set[str]:
    return {site.id for site in load_sites()}


def site_result_ids(target: date, root: Path | None = None) -> set[str]:
    folder = (root or project_root()) / "output" / target.isoformat()
    if not folder.exists():
        return set()
    ids: set[str] = set()
    for path in folder.glob("*.json"):
        if path.name == "all.json" or path.name.startswith("_"):
            continue
        ids.add(path.stem)
    return ids


def missing_site_ids(target: date, root: Path | None = None) -> list[str]:
    return sorted(expected_site_ids() - site_result_ids(target, root))


def list_output_dates(root: Path | None = None) -> list[date]:
    base = (root or project_root()) / "output"
    if not base.exists():
        return []
    dates: list[date] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        try:
            dates.append(date.fromisoformat(child.name))
        except ValueError:
            continue
    return dates


def list_incomplete_dates(root: Path | None = None) -> list[date]:
    return [target for target in list_output_dates(root) if missing_site_ids(target, root)]


def save_pending_refresh(target: date, site_ids: list[str], root: Path | None = None) -> Path:
    path = output_dir(target, root) / _PENDING_REFRESH
    path.write_text(json.dumps({"ids": list(site_ids)}, indent=2) + "\n", encoding="utf-8")
    return path


def load_pending_refresh(target: date, root: Path | None = None) -> list[str]:
    path = (root or project_root()) / "output" / target.isoformat() / _PENDING_REFRESH
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    ids = data.get("ids") if isinstance(data, dict) else None
    if not isinstance(ids, list):
        return []
    return [str(item) for item in ids if item]


def clear_pending_refresh(target: date, root: Path | None = None) -> None:
    path = (root or project_root()) / "output" / target.isoformat() / _PENDING_REFRESH
    path.unlink(missing_ok=True)


def list_pending_refreshes(root: Path | None = None) -> list[tuple[date, list[str]]]:
    pending: list[tuple[date, list[str]]] = []
    for target in list_output_dates(root):
        ids = load_pending_refresh(target, root)
        if ids:
            pending.append((target, ids))
    return pending


def list_cached_dates(root: Path | None = None) -> list[str]:
    base = (root or project_root()) / "output"
    if not base.exists():
        return []
    dates: list[str] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or not (child / "all.json").exists():
            continue
        try:
            target = date.fromisoformat(child.name)
        except ValueError:
            continue
        if missing_site_ids(target, root):
            continue
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


def assemble_from_files(target: date, root: Path | None = None, *, persist: bool = False) -> CombinedOutput | None:
    """Build a CombinedOutput from per-prefecture JSON. persist=True writes all.json."""
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
    if persist:
        write_combined(results, target, root)
        return load_combined(target, root)
    now = datetime.now(timezone.utc).isoformat()
    return CombinedOutput(
        date=target.isoformat(),
        generated_at=now,
        site_count=len(results),
        ok_count=sum(1 for item in results if item.ok),
        event_count=sum(item.event_count for item in results),
        sites=results,
    )


def live_combined(target: date, root: Path | None = None) -> CombinedOutput | None:
    """Latest on-disk snapshot. Site files overlay all.json; never writes all.json."""
    folder = (root or project_root()) / "output" / target.isoformat()
    from_files: dict[str, SiteResult] = {}
    if folder.exists():
        for path in folder.glob("*.json"):
            if path.name == "all.json" or path.name.startswith("_"):
                continue
            try:
                site = SiteResult.model_validate(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            from_files[site.id] = site

    base = load_combined(target, root)
    if base is None and not from_files:
        return None
    merged: dict[str, SiteResult] = {}
    if base is not None:
        merged = {site.id: site for site in base.sites}
    merged.update(from_files)
    sites = list(merged.values())
    generated = base.generated_at if base is not None else datetime.now(timezone.utc).isoformat()
    return CombinedOutput(
        date=target.isoformat(),
        generated_at=generated,
        site_count=len(sites),
        ok_count=sum(1 for item in sites if item.ok),
        event_count=sum(item.event_count for item in sites),
        sites=sites,
    )


def rebuild_combined_from_files(target: date, root: Path | None = None) -> CombinedOutput | None:
    """Assemble all.json from per-prefecture files when all.json is missing or stale."""
    return assemble_from_files(target, root, persist=True)
