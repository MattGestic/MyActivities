# SheetJS (vendored for .xlsx import and export, TD-216 / D-23)

| Item | Value |
|---|---|
| Package | `xlsx` (SheetJS Community Edition) |
| Version | 0.18.5 |
| Build | `dist/xlsx.mini.min.js` (mini: XLSX/XLSM and CSV read and write; no legacy .xls, no codepage tables) |
| Licence | Apache-2.0, see `LICENSE` (copied unmodified from the package) |
| Download URL | https://registry.npmjs.org/xlsx/-/xlsx-0.18.5.tgz |
| Tarball sha256 | `5b23e25faa2472e50679e5f6ee52fced3ae4c4b1e46e8dfebb221c59747461ee` |
| Registry integrity | `sha512-dmg3LCjBPHZnQp5/F/+nnTa+miPJxUXB6vtk42YjBBKayDNagxGEeIdWApkYPOf3Z3pm3k62Knjzp7lMeTEtFQ==` |
| Project | https://sheetjs.com |
| Obtained | 2026-09-28. Supplied by Matt; byte-identical to the npm tarball's `package/dist/xlsx.mini.min.js` |

## Files

| File | From | sha256 |
|---|---|---|
| `xlsx.mini.min.js` | `package/dist/xlsx.mini.min.js` | `3120abba1fd0ea031f25ab22ac93e726f6f63467da1a6349b82e82f3df5d775c` |
| `LICENSE` | `package/LICENSE` | `4d2a38ac35cda06a555c84074a819d413339cd3691b822cae50f8f322fe01f64` |

Inlined into `<script id="vendor-sheetjs">`, the last element inside `<body>`, with the Apache-2.0 notice in a comment before it. It contains no `</script` and no script start tag.

**One change in the embedded copy, nothing else:** the library's HTML table-export template holds the literals `<html>`, `<head>`, `</head>`, `<body>` (one string) and `</body>`, `</html>` (another). Embedded as-is, the page would contain two `</body>`, and every check tool injects its probe with `replace("</body>", …)`, which put probe code inside the library's string and broke it. In the embedded copy the `<` of those six literals is written `\x3C`: the same string at runtime. `tools/d23_check.py` rebuilds the embedded text from this file with exactly that substitution and asserts it matches.

## Why mini, not full

Matt, 2026-09-28: mini unless the full build's extra functionality would be a benefit. Measured against the full build (same version) in Node:

- the reference export `data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx` reads identically
- `.xlsm` and CSV read identically, and mini's own `.xlsx` output reads back identically in full
- **legacy `.xls` (Excel 97-2003, BIFF8) does not read** in mini (`parse_xlscfb is not defined`). The app now says so and asks for `.xlsx` or CSV, rather than failing obscurely

The full build would add .xls and codepage support for about 630 KB more (882 KB against 251 KB). Switching is a file swap here plus the block in the app.

## Known issue: version

0.18.5 carries two published advisories, both in **reading** untrusted workbooks: CVE-2023-30533 (prototype pollution, fixed in 0.19.3) and CVE-2024-22363 (regular-expression denial of service, fixed in 0.20.2). This is the same version the app fetched from cdnjs before this change, so exposure is unchanged. The fixed releases are published only at `cdn.sheetjs.com`, which the build environment's proxy blocks. Upgrading is a drop-in replacement of `xlsx.mini.min.js` (and the block) once a fixed mini build is downloaded on a machine that can reach that host. Tracked in `docs/03-todo.md`.
