# ui-icons (`SRETIcons`)

The kit's inline SVG icon set (D-31). 24 by 24 stroke icons drawn with `currentColor`. No icon font, no network.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` |
| Status | Standalone (D-31 Stage A) |
| Global | `window.SRETIcons`, also `module.exports` |
| Requires | none |

## Interface

The header comment of `ui-icons.js` is the API reference: `svg(name, opts)`, `has(name)`, `names()`. An unknown name renders an empty box instead of throwing.

## Layout contract

| Rule | Value |
|---|---|
| Size | Takes the size its container gives `.ui-icon` (18 px default, 15 px small, via tokens). |
| Colour | Inherits the text colour. |
| Flex | Always `flex: none` inside rows, so it never shrinks. |

## Motion

None.

## Changelog

| Version | App version | Change |
|---|---|---|
| 0.1.0 | none (standalone) | First version, D-31 Stage A. |
