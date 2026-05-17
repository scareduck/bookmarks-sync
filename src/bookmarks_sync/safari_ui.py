from __future__ import annotations

import subprocess
from pathlib import Path


class SafariUIAutomationError(RuntimeError):
    pass


def import_bookmarks_html(html_path: Path) -> None:
    script = _import_script(str(html_path))
    _run_osascript(script)


def delete_top_level_bookmark_items(row_indexes: list[int]) -> None:
    script = _delete_top_level_script(row_indexes)
    _run_osascript(script)


def _run_osascript(script: str) -> None:
    result = subprocess.run(
        ["osascript", "-e", script],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Safari UI automation failed."
        raise SafariUIAutomationError(message)


def _import_script(posix_path: str) -> str:
    escaped_path = posix_path.replace("\\", "\\\\").replace('"', '\\"')
    return f'''
set bookmarkFile to "{escaped_path}"

tell application "Safari"
    activate
end tell

tell application "System Events"
    if not (exists process "Safari") then error "Safari is not running."
    tell process "Safari"
        set frontmost to true
        delay 0.5
        if my clickImportCommand() is false then error "Could not find Safari's bookmarks import menu item."
        delay 0.8
        my clickChooseFileButton()
        delay 0.8
        keystroke "g" using {{command down, shift down}}
        delay 0.2
        keystroke bookmarkFile
        key code 36
        delay 0.4
        key code 36
    end tell
end tell

on clickImportCommand()
    tell application "System Events"
        tell process "Safari"
            set fileMenu to menu "File" of menu bar 1
            repeat with candidate in menu items of fileMenu
                set candidateName to name of candidate
                if candidateName contains "Import Browsing Data" then
                    click candidate
                    return true
                end if
            end repeat
            if exists menu item "Import Browsing Data from File or Folder…" of fileMenu then
                click menu item "Import Browsing Data from File or Folder…" of fileMenu
                return true
            end if
            if exists menu item "Import From" of fileMenu then
                set importMenu to menu "Import From" of menu item "Import From" of fileMenu
                repeat with candidate in menu items of importMenu
                    set candidateName to name of candidate
                    if candidateName contains "Bookmark" and candidateName contains "HTML" then
                        click candidate
                        return true
                    end if
                end repeat
            end if
            return false
        end tell
    end tell
end clickImportCommand

on clickChooseFileButton()
    tell application "System Events"
        tell process "Safari"
            repeat with safariWindow in windows
                repeat with candidate in buttons of safariWindow
                    set candidateName to name of candidate
                    if candidateName contains "Choose File" then
                        click candidate
                        return true
                    end if
                end repeat
            end repeat
            return false
        end tell
    end tell
end clickChooseFileButton
'''


def _delete_top_level_script(row_indexes: list[int]) -> str:
    apple_list = ", ".join(str(index) for index in sorted(row_indexes, reverse=True))
    return f'''
set targetRows to {{{apple_list}}}

tell application "Safari"
    activate
end tell

tell application "System Events"
    if not (exists process "Safari") then error "Safari is not running."
    tell process "Safari"
        set frontmost to true
        delay 0.5
        my openBookmarksEditor()
        delay 0.8
        repeat with targetRow in targetRows
            my deleteOutlineRow(targetRow as integer)
            delay 0.2
        end repeat
    end tell
end tell

on openBookmarksEditor()
    tell application "System Events"
        tell process "Safari"
            set bookmarksMenu to menu "Bookmarks" of menu bar 1
            if exists menu item "Show Bookmarks" of bookmarksMenu then
                click menu item "Show Bookmarks" of bookmarksMenu
            end if
            delay 0.2
            set bookmarksMenu to menu "Bookmarks" of menu bar 1
            if exists menu item "Show Bookmarks Editor" of bookmarksMenu then
                click menu item "Show Bookmarks Editor" of bookmarksMenu
            end if
        end tell
    end tell
end openBookmarksEditor

on deleteOutlineRow(rowIndex)
    tell application "System Events"
        tell process "Safari"
            set bookmarkOutline to my findFirstOutline(front window)
            if bookmarkOutline is missing value then error "Could not find Safari bookmarks outline."
            if rowIndex > (count of rows of bookmarkOutline) then return false
            set targetRow to row rowIndex of bookmarkOutline
            select targetRow
            delay 0.1
            key code 51
            delay 0.2
            my confirmDeleteIfNeeded()
        end tell
    end tell
end deleteOutlineRow

on findFirstOutline(rootElement)
    tell application "System Events"
        try
            if role of rootElement is "AXOutline" then return rootElement
        end try
        try
            repeat with childElement in UI elements of rootElement
                set foundElement to my findFirstOutline(childElement)
                if foundElement is not missing value then return foundElement
            end repeat
        end try
        return missing value
    end tell
end findFirstOutline

on confirmDeleteIfNeeded()
    tell application "System Events"
        tell process "Safari"
            repeat with safariWindow in windows
                if exists button "Delete" of safariWindow then
                    click button "Delete" of safariWindow
                    return true
                end if
            end repeat
            return false
        end tell
    end tell
end confirmDeleteIfNeeded
'''


def _quote_applescript(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
