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

## Known dead ends (macOS Sequoia / Safari 18)

### Destructive iCloud sync is not automatable

The goal of a full destructive Firefox → Safari sync (replacing all Safari
bookmarks and propagating to iCloud) is blocked by two hard constraints that
compound each other:

**iCloud overwrites local plist changes.** Writing Safari's `Bookmarks.plist`
directly (`sync --apply`) works for local-only Safari, but when iCloud bookmark
sync is active, iCloud treats its copy as authoritative. Opening Safari after a
plist write causes iCloud to push the cloud state back down, undoing the local
change. There is no supported way to signal iCloud that a local file write
should be treated as the new source of truth.

**Safari's bookmarks editor is inaccessible via Accessibility API.** Any
attempt to interact with rows in the bookmarks editor outline (select, click by
coordinate, etc.) hangs indefinitely in `osascript`. The AX actions are sent to
Safari but never return. This affects both `select targetRow` and `click at
{x, y}` derived from the row's own AX position properties. Keyboard-only
approaches and the sidebar were not fully explored but are unlikely to fare
better given that the underlying AX channel to that control appears blocked.

**`import-ui` only adds, never removes.** Even if deletion were solved,
Safari's File > Import Browsing Data appends to existing bookmarks. It provides
no way to replace them.

### Safari extensions have no bookmark API

Neither Safari Web Extensions (WebExtensions API) nor Safari App Extensions
(`SFSafariApplication`) expose any API for reading or writing bookmarks.
Apple's WebExtensions implementation omits `browser.bookmarks` entirely.
Private bookmark frameworks exist inside Safari but require entitlements Apple
does not grant to third parties.

### Summary

A fully automated destructive sync that propagates to iCloud would require
Apple to either (a) expose `browser.bookmarks` in Safari's WebExtensions
implementation, or (b) provide a supported CLI or API for Safari bookmark
management. Neither exists as of Sequoia. The best available option remains a
manual import: export HTML with `export-html`, then use Safari's File > Import
Browsing Data by hand.
