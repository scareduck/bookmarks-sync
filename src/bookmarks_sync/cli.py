from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .backup import create_backup, default_backup_root
from .bookmark_html import write_bookmarks_html
from .firefox_db import find_places_db, read_firefox_bookmarks
from .model import SyncReport, count_bookmarks, count_folders
from .process_check import BrowserRunningError, require_browsers_stopped
from .safari_plist import (
    SafariBookmarksAccessError,
    default_safari_bookmarks,
    preview,
    prune_top_level_items,
    read_top_level_items,
    write_safari_bookmarks,
)
from .safari_ui import SafariUIAutomationError, delete_top_level_bookmark_items, import_bookmarks_html
from .transform import transform_tree


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bookmarks-sync")
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync", help="Sync Firefox bookmarks into Safari")
    sync.add_argument("--firefox-db", type=Path)
    sync.add_argument("--firefox-profile", type=Path)
    sync.add_argument("--safari-bookmarks", type=Path, default=default_safari_bookmarks())
    sync.add_argument("--allow-folder", action="append", default=[])
    sync.add_argument("--deny-folder", action="append", default=[])
    sync.add_argument("--deny-url-substring", action="append", default=[])
    sync.add_argument("--global-dedupe", action="store_true")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--apply", action="store_true")

    backup = sub.add_parser("backup", help="Back up Firefox and Safari bookmark files")
    backup.add_argument("--firefox-db", type=Path)
    backup.add_argument("--firefox-profile", type=Path)
    backup.add_argument("--safari-bookmarks", type=Path, default=default_safari_bookmarks())
    backup.add_argument("--output-dir", type=Path, default=default_backup_root())

    export_html = sub.add_parser("export-html", help="Export transformed Firefox bookmarks as Safari import HTML")
    add_source_options(export_html)
    export_html.add_argument("output", type=Path)

    import_ui = sub.add_parser("import-ui", help="Ask Safari to import a bookmarks HTML file through its UI")
    import_ui.add_argument("html_file", type=Path)
    import_ui.add_argument("--yes-really-click-safari", action="store_true")

    inspect = sub.add_parser("inspect-safari", help="Print Safari's top-level bookmark plist items")
    inspect.add_argument("--safari-bookmarks", type=Path, default=default_safari_bookmarks())

    prune = sub.add_parser("prune-safari-top-level", help="Remove non-system top-level Safari bookmark items")
    prune.add_argument("--safari-bookmarks", type=Path, default=default_safari_bookmarks())
    prune.add_argument("--apply", action="store_true")

    delete_ui = sub.add_parser("delete-top-level-ui", help="Delete non-system top-level bookmarks through Safari UI")
    delete_ui.add_argument("--safari-bookmarks", type=Path, default=default_safari_bookmarks())
    delete_ui.add_argument("--yes-really-click-safari", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "sync":
        return sync(args)
    if args.command == "backup":
        return backup(args)
    if args.command == "export-html":
        return export_html(args)
    if args.command == "import-ui":
        return import_ui(args)
    if args.command == "inspect-safari":
        return inspect_safari(args)
    if args.command == "prune-safari-top-level":
        return prune_safari_top_level(args)
    if args.command == "delete-top-level-ui":
        return delete_top_level_ui(args)

    parser.error("Unknown command")
    return 2


def add_source_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--firefox-db", type=Path)
    parser.add_argument("--firefox-profile", type=Path)
    parser.add_argument("--allow-folder", action="append", default=[])
    parser.add_argument("--deny-folder", action="append", default=[])
    parser.add_argument("--deny-url-substring", action="append", default=[])
    parser.add_argument("--global-dedupe", action="store_true")


def load_transformed_firefox_tree(args: argparse.Namespace, report: SyncReport | None = None):
    db_path = args.firefox_db or find_places_db(args.firefox_profile)
    root = read_firefox_bookmarks(db_path)
    if report is not None:
        report.folders_read = count_folders(root)
        report.bookmarks_read = count_bookmarks(root)
    transformed = transform_tree(
        root,
        allow_folders=args.allow_folder,
        deny_folders=args.deny_folder,
        deny_url_substrings=args.deny_url_substring,
        global_dedupe=args.global_dedupe,
        report=report,
    )
    return db_path, transformed


def sync(args: argparse.Namespace) -> int:
    if args.apply and args.dry_run:
        print("Use either --apply or --dry-run, not both.", file=sys.stderr)
        return 2
    if not args.apply:
        args.dry_run = True

    try:
        require_browsers_stopped()
    except BrowserRunningError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report = SyncReport()
    db_path, transformed = load_transformed_firefox_tree(args, report)
    report.bookmarks_written = count_bookmarks(transformed)

    print(f"Firefox database: {db_path}")
    print(f"Safari bookmarks: {args.safari_bookmarks}")
    print(f"Folders read: {report.folders_read}")
    print(f"Bookmarks read: {report.bookmarks_read}")
    print(f"Duplicates removed: {report.duplicate_bookmarks_removed}")
    print(f"Bookmarks to write: {report.bookmarks_written}")

    if args.dry_run:
        print(preview(transformed))
        print("Dry run only. Re-run with --apply to replace Safari bookmarks.")
        return 0

    try:
        report.backup_path = write_safari_bookmarks(transformed, args.safari_bookmarks)
    except SafariBookmarksAccessError as exc:
        print(str(exc), file=sys.stderr)
        print("No Safari changes were written.", file=sys.stderr)
        return 1

    if report.backup_path:
        print(f"Backup: {report.backup_path}")
    print("Safari bookmarks replaced.")
    return 0


def export_html(args: argparse.Namespace) -> int:
    try:
        require_browsers_stopped(["Firefox"])
    except BrowserRunningError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report = SyncReport()
    db_path, transformed = load_transformed_firefox_tree(args, report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(write_bookmarks_html(transformed), encoding="utf-8")
    print(f"Firefox database: {db_path}")
    print(f"Output HTML: {args.output}")
    print(f"Folders read: {report.folders_read}")
    print(f"Bookmarks read: {report.bookmarks_read}")
    print(f"Duplicates removed: {report.duplicate_bookmarks_removed}")
    print(f"Bookmarks exported: {count_bookmarks(transformed)}")
    return 0


def import_ui(args: argparse.Namespace) -> int:
    if not args.yes_really_click_safari:
        print(
            "Refusing to drive Safari UI without --yes-really-click-safari.",
            file=sys.stderr,
        )
        return 2
    if not args.html_file.exists():
        print(f"HTML file not found: {args.html_file}", file=sys.stderr)
        return 1
    try:
        import_bookmarks_html(args.html_file)
    except SafariUIAutomationError as exc:
        print(str(exc), file=sys.stderr)
        print("Safari UI import did not complete.", file=sys.stderr)
        return 1
    print("Safari import automation completed.")
    return 0


def inspect_safari(args: argparse.Namespace) -> int:
    for item in read_top_level_items(args.safari_bookmarks):
        print(f"{item.index:02d} {item.bookmark_type} {item.title}")
    return 0


def prune_safari_top_level(args: argparse.Namespace) -> int:
    try:
        require_browsers_stopped(["Safari"])
    except BrowserRunningError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        removed = prune_top_level_items(args.safari_bookmarks, apply=args.apply)
    except SafariBookmarksAccessError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    action = "Removed" if args.apply else "Would remove"
    for item in removed:
        print(f"{action}: {item.index:02d} {item.bookmark_type} {item.title}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to prune top-level Safari items.")
    return 0


def delete_top_level_ui(args: argparse.Namespace) -> int:
    target_items = [
        item
        for item in read_top_level_items(args.safari_bookmarks)
        if item.title not in {"History", "BookmarksBar", "BookmarksMenu", "com.apple.ReadingList"}
    ]
    for item in target_items:
        print(f"Target row {item.index}: {item.title}")
    if not args.yes_really_click_safari:
        print("Dry run only. Re-run with --yes-really-click-safari to delete through Safari UI.")
        return 0
    print(
        "Refusing to run this UI deletion method: Safari's bookmark editor rows "
        "are visible through Accessibility, but row selection/manipulation hangs.",
        file=sys.stderr,
    )
    print("Delete top-level items manually in Safari, or use prune-safari-top-level --apply for local plist cleanup.", file=sys.stderr)
    return 2


def backup(args: argparse.Namespace) -> int:
    try:
        require_browsers_stopped()
    except BrowserRunningError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    result = create_backup(
        firefox_db=args.firefox_db,
        firefox_profile=args.firefox_profile,
        safari_bookmarks=args.safari_bookmarks,
        output_dir=args.output_dir,
    )
    print(f"Backup directory: {result.directory}")
    for path in result.files:
        print(f"Backed up: {path.name}")
    for skipped in result.skipped:
        print(f"Skipped: {skipped}", file=sys.stderr)
    if result.skipped:
        print("Some files could not be backed up; macOS Full Disk Access may be required.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
