from __future__ import annotations

import plistlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bookmarks_sync.backup import create_backup
from bookmarks_sync.bookmark_html import write_bookmarks_html
from bookmarks_sync.firefox_db import read_firefox_bookmarks
from bookmarks_sync.model import Bookmark, Folder, SyncReport
from bookmarks_sync.process_check import BrowserRunningError, require_browsers_stopped
from bookmarks_sync.safari_plist import (
    SafariBookmarksAccessError,
    build_safari_plist,
    prune_top_level_items,
    read_top_level_items,
    write_safari_bookmarks,
)
from bookmarks_sync.transform import transform_tree


class FirefoxDatabaseTests(unittest.TestCase):
    def test_reads_bookmarks_from_places_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "places.sqlite"
            self._create_firefox_db(db_path)

            root = read_firefox_bookmarks(db_path)

        self.assertEqual(root.title, "Firefox")
        self.assertEqual(root.folders[0].title, "Bookmarks Menu")
        self.assertEqual(root.folders[0].bookmarks[0].title, "Example")
        self.assertEqual(root.folders[0].bookmarks[0].url, "https://example.com/")

    @staticmethod
    def _create_firefox_db(db_path: Path) -> None:
        con = sqlite3.connect(db_path)
        try:
            con.executescript(
                """
                CREATE TABLE moz_places (
                    id INTEGER PRIMARY KEY,
                    url TEXT
                );
                CREATE TABLE moz_bookmarks (
                    id INTEGER PRIMARY KEY,
                    fk INTEGER,
                    type INTEGER NOT NULL,
                    parent INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    title TEXT,
                    guid TEXT NOT NULL
                );
                INSERT INTO moz_bookmarks VALUES (1, NULL, 2, 0, 0, NULL, 'root________');
                INSERT INTO moz_bookmarks VALUES (2, NULL, 2, 1, 0, NULL, 'menu________');
                INSERT INTO moz_places VALUES (10, 'https://example.com/');
                INSERT INTO moz_bookmarks VALUES (3, 10, 1, 2, 0, 'Example', 'bookmark1');
                """
            )
        finally:
            con.close()


class BackupTests(unittest.TestCase):
    def test_creates_backup_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            profile = root / "Firefox" / "Profiles" / "default"
            profile.mkdir(parents=True)
            db_path = profile / "places.sqlite"
            FirefoxDatabaseTests._create_firefox_db(db_path)
            profiles_ini = root / "Firefox" / "profiles.ini"
            profiles_ini.write_text("[Profile0]\nName=default\nIsRelative=1\nPath=Profiles/default\nDefault=1\n")
            safari_bookmarks = root / "Safari" / "Bookmarks.plist"
            safari_bookmarks.parent.mkdir()
            safari_bookmarks.write_bytes(plistlib.dumps({"old": True}))

            result = create_backup(
                firefox_profile=profile,
                safari_bookmarks=safari_bookmarks,
                output_dir=root / "backups",
            )

            names = {path.name for path in result.files}
            self.assertIn("firefox-places.sqlite", names)
            self.assertIn("firefox-profiles.ini", names)
            self.assertIn("safari-Bookmarks.plist", names)
            self.assertIn("manifest.json", names)
            self.assertEqual(result.skipped, [])


class BookmarkHtmlTests(unittest.TestCase):
    def test_writes_netscape_bookmark_html(self) -> None:
        root = Folder(
            title="Firefox",
            folders=[Folder(title="Bookmarks Menu", bookmarks=[Bookmark("A & B", "https://example.com/?a=1&b=2")])],
        )

        html = write_bookmarks_html(root)

        self.assertIn("<!DOCTYPE NETSCAPE-Bookmark-file-1>", html)
        self.assertIn("<H3>Bookmarks Menu</H3>", html)
        self.assertIn('HREF="https://example.com/?a=1&amp;b=2"', html)
        self.assertIn(">A &amp; B</A>", html)


class TransformTests(unittest.TestCase):
    def test_removes_local_and_global_duplicates(self) -> None:
        root = Folder(
            title="root",
            bookmarks=[
                Bookmark("First", "HTTPS://EXAMPLE.com/a"),
                Bookmark("Duplicate", "https://example.com/a"),
            ],
            folders=[Folder(title="child", bookmarks=[Bookmark("Again", "https://example.com/a")])],
        )
        report = SyncReport()

        transformed = transform_tree(root, global_dedupe=True, report=report)

        self.assertEqual(len(transformed.bookmarks), 1)
        self.assertEqual(len(transformed.folders[0].bookmarks), 0)
        self.assertEqual(report.duplicate_bookmarks_removed, 2)

    def test_denies_folders_and_url_substrings(self) -> None:
        root = Folder(
            title="root",
            folders=[
                Folder(title="Keep", bookmarks=[Bookmark("Good", "https://example.com/")]),
                Folder(title="Drop", bookmarks=[Bookmark("Bad", "https://bad.example/")]),
            ],
        )

        transformed = transform_tree(
            root,
            deny_folders=["Drop"],
            deny_url_substrings=["bad.example"],
        )

        self.assertEqual([folder.title for folder in transformed.folders], ["Keep"])


