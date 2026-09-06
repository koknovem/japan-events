from __future__ import annotations

import threading
from typing import Any


class JobProgress:
    """Thread-safe scrape progress for one date. Percent only moves when sites finish."""

    def __init__(self, date_key: str) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {
            "date": date_key,
            "phase": "starting",
            "total": 0,
            "done": 0,
            "ok_count": 0,
            "events_so_far": 0,
            "percent": 0,
            "running": [],
            "sites": [],
            "error": None,
            "concurrency": 0,
        }

    def handle(self, event: str, payload: dict[str, Any] | None = None) -> None:
        payload = payload or {}
        with self._lock:
            if event == "init":
                sites = payload.get("sites") or []
                self._state["phase"] = str(payload.get("phase") or "scraping")
                self._state["total"] = len(sites)
                self._state["done"] = 0
                self._state["ok_count"] = 0
                self._state["events_so_far"] = 0
                self._state["running"] = []
                self._state["concurrency"] = int(payload.get("concurrency") or 0)
                self._state["sites"] = [
                    {
                        "id": site["id"],
                        "prefecture": site.get("prefecture") or site["id"],
                        "status": "pending",
                        "event_count": 0,
                        "error": None,
                    }
                    for site in sites
                ]
            elif event == "site_start":
                if self._state["phase"] not in {"scanning", "combining", "done"}:
                    self._state["phase"] = str(payload.get("phase") or self._state["phase"] or "scraping")
                site_id = payload.get("id")
                if site_id and site_id not in self._state["running"]:
                    self._state["running"].append(site_id)
                self._set_site(site_id, status="running")
            elif event == "site_done":
                site_id = payload.get("id")
                ok = bool(payload.get("ok", True))
                count = int(payload.get("event_count") or 0)
                error = payload.get("error")
                if site_id in self._state["running"]:
                    self._state["running"] = [s for s in self._state["running"] if s != site_id]
                site = self._set_site(
                    site_id,
                    status="ok" if ok else "error",
                    event_count=count,
                    error=error,
                    prefecture=payload.get("prefecture"),
                )
                if site is not None:
                    self._state["done"] = sum(
                        1 for item in self._state["sites"] if item["status"] in {"ok", "error"}
                    )
                    self._state["ok_count"] = sum(1 for item in self._state["sites"] if item["status"] == "ok")
                    self._state["events_so_far"] = sum(
                        int(item.get("event_count") or 0) for item in self._state["sites"]
                    )
            elif event == "combining":
                self._state["phase"] = "combining"
                self._state["running"] = []
            elif event == "done":
                self._state["phase"] = "done"
                self._state["running"] = []
                if payload.get("ok_count") is not None:
                    self._state["ok_count"] = int(payload["ok_count"])
                if payload.get("event_count") is not None:
                    self._state["events_so_far"] = int(payload["event_count"])
            elif event == "error":
                self._state["phase"] = "error"
                self._state["error"] = str(payload.get("error") or "Scrape failed")
                self._state["running"] = []
            self._recompute_percent()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            phase = self._state["phase"]
            total = int(self._state["total"] or 0)
            return {
                "date": self._state["date"],
                "phase": phase,
                "total": total,
                "done": self._state["done"],
                "ok_count": self._state["ok_count"],
                "events_so_far": self._state["events_so_far"],
                "percent": self._state["percent"],
                "running": list(self._state["running"]),
                "sites": [dict(item) for item in self._state["sites"]],
                "error": self._state["error"],
                "concurrency": self._state["concurrency"],
                "queued": phase == "starting" and total == 0,
            }

    def _set_site(self, site_id: str | None, **fields: Any) -> dict[str, Any] | None:
        if not site_id:
            return None
        for item in self._state["sites"]:
            if item["id"] == site_id:
                for key, value in fields.items():
                    if value is not None:
                        item[key] = value
                return item
        item = {
            "id": site_id,
            "prefecture": fields.get("prefecture") or site_id,
            "status": fields.get("status") or "pending",
            "event_count": fields.get("event_count") or 0,
            "error": fields.get("error"),
        }
        self._state["sites"].append(item)
        self._state["total"] = len(self._state["sites"])
        return item

    def _recompute_percent(self) -> None:
        phase = self._state["phase"]
        total = int(self._state["total"] or 0)
        done = int(self._state["done"] or 0)
        if phase == "done":
            self._state["percent"] = 100
            return
        if phase == "error":
            return
        if total <= 0:
            self._state["percent"] = 0
            return
        pct = int((done * 100) / total)
        if phase == "combining":
            pct = max(pct, 99)
        self._state["percent"] = min(99 if phase != "done" else 100, pct)
