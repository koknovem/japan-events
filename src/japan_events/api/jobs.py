from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any


@dataclass
class ScrapeJob:
    id: str
    date: str
    prefecture: str | None
    status: str = "queued"  # queued | running | completed | failed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    event_count: int = 0
    site_count: int = 0
    ok_count: int = 0


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, ScrapeJob] = {}
        self._lock = asyncio.Lock()
        self._running = False

    def list_jobs(self) -> list[ScrapeJob]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def get(self, job_id: str) -> ScrapeJob | None:
        return self._jobs.get(job_id)

    async def enqueue(self, target: date, prefecture: str | None = None) -> ScrapeJob:
        job = ScrapeJob(
            id=str(uuid.uuid4()),
            date=target.isoformat(),
            prefecture=prefecture,
        )
        async with self._lock:
            self._jobs[job.id] = job
        asyncio.create_task(self._run(job.id))
        return job

    async def _run(self, job_id: str) -> None:
        job = self._jobs[job_id]
        async with self._lock:
            if self._running:
                # Simple serial queue: wait until free.
                while self._running:
                    await asyncio.sleep(0.5)
            self._running = True
            job.status = "running"
            job.started_at = datetime.now(timezone.utc).isoformat()

        try:
            from japan_events.scrape import run_scrape

            results = await run_scrape(
                date.fromisoformat(job.date),
                prefecture=job.prefecture,
                headed=False,
                concurrency=3,
            )
            job.site_count = len(results)
            job.ok_count = sum(1 for r in results if r.ok)
            job.event_count = sum(r.event_count for r in results)
            job.status = "completed"
        except Exception as exc:
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
        finally:
            job.finished_at = datetime.now(timezone.utc).isoformat()
            async with self._lock:
                self._running = False

    def to_dict(self, job: ScrapeJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "date": job.date,
            "prefecture": job.prefecture,
            "status": job.status,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "error": job.error,
            "event_count": job.event_count,
            "site_count": job.site_count,
            "ok_count": job.ok_count,
        }


jobs = JobManager()
