Build a Python CLI tool for destructively syncing Firefox bookmarks into Safari on macOS.

Requirements:

- Python 3.12+
- Use only the standard library unless a third-party dependency is clearly justified
- Input: Firefox profile `places.sqlite`
- Output: Safari `Bookmarks.plist`
- Modify Safari storage directly only after explicit `--apply`
- Do not automate browsers or call private iCloud APIs
- Keep code readable and boring
- Prefer dry-run previews and hard preflight failures over convenience
- Treat Firefox as authoritative. Do not preserve Safari-only special sections.
- Direct plist writes are local-only/experimental because they may not trigger
  iCloud sync. Prefer Safari-originated import/automation for iCloud experiments.

Core features:

1. Read Firefox bookmarks directly from the local database
   - discover the default profile from `profiles.ini`
   - refuse to read while Firefox is running
   - copy `places.sqlite` to a temporary snapshot before querying
   - reconstruct the bookmark tree from `moz_bookmarks` and `moz_places`

2. Force clean browser state
   - refuse to run when Firefox is running
   - refuse to run when Safari is running
   - provide a clear error telling the user what to quit

3. Convert bookmarks into an internal tree structure
   - folders
   - bookmarks
   - optional metadata if available

4. Normalize bookmarks
   - trim whitespace
   - normalize folder names
   - canonicalize URLs conservatively
   - preserve original title if possible

5. Deduplicate
   - duplicate bookmarks by URL within the same folder
   - optional global dedupe mode
   - keep the first non-empty title unless a later one is clearly better

6. Safari/iCloud write path
   - write Safari-compatible bookmark plist data
   - back up the existing Safari `Bookmarks.plist` before replacement
   - destructive writes require `--apply`
   - replace Safari bookmark contents wholesale; Safari-only sections can go
   - do not assume direct plist writes propagate to iCloud

7. Safari import/UI automation path
   - generate Netscape bookmark HTML from the transformed tree
   - optionally drive Safari's own import UI with explicit user opt-in
   - keep UI automation fenced behind obvious flags and clear warnings

8. Filtering
   - optional folder allowlist
   - optional folder denylist
   - optional URL substring denylist

9. Reporting
   - dry-run mode
   - print counts for folders read, bookmarks read, duplicates removed, folders renamed, bookmarks written

10. Tests
   - add unit tests for reading small synthetic Firefox databases
   - add tests for dedupe and folder filtering
   - add tests for process refusal logic
   - add tests for Safari plist generation without touching real Safari data

CLI shape:

- `python -m bookmarks_sync sync`
- `python -m bookmarks_sync export-html output.html`
- `python -m bookmarks_sync import-ui output.html --yes-really-click-safari`
- options:
  - `--firefox-db /path/to/places.sqlite`
  - `--firefox-profile /path/to/profile`
  - `--safari-bookmarks /path/to/Bookmarks.plist`
  - `--allow-folder Foo`
  - `--deny-folder Bar`
  - `--deny-url-substring example.com`
  - `--global-dedupe`
  - `--dry-run`
  - `--apply`

Project layout:

- `pyproject.toml`
- `src/bookmarks_sync/__init__.py`
- `src/bookmarks_sync/cli.py`
- `src/bookmarks_sync/firefox_db.py`
- `src/bookmarks_sync/model.py`
- `src/bookmarks_sync/process_check.py`
- `src/bookmarks_sync/safari_plist.py`
- `src/bookmarks_sync/transform.py`
- `tests/`

Implementation notes:

- Firefox bookmarks are in `places.sqlite`
- Safari bookmarks are stored locally in a plist that iCloud sync may propagate
- keep transformations deterministic
- add docstrings and type hints
- include a sample command in README
