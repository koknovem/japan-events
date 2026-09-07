from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime

from japan_events.settings import site_concurrency


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="japan-events",
        description="Discover and scrape official Japan prefecture tourism event calendars.",
    )
    parser.add_argument("--discover", action="store_true", help="Run discovery (alias for the discover command).")
    parser.add_argument("--date", type=_parse_date, help="Target date YYYY-MM-DD (required for scrape).")
    parser.add_argument("--prefecture", help="Comma-separated site ids (e.g. tokyo,kyoto,hokkaido).")
    parser.add_argument("--headed", action="store_true", help="Show the Chromium window.")
    parser.add_argument("--concurrency", type=int, default=None, help="Max parallel browser contexts (default 16, env JAPAN_EVENTS_CONCURRENCY, cap 48).")

    sub = parser.add_subparsers(dest="command")

    scrape = sub.add_parser("scrape", help="Scrape events that occur on --date.")
    scrape.add_argument("--date", type=_parse_date, required=True)
    scrape.add_argument("--prefecture")
    scrape.add_argument("--headed", action="store_true")
    scrape.add_argument("--concurrency", type=int, default=None)

    discover = sub.add_parser("discover", help="Probe each site for event URLs and JSON APIs.")
    discover.add_argument("--prefecture")
    discover.add_argument("--headed", action="store_true")
    discover.add_argument("--concurrency", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    headed = bool(getattr(args, "headed", False))
    concurrency = site_concurrency(getattr(args, "concurrency", None))
    prefecture = getattr(args, "prefecture", None)

    command = args.command
    if getattr(args, "discover", False) and not command:
        command = "discover"
    if command is None:
        if getattr(args, "date", None):
            command = "scrape"
        else:
            parser.print_help()
            sys.exit(2)

    if command == "discover":
        from japan_events.discover import run_discover

        asyncio.run(run_discover(prefecture=prefecture, headed=headed, concurrency=concurrency))
        return

    target = getattr(args, "date", None)
    if target is None:
        parser.error("scrape requires --date YYYY-MM-DD")

    from japan_events.scrape import run_scrape

    asyncio.run(run_scrape(target, prefecture=prefecture, headed=headed, concurrency=concurrency))


if __name__ == "__main__":
    main()
