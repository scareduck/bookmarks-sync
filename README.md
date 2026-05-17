# bookmarks-sync

Destructive Firefox -> Safari bookmark sync for macOS.

## Goal

Treat Firefox as the source of truth and read its local `places.sqlite`
database. The original direct-plist writer works for local Safari, but does not
reliably trigger iCloud bookmark sync. The newer experimental path exports a
Safari import HTML file and can ask Safari to import it through its own UI.

This is a full replacement sync. Safari special sections, imported wrappers, and
other destination-only bookmark structures are intentionally not preserved.

## Safety rules

- Firefox and Safari must both be stopped before source or destination data is read.
- The Firefox database is copied to a temporary snapshot before SQLite reads begin.
- Safari's `Bookmarks.plist` is backed up before replacement.
- The command defaults to dry-run behavior. Use `--apply` to write Safari data.
- Destination-only Safari bookmark sections are removed by design.
- The tool does not call private iCloud APIs.
- Direct plist sync is local-only/experimental; prefer the HTML + Safari UI path
  when iCloud propagation matters.

## Current workflow

Preview what would be synced:

```sh
bookmarks-sync sync --dry-run
```

Create a timestamped backup bundle:

```sh
bookmarks-sync backup
```

Export transformed Firefox bookmarks as Safari import HTML:

```sh
bookmarks-sync export-html /tmp/bookmarks-sync-safari-import.html
```

Ask Safari to import that HTML file through its UI. This requires macOS
Accessibility permission for the app or terminal running the command:

```sh
bookmarks-sync import-ui /tmp/bookmarks-sync-safari-import.html --yes-really-click-safari
```

Write Safari bookmarks directly after reviewing the preview. This updates local
Safari, but may not propagate to iCloud:

```sh
bookmarks-sync sync --apply
```

Use `--firefox-db` and `--safari-bookmarks` to point at explicit files while
developing or testing.
