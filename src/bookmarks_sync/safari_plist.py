from __future__ import annotations

import plistlib
import shutil
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from .model import Bookmark, Folder, count_bookmarks, count_folders


class SafariBookmarksAccessError(RuntimeError):
    pass


@dataclass(frozen=True)
class SafariTopLevelItem:
    index: int
    bookmark_type: str
    title: str


SAFARI_SYSTEM_TOP_LEVEL_TITLES = {
    "History",
    "BookmarksBar",
    "BookmarksMenu",
    "com.apple.ReadingList",
}


def default_safari_bookmarks(home: Path | None = None) -> Path:
    home = home or Path.home()
    return home / "Library" / "Safari" / "Bookmarks.plist"


def build_safari_plist(root: Folder) -> dict:
    """Build a Safari-style bookmark plist from a bookmark tree."""
    return {
        "WebBookmarkFileVersion": 1,
        "WebBookmarkType": "WebBookmarkTypeList",
        "Title": "Bookmarks",
        "Children": _children_to_safari(root),
    }


def read_top_level_items(path: Path) -> list[SafariTopLevelItem]:
    data = plistlib.loads(path.read_bytes())
    items: list[SafariTopLevelItem] = []
    for index, child in enumerate(data.get("Children", []), start=1):
        items.append(_top_level_item(index, child))
    return items


def prune_top_level_items(path: Path, *, apply: bool = False) -> list[SafariTopLevelItem]:
    """Remove non-system top-level Safari bookmark items from a plist."""
    try:
        data = plistlib.loads(path.read_bytes())
    except PermissionError as exc:
        raise SafariBookmarksAccessError(
            f"Cannot read Safari bookmarks: {path}. "
            "Grant Full Disk Access to the terminal/app running this command, then retry."
        ) from exc

    children = data.get("Children", [])
    kept = []
    removed = []
    for index, child in enumerate(children, start=1):
        item = _top_level_item(index, child)
        if item.title in SAFARI_SYSTEM_TOP_LEVEL_TITLES:
            kept.append(child)
        else:
            removed.append(item)

    if apply:
        backup_path = _backup_path(path)
        try:
            shutil.copy2(path, backup_path)
            data["Children"] = kept
            path.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))
        except PermissionError as exc:
            raise SafariBookmarksAccessError(
                f"Cannot update Safari bookmarks: {path}. "
                "Grant Full Disk Access to the terminal/app running this command, then retry."
            ) from exc

    return removed


def write_safari_bookmarks(root: Folder, destination: Path) -> str:
    """Back up and replace Safari's local bookmark plist."""
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise SafariBookmarksAccessError(
            f"Cannot create Safari bookmarks directory {destination.parent}: {exc}"
        ) from exc

    backup_path = _backup_path(destination)
    had_existing_file = destination.exists()
    if destination.exists():
        try:
            shutil.copy2(destination, backup_path)
        except PermissionError as exc:
            raise SafariBookmarksAccessError(
                f"Cannot read Safari bookmarks for backup: {destination}. "
                "Grant Full Disk Access to the terminal/app running this command, then retry."
            ) from exc

    data = plistlib.dumps(build_safari_plist(root), fmt=plistlib.FMT_BINARY)
    try:
        destination.write_bytes(data)
    except PermissionError as exc:
        raise SafariBookmarksAccessError(
            f"Cannot write Safari bookmarks: {destination}. "
            "Grant Full Disk Access to the terminal/app running this command, then retry."
        ) from exc
    return str(backup_path) if had_existing_file else ""


def preview(root: Folder) -> str:
    top_level_items = len(root.folders) + len(root.bookmarks)
    folders = max(count_folders(root) - 1, 0)
    return (
        f"Would replace Safari with {count_bookmarks(root)} bookmarks "
        f"across {folders} folders and {top_level_items} top-level items."
    )


def _folder_to_safari(folder: Folder) -> dict:
    return {
        "WebBookmarkType": "WebBookmarkTypeList",
        "Title": folder.title,
        "Children": _children_to_safari(folder),
    }


def _children_to_safari(folder: Folder) -> list[dict]:
    children = [_folder_to_safari(child) for child in folder.folders]
    children.extend(_bookmark_to_safari(bookmark) for bookmark in folder.bookmarks)
    return children


def _bookmark_to_safari(bookmark: Bookmark) -> dict:
    return {
        "WebBookmarkType": "WebBookmarkTypeLeaf",
        "URLString": bookmark.url,
        "URIDictionary": {"title": bookmark.title},
    }


def _top_level_item(index: int, child: dict) -> SafariTopLevelItem:
    title = child.get("Title") or child.get("URIDictionary", {}).get("title") or child.get("URLString") or ""
    return SafariTopLevelItem(
        index=index,
        bookmark_type=child.get("WebBookmarkType", ""),
        title=title,
    )


def _backup_path(destination: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return destination.with_name(f"{destination.name}.{timestamp}.bak")
