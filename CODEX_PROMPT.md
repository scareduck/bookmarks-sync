Build a small Python CLI tool for transforming Firefox bookmark export HTML into a cleaner Safari import HTML file.

Requirements:

- Python 3.12+
- Use only the standard library unless a third-party dependency is clearly justified
- Input: Firefox bookmarks HTML export file
- Output: cleaned bookmarks HTML file that Safari can import
- Do not modify Safari storage directly
- Do not automate browsers
- Keep code readable and boring

Core features:

1. Parse Firefox bookmarks export HTML into an internal tree structure
   - folders
   - bookmarks
   - optional metadata if available

2. Normalize bookmarks
   - trim whitespace
   - normalize folder names
   - canonicalize URLs conservatively
   - preserve original title if possible

3. Deduplicate
   - duplicate bookmarks by URL within the same folder
   - optional global dedupe mode
   - keep the first non-empty title unless a later one is clearly better

4. Container folder support
   - write all output under a single top-level folder, default `From Firefox`

5. Filtering
   - optional folder allowlist
   - optional folder denylist
   - optional URL substring denylist

6. Reporting
   - dry-run mode
   - print counts for folders read, bookmarks read, duplicates removed, folders renamed, bookmarks written

7. Output
   - generate valid Netscape bookmark HTML format compatible with Safari import

8. Tests
   - add unit tests for parsing small sample inputs
   - add tests for dedupe and folder filtering

CLI shape:

- `python -m bookmarks_sync transform input.html output.html`
- options:
  - `--container "From Firefox"`
  - `--allow-folder Foo`
  - `--deny-folder Bar`
  - `--deny-url-substring example.com`
  - `--global-dedupe`
  - `--dry-run`

Project layout:

- `pyproject.toml`
- `src/bookmarks_sync/__init__.py`
- `src/bookmarks_sync/cli.py`
- `src/bookmarks_sync/model.py`
- `src/bookmarks_sync/parser.py`
- `src/bookmarks_sync/transform.py`
- `src/bookmarks_sync/writer.py`
- `tests/`

Implementation notes:

- Firefox export HTML is based on the classic Netscape bookmarks format
- use `html.parser` from stdlib if practical
- keep transformations deterministic
- add docstrings and type hints
- include a sample command in README
