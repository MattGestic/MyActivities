# SheetJS (vendored for .xlsx import and export, TD-216 / D-23, upgraded TD-220)

| Item | Value |
|---|---|
| Package | `xlsx` (SheetJS Community Edition) |
| Version | 0.20.3 |
| Build | `dist/xlsx.mini.min.js` (mini: XLSX/XLSM and CSV read and write; no legacy .xls, no codepage tables) |
| Licence | Apache-2.0, see `LICENSE` (the Apache-2.0 text as shipped in the npm `xlsx@0.18.5` package; SheetJS CE is Apache-2.0 in both versions) |
| Source | Downloaded by Matt on 2026-09-28 from `https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.mini.min.js`. Fixed releases are published only at cdn.sheetjs.com (not npm), which the build environment cannot reach, so the file's hash below is recorded from the upload and could not be cross-checked against the host |
| Project | https://sheetjs.com |
| Replaced | 0.18.5 mini (P60), npm tarball sha256 `5b23e25faa2472e50679e5f6ee52fced3ae4c4b1e46e8dfebb221c59747461ee` |

## Files

| File | From | sha256 |
|---|---|---|
| `xlsx.mini.min.js` | `package/dist/xlsx.mini.min.js` (0.20.3) | `0cb353f830d7288385492c83d277b058ddeac664ca51cf1393aa1fd3e2b70939` |
| `LICENSE` | `package/LICENSE` | `4d2a38ac35cda06a555c84074a819d413339cd3691b822cae50f8f322fe01f64` |

Inlined into `<script id="vendor-sheetjs">`, the last element inside `<body>`, with the Apache-2.0 notice in a comment before it. It contains no `</script` and no script start tag.

**One change in the embedded copy, nothing else:** the library's HTML table-export template holds the literals `<html>`, `<head>`, `</head>`, `<body>` (one string) and `</body>`, `</html>` (another). Embedded as-is, the page would contain two `</body>`, and every check tool injects its probe with `replace("</body>", …)`, which put probe code inside the library's string and broke it. In the embedded copy the `<` of those six literals is written `\x3C`: the same string at runtime. `tools/d23_check.py` rebuilds the embedded text from this file with exactly that substitution and asserts it matches.

## Why mini, not full

Matt, 2026-09-28: mini unless the full build's extra functionality would be a benefit. Measured against the full build (same version) in Node:

- the reference export `data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx` reads identically
- `.xlsm` and CSV read identically, and mini's own `.xlsx` output reads back identically in full
- **legacy `.xls` (Excel 97-2003, BIFF8) does not read** in mini (`parse_xlscfb is not defined`). The app now says so and asks for `.xlsx` or CSV, rather than failing obscurely

The full build would add .xls and codepage support for about 630 KB more (882 KB against 251 KB). Switching is a file swap here plus the block in the app.

## Version history

- **0.18.5 (P60):** carried CVE-2023-30533 (prototype pollution, fixed 0.19.3) and CVE-2024-22363 (ReDoS, fixed 0.20.2), both when reading untrusted workbooks.
- **0.20.3 (P62, TD-220):** past both fixes. Measured against 0.18.5 on the reference export in Node: one cell differs, the "Activity ID" header, whose surrounding line breaks come back as `\n` instead of `\r\n`. The app trims header whitespace, and `tools/d23_check.py` confirms header detection, the Activity ID column and the row count through `Parse.workbook()`. Legacy `.xls` still fails with the same `parse_xlscfb` error, so the app's plain-language message still triggers. The same six HTML tag literals are escaped with `\x3C`.