class SafariPlistTests(unittest.TestCase):
    def test_builds_safari_plist(self) -> None:
        root = Folder(title="From Firefox", bookmarks=[Bookmark("Example", "https://example.com/")])

        plist = build_safari_plist(root)

        child = plist["Children"][0]
        self.assertEqual(child["WebBookmarkType"], "WebBookmarkTypeLeaf")
        self.assertEqual(child["URLString"], "https://example.com/")
        self.assertEqual(child["URIDictionary"]["title"], "Example")

    def test_generated_plist_contains_only_source_tree(self) -> None:
        root = Folder(
            title="Firefox",
            folders=[Folder(title="Bookmarks Menu")],
            bookmarks=[Bookmark("Example", "https://example.com/")],
        )

        plist = build_safari_plist(root)

        titles = [item.get("Title") or item.get("URIDictionary", {}).get("title") for item in plist["Children"]]
        self.assertEqual(titles, ["Bookmarks Menu", "Example"])
        self.assertNotIn("Reading List", titles)
        self.assertNotIn("Imported", titles)

    def test_write_backs_up_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "Bookmarks.plist"
            destination.write_bytes(plistlib.dumps({"old": True}))

            backup = write_safari_bookmarks(
                Folder(title="From Firefox", bookmarks=[Bookmark("Example", "https://example.com/")]),
                destination,
            )

            self.assertTrue(Path(backup).exists())
            written = plistlib.loads(destination.read_bytes())
            self.assertEqual(written["Children"][0]["URLString"], "https://example.com/")

    def test_reads_top_level_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "Bookmarks.plist"
            destination.write_bytes(
                plistlib.dumps(
                    {
                        "Children": [
                            {"WebBookmarkType": "WebBookmarkTypeList", "Title": "BookmarksBar"},
                            {
                                "WebBookmarkType": "WebBookmarkTypeLeaf",
                                "URLString": "https://example.com/",
                                "URIDictionary": {"title": "Example"},
                            },
                        ]
                    }
                )
            )

            items = read_top_level_items(destination)

            self.assertEqual(items[0].title, "BookmarksBar")
            self.assertEqual(items[1].title, "Example")

    def test_prunes_non_system_top_level_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "Bookmarks.plist"
            destination.write_bytes(
                plistlib.dumps(
                    {
                        "Children": [
                            {"WebBookmarkType": "WebBookmarkTypeProxy", "Title": "History"},
                            {"WebBookmarkType": "WebBookmarkTypeList", "Title": "BookmarksBar"},
                            {"WebBookmarkType": "WebBookmarkTypeList", "Title": "Dogs"},
                            {
                                "WebBookmarkType": "WebBookmarkTypeLeaf",
                                "URLString": "https://example.com/",
                                "URIDictionary": {"title": "Example"},
                            },
                        ]
                    }
                )
            )

            removed = prune_top_level_items(destination, apply=True)
            remaining = read_top_level_items(destination)

            self.assertEqual([item.title for item in removed], ["Dogs", "Example"])
            self.assertEqual([item.title for item in remaining], ["History", "BookmarksBar"])

    def test_write_reports_backup_permission_error_without_replacing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "Bookmarks.plist"
            original = plistlib.dumps({"old": True})
            destination.write_bytes(original)

            with patch("bookmarks_sync.safari_plist.shutil.copy2", side_effect=PermissionError("blocked")):
                with self.assertRaises(SafariBookmarksAccessError):
                    write_safari_bookmarks(
                        Folder(title="From Firefox", bookmarks=[Bookmark("Example", "https://example.com/")]),
                        destination,
                    )

            self.assertEqual(destination.read_bytes(), original)


class ProcessCheckTests(unittest.TestCase):
    def test_raises_when_browser_is_running(self) -> None:
        with patch("bookmarks_sync.process_check.running_browsers", return_value=["Safari"]):
            with self.assertRaises(BrowserRunningError):
                require_browsers_stopped()


if __name__ == "__main__":
    unittest.main()
