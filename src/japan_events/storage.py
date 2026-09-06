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
