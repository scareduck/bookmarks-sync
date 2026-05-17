from __future__ import annotations

from html import escape

from .model import Bookmark, Folder


def write_bookmarks_html(root: Folder) -> str:
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]
    for folder in root.folders:
        _write_folder(lines, folder, 1)
    for bookmark in root.bookmarks:
        _write_bookmark(lines, bookmark, 1)
    lines.append("</DL><p>")
    return "\n".join(lines) + "\n"


def _write_folder(lines: list[str], folder: Folder, depth: int) -> None:
    indent = "    " * depth
    lines.append(f"{indent}<DT><H3>{escape(folder.title)}</H3>")
    lines.append(f"{indent}<DL><p>")
    for child in folder.folders:
        _write_folder(lines, child, depth + 1)
    for bookmark in folder.bookmarks:
        _write_bookmark(lines, bookmark, depth + 1)
    lines.append(f"{indent}</DL><p>")


def _write_bookmark(lines: list[str], bookmark: Bookmark, depth: int) -> None:
    indent = "    " * depth
    title = escape(bookmark.title)
    url = escape(bookmark.url, quote=True)
    lines.append(f'{indent}<DT><A HREF="{url}">{title}</A>')
