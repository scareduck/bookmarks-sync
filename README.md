# bookmarks-sync

Small utility project for making Firefox → Safari bookmark migration less annoying.

## Goal

Treat Firefox as the source of truth, export bookmarks to HTML, then run a local script that:

- parses Firefox bookmark export HTML
- normalizes and deduplicates bookmarks
- optionally collapses or renames top-level folders
- emits a Safari-friendly HTML import file
- keeps all imported material inside a predictable container folder such as `From Firefox`

## Suggested workflow

1. Export bookmarks from Firefox to HTML.
2. Run the transformation script in this directory.
3. Import the generated HTML into Safari.
4. Clean up only the single imported wrapper folder if Safari insists on creating one.
