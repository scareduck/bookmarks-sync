from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .firefox_db import find_default_profile, find_places_db
from .safari_plist import default_safari_bookmarks


@dataclass(frozen=True)
class BackupResult:
    directory: Path
    files: list[Path]
    skipped: list[str]


def default_backup_root(home: Path | None = None) -> Path:
    home = home or Path.home()
    return home / "bookmarks-sync-backups"


def create_backup(
    *,
    firefox_db: Path | None = None,
    firefox_profile: Path | None = None,
    safari_bookmarks: Path | None = None,
    output_dir: Path | None = None,
) -> BackupResult:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = (output_dir or default_backup_root()) / timestamp
    destination.mkdir(parents=True, exist_ok=False)

    profile = firefox_profile or find_default_profile()
    db_path = firefox_db or find_places_db(profile)
    safari_path = safari_bookmarks or default_safari_bookmarks()

    copied: list[Path] = []
    skipped: list[str] = []
    _copy_optional(db_path, destination / "firefox-places.sqlite", copied, skipped)

    profiles_ini = profile.parent.parent / "profiles.ini"
    if profiles_ini.exists():
        _copy_optional(profiles_ini, destination / "firefox-profiles.ini", copied, skipped)

    if safari_path.exists():
        _copy_optional(safari_path, destination / "safari-Bookmarks.plist", copied, skipped)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "firefox_profile": str(profile),
        "firefox_db": str(db_path),
        "safari_bookmarks": str(safari_path),
        "files": [path.name for path in copied],
        "skipped": skipped,
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    copied.append(manifest_path)

    return BackupResult(directory=destination, files=copied, skipped=skipped)


def _copy_optional(source: Path, destination: Path, copied: list[Path], skipped: list[str]) -> None:
    try:
        shutil.copy2(source, destination)
    except PermissionError as exc:
        skipped.append(f"{source}: {exc}")
    else:
        copied.append(destination)
