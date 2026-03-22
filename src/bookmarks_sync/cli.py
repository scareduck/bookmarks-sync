from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bookmarks-sync")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("transform", help="Transform Firefox bookmark HTML")
    t.add_argument("input", type=Path)
    t.add_argument("output", type=Path)
    t.add_argument("--container", default="From Firefox")
    t.add_argument("--allow-folder", action="append", default=[])
    t.add_argument("--deny-folder", action="append", default=[])
    t.add_argument("--deny-url-substring", action="append", default=[])
    t.add_argument("--global-dedupe", action="store_true")
    t.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "transform":
        print("Scaffold only: transformation logic not implemented yet.")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Container: {args.container}")
        print(f"Dry run: {args.dry_run}")
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
