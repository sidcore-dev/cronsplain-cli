"""Command-line entry point for cronsplain-cli."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .core import describe, next_runs, parse_cron


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronsplain-cli",
        description="Explain a 5-field cron expression in plain English and show its next run times.",
    )
    parser.add_argument(
        "expression",
        nargs="+",
        help="Cron expression (quote it, e.g. '*/15 9-17 * * 1-5', or pass the 5 fields as separate arguments)",
    )
    parser.add_argument(
        "--count", type=int, default=5, help="Number of upcoming run times to show (default: 5)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.count < 1:
        print("cronsplain-cli: error: --count must be at least 1", file=sys.stderr)
        return 2

    expression = " ".join(args.expression)

    try:
        parsed = parse_cron(expression)
    except ValueError as exc:
        print(f"cronsplain-cli: error: {exc}", file=sys.stderr)
        return 2

    print(describe(parsed))
    print()

    runs = next_runs(parsed, datetime.now(), args.count)
    if not runs:
        print("No upcoming run times found in the search window (this expression may be impossible to satisfy).")
    else:
        print(f"Next {len(runs)} run time(s):")
        for dt in runs:
            print(f"  {dt.strftime('%Y-%m-%d %H:%M')} ({dt.strftime('%A')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
