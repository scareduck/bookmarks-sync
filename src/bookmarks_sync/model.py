from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Bookmark:
    title: str
    url: str
    guid: str | None = None


@dataclass
class Folder:
    title: str
    folders: list["Folder"] = field(default_factory=list)
    bookmarks: list[Bookmark] = field(default_factory=list)
    guid: str | None = None


@dataclass
class SyncReport:
    folders_read: int = 0
    bookmarks_read: int = 0
    duplicate_bookmarks_removed: int = 0
    bookmarks_written: int = 0
    backup_path: str | None = None


def count_folders(root: Folder) -> int:
    return 1 + sum(count_folders(folder) for folder in root.folders)


def count_bookmarks(root: Folder) -> int:
    return len(root.bookmarks) + sum(count_bookmarks(folder) for folder in root.folders)
