# SlickGrid (vendored for the D-09 grid view)

| Item | Value |
|---|---|
| Package | `slickgrid` (the 6pac fork, no jQuery) |
| Version | 5.20.2 |
| Licence | MIT, see `LICENSE` (copied unmodified from the package) |
| Download URL | https://registry.npmjs.org/slickgrid/-/slickgrid-5.20.2.tgz |
| Tarball sha256 | `ca402b941bc6f1a5f0dc2f3e075f48aa273d5f7360751461a2f9143def8b18d8` |
| Registry integrity | `sha512-WexXtvKkXkaQWkLEszgs+3tjKweAULYW0ZMGT1JRFfrUis9IBGET6dQ7eS1wfFBao2go7U7Uj6uNrhhA9RiVMQ==` (sha1 `aa943a97d3bc4f1bffa43cce35f61a6c57dc17e4`) |
| Project | https://github.com/6pac/SlickGrid |
| Downloaded | 2026-09-27 |

## Files

`dist/` holds the package's own browser builds, byte for byte, taken from `package/dist/browser/` (and `package/dist/styles/css/` for the stylesheet). Only the subset the grid view uses is kept.

| File | From | sha256 |
|---|---|---|
| `dist/slick.core.js` | `dist/browser/slick.core.js` | `34fdd20ddbed9b988195cca89c7e234ca7f306ea272824080ad22aba18a63a96` |
| `dist/slick.interactions.js` | `dist/browser/slick.interactions.js` | `09f105b193ce300e9c3325df54a34960611bb8c10077da877bbad53a1a886df8` |
| `dist/slick.grid.js` | `dist/browser/slick.grid.js` | `30179ba19697311a8ff536aec4cfbb2cd0bbe4437482b097f065207fed4933f7` |
| `dist/slick.dataview.js` | `dist/browser/slick.dataview.js` | `021af46ecb7fc8799efa6537442b6290b7320438e0c6cea641f4a62e0c63f24a` |
| `dist/slick.checkboxselectcolumn.js` | `dist/browser/plugins/slick.checkboxselectcolumn.js` | `51d7d9829a44b2d9c786f7cc669f571c50e130f667845aaa92086cb7c8719e30` |
| `dist/slick.rowselectionmodel.js` | `dist/browser/plugins/slick.rowselectionmodel.js` | `4e5d8082b5ec6fca874e0dd134ea6ca27e17e15cd19708d35e3232ff11a6d0f1` |
| `dist/slick.grid.css` | `dist/styles/css/slick.grid.css` | `0e7cff2da3f989c945cc0fb739cc224768d207d388184dcfb10b57a58e535f4e` |
| `LICENSE` | `LICENSE` | `bfce12a8ee2abffdc3784453b1866112c31705ddc55ebf586faf24f75069737c` |

`slickgrid.subset.min.js` is the six JS files above, concatenated in the order listed and minified once. This is the file that gets inlined. It is the only transformed file, and it is reproducible:

```
cat dist/slick.core.js dist/slick.interactions.js dist/slick.grid.js dist/slick.dataview.js \
    dist/slick.checkboxselectcolumn.js dist/slick.rowselectionmodel.js > /tmp/sg-concat.js
npx -y esbuild@0.24.0 /tmp/sg-concat.js --minify --legal-comments=inline --outfile=slickgrid.subset.min.js
```

sha256 `57ee09f30f74cb51ad949b8a5cf25fa6ed9e28735fac5cc24f93e167528f71f9`, 217,423 bytes.

The package does not ship minified browser files, which is why this one step exists. esbuild is used at vendoring time only and never by the app. See `docs/decisions/D-09-grid-library.md` for the sign-off point this raises.

## Embedded in the app (P61, TD-221)

Where `docs/grid-view-integration.md` puts them:

- `slickgrid.subset.min.js` is in `<script id="vendor-slickgrid">`, immediately before `<script id="app-script">`. A `/* */` comment ahead of it holds the version line and the full text of `LICENSE`.
- `dist/slick.grid.css` is in `<style id="vendor-slickgrid-css">`, immediately after the main `</style>`.

**Both are embedded byte for byte. No `\x3C` escape was needed**, unlike SheetJS (TD-216). Checked before embedding:

- Neither file contains `</body>`, `<body>`, `<head>`, `</head>`, `<html>`, `</html>`, a script start or end tag, `</style` or `<!--`.
- The JS holds one tag-like literal, `'<style type="text/css" rel="stylesheet" />'`, in `createCssRulesAlternative()`. It is not on the list above. Inside a script it is plain text to the HTML parser. It only runs when the engine cannot create a stylesheet the normal way.

`tools/p61_check.py` asserts that each block carries its file unchanged, and that the page still holds exactly one of each tag the check tools inject against.

## Not included, on purpose

- `slick.editors.js`, `slick.formatters.js`: the wrapper has its own four native-input editors and formatter, so the date editor needs no third-party picker (the package's date editor needs Flatpickr).
- `slick-alpine-theme.css`, `slick-default-theme.css`: every colour comes from the app's `--color-*` roles in `src/modules/grid-view/grid-view.css`.
- SortableJS (the package's one dependency): only needed for drag column reorder, which is switched off (`enableColumnReorder:false`). SlickGrid only references it when that option is on.

## Updating

Download the new tarball, check its sha256 against the registry integrity, replace the `dist/` files, re-run the minify command, update every hash here, re-run `python3 tools/grid_view_assemble.py` and `python3 tools/grid_view_check.py`.
