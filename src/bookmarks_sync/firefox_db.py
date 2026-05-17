from __future__ import annotations

import configparser
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .model import Bookmark, Folder

BOOKMARK_TYPE = 1
FOLDER_TYPE = 2
SPECIAL_FOLDER_TITLES = {
    "root________": "Firefox",
    "menu________": "Bookmarks Menu",
    "toolbar_____": "Bookmarks Toolbar",
    "unfiled_____": "Other Bookmarks",
    "mobile______": "Mobile Bookmarks",
}
IGNORED_FOLDER_GUIDS = {"tags________"}


@dataclass(frozen=True)
class FirefoxBookmarkRow:
    id: int
    parent: int
    type: int
    title: str
    position: int
    guid: str
    url: str | None


def default_firefox_root(home: Path | None = None) -> Path:
    home = home or Path.home()
    return home / "Library" / "Application Support" / "Firefox"


def find_default_profile(firefox_root: Path | None = None) -> Path:
    firefox_root = firefox_root or default_firefox_root()
    profiles_ini = firefox_root / "profiles.ini"
    parser = configparser.ConfigParser()
    if not parser.read(profiles_ini):
        raise FileNotFoundError(f"Could not read Firefox profiles file: {profiles_ini}")

    sections = [section for section in parser.sections() if section.startswith("Profile")]
    default_sections = [section for section in sections if parser.get(section, "Default", fallback="0") == "1"]
    candidates = default_sections or sections
    if not candidates:
        raise FileNotFoundError(f"No Firefox profiles found in {profiles_ini}")

    section = candidates[0]
    profile_path = Path(parser.get(section, "Path"))
    if parser.get(section, "IsRelative", fallback="1") == "1":
        profile_path = firefox_root / profile_path
    return profile_path


def find_places_db(profile: Path | None = None) -> Path:
    profile = profile or find_default_profile()
    db_path = profile / "places.sqlite"
    if not db_path.exists():
        raise FileNotFoundError(f"Firefox database not found: {db_path}")
    return db_path


def read_firefox_bookmarks(db_path: Path) -> Folder:
    """Read Firefox bookmarks from a snapshot copy of places.sqlite."""
    with tempfile.TemporaryDirectory(prefix="bookmarks-sync-") as tmpdir:
        snapshot = Path(tmpdir) / "places.sqlite"
        shutil.copy2(db_path, snapshot)
        return _read_snapshot(snapshot)


def _read_snapshot(db_path: Path) -> Folder:
    con = sqlite3.connect(db_path)
    try:
        rows = [
            FirefoxBookmarkRow(*row)
            for row in con.execute(
                """
                SELECT b.id,
                       b.parent,
                       b.type,
                       COALESCE(b.title, ''),
                       b.position,
                       b.guid,
                       p.url
                  FROM moz_bookmarks b
             LEFT JOIN moz_places p ON p.id = b.fk
                 WHERE b.type IN (?, ?)
              ORDER BY b.parent, b.position, b.id
                """,
                (BOOKMARK_TYPE, FOLDER_TYPE),
            )
        ]
    finally:
        con.close()

    folders_by_id: dict[int, Folder] = {}
    folder_rows: dict[int, FirefoxBookmarkRow] = {}
    child_rows: dict[int, list[FirefoxBookmarkRow]] = {}

    for row in rows:
        child_rows.setdefault(row.parent, []).append(row)
        if row.type == FOLDER_TYPE:
            title = _folder_title(row)
            folders_by_id[row.id] = Folder(title=title, guid=row.guid)
            folder_rows[row.id] = row

    root_id = _choose_root_id(folder_rows)
    if root_id is None:
        return Folder(title="Firefox")

    root = folders_by_id[root_id]
    _fill_folder(root_id, root, child_rows, folders_by_id)
    return root


def _fill_folder(
    folder_id: int,
    folder: Folder,
    child_rows: dict[int, list[FirefoxBookmarkRow]],
    folders_by_id: dict[int, Folder],
) -> None:
    for row in child_rows.get(folder_id, []):
        if row.guid in IGNORED_FOLDER_GUIDS:
            continue
        if row.type == FOLDER_TYPE:
            child = folders_by_id[row.id]
            _fill_folder(row.id, child, child_rows, folders_by_id)
            folder.folders.append(child)
        elif row.type == BOOKMARK_TYPE and row.url:
            folder.bookmarks.append(
                Bookmark(
                    title=_clean_title(row.title) or row.url,
                    url=row.url.strip(),
                    guid=row.guid,
                )
            )


def _choose_root_id(folder_rows: dict[int, FirefoxBookmarkRow]) -> int | None:
    roots = [row for row in folder_rows.values() if row.parent == 0]
    if roots:
        return sorted(roots, key=lambda row: (row.position, row.id))[0].id
    if folder_rows:
        return sorted(folder_rows)[0]
    return None


def _clean_title(title: str) -> str:
    return " ".join(title.split())


def _folder_title(row: FirefoxBookmarkRow) -> str:
    return SPECIAL_FOLDER_TITLES.get(row.guid) or _clean_title(row.title) or _fallback_folder_title(row.guid, row.id)


def _fallback_folder_title(guid: str, row_id: int) -> str:
    return guid or f"Folder {row_id}"
