from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Bookmark:
    title: str
    url: str


@dataclass
class Folder:
    title: str
    folders: list["Folder"] = field(default_factory=list)
    bookmarks: list[Bookmark] = field(default_factory=list)
