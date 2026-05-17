from __future__ import annotations

from dataclasses import replace
from urllib.parse import urlsplit, urlunsplit

from .model import Bookmark, Folder, SyncReport


def transform_tree(
    root: Folder,
    *,
    allow_folders: list[str] | None = None,
    deny_folders: list[str] | None = None,
    deny_url_substrings: list[str] | None = None,
    global_dedupe: bool = False,
    report: SyncReport | None = None,
) -> Folder:
    allow = {_normalize_name(name) for name in allow_folders or []}
    deny = {_normalize_name(name) for name in deny_folders or []}
    denied_urls = deny_url_substrings or []
    seen_global: set[str] = set()

    transformed = _transform_folder(
        root,
        allow=allow,
        deny=deny,
        denied_urls=denied_urls,
        global_dedupe=global_dedupe,
        seen_global=seen_global,
        is_root=True,
        report=report,
    )
    return transformed or Folder(title=_normalize_name(root.title) or "Firefox")


def _transform_folder(
    folder: Folder,
    *,
    allow: set[str],
    deny: set[str],
    denied_urls: list[str],
    global_dedupe: bool,
    seen_global: set[str],
    is_root: bool,
    report: SyncReport | None,
) -> Folder | None:
    title = _normalize_name(folder.title)
    if not is_root and title in deny:
        return None

    local_seen: set[str] = set()
    bookmarks: list[Bookmark] = []
    for bookmark in folder.bookmarks:
        normalized = _normalize_bookmark(bookmark)
        if any(fragment in normalized.url for fragment in denied_urls):
            continue
        key = normalized.url
        if key in local_seen or (global_dedupe and key in seen_global):
            if report:
                report.duplicate_bookmarks_removed += 1
            continue
        local_seen.add(key)
        seen_global.add(key)
        bookmarks.append(normalized)

    folders: list[Folder] = []
    for child in folder.folders:
        transformed = _transform_folder(
            child,
            allow=allow,
            deny=deny,
            denied_urls=denied_urls,
            global_dedupe=global_dedupe,
            seen_global=seen_global,
            is_root=False,
            report=report,
        )
        if transformed is not None:
            folders.append(transformed)

    if allow and not is_root and title not in allow and not folders:
        return None

    return Folder(title=title or "Firefox", folders=folders, bookmarks=bookmarks, guid=folder.guid)


def _normalize_bookmark(bookmark: Bookmark) -> Bookmark:
    title = _normalize_name(bookmark.title) or bookmark.url.strip()
    return replace(bookmark, title=title, url=_normalize_url(bookmark.url))


def _normalize_name(name: str) -> str:
    return " ".join(name.split())


def _normalize_url(url: str) -> str:
    stripped = url.strip()
    parts = urlsplit(stripped)
    if parts.scheme in {"http", "https"}:
        netloc = parts.netloc.lower()
        return urlunsplit((parts.scheme.lower(), netloc, parts.path, parts.query, parts.fragment))
    return stripped
