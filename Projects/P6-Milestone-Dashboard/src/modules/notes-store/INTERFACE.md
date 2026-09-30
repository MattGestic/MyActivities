# SRETEntries: interface (P65, M1 store core + M2 migration)

`notes-store.js` is plain ES5/ES2017, no imports, no network. It sets
`window.SRETEntries` (or `globalThis` outside a browser) and `module.exports`
when defined. It reads and writes no app global.

Style: **pure functions over an array the caller owns and persists** (`ENTRIES`).
`create()` is a thin wrapper binding one array and one clock.

Tests: `node tools/notes_store_test.mjs`. Fixtures are real app output, rebuilt
with `python3 tools/p65_fixtures.py`.

## Entry (fixed contract)

```
{ eid:'E-0001', target:{kind:'ms'|'general'|'dep'|'row', key:string|null}, links:[ID],
  period:'YYYY-MM-DD', at:ISO, updatedAt:ISO, by:null,
  status:'note'|'open'|'sent'|'review'|'outstanding'|'done'|'closed',
  text:string, changes:{ <field>:{from, to} }, origin:'card'|'grid'|'notes'|'carried'|'mount:<file>'|string,
  followsUp:eid|null, nid?:'N-###', sig?:string, clearText?:true }
```

- `changes` fields: `actName start date weight floatD type marker` (the app's
  `MS_EDITABLE_FIELDS`), `health` (0-4), `progress` (int), and for `row`
  targets `rowHealth`, `rowRemark`. `to:null` is "back to the schedule / no override".
- `general`: `key` is always null, and `nid` is always set (assigned `N-###` when absent).
- `dep`: key is the `edgeKey()` string. `row`: key is the row ref.
- `clearText:true` (text always `''`) is an explicit "this remark is now cleared".
  It is never an empty entry, never coalesces, and nothing coalesces into it.
- `sig` is set only on migrated entries: a stable hash of kind, key, text and
  the `to` values (not period, not time), used for idempotent import.

## Constants

`SCHEMA_VERSION` (2), `KINDS`, `STATUSES`, `OPEN_STATUSES` (open, sent, review,
outstanding), `MS_FIELDS`, `CHANGE_FIELDS`, `DEFAULT_WINDOW_MS` (600000).

## Store core

| Signature | Returns | Notes |
|---|---|---|
| `append(entries, draft, ctx)` | the new entry, the entry it merged into, or `null` | `draft = {target, text?, changes?, clearText?, origin? ('card' default), links?, status?, followsUp?, by?, nid?, sig?}`. `ctx = {now? (ms, Date or ISO; default Date.now()), period, windowMs? (default 10 min), seq? (eid floor)}`. Fields whose `from` equals `to` are dropped. A non-general draft with no text and no change returns `null` and appends nothing. Default status: `note`, or `open` for `general`. |
| `edit(entries, eid, patch, ctx)` | `{ok:true, entry}` or `{ok:false, error, message}` | Never throws. Refused (`error:'period'`) unless `entry.period === ctx.period`. `patch` may carry `text, clearText, changes (replaces), links, status, followsUp, by`; `eid, target, at, period, origin, nid, sig` are refused (`error:'immutable'`). Sets `updatedAt`. |
| `remove(entries, eid)` | the removed entry or `null` | |
| `setStatus(entries, eids, status, ctx?)` | count changed | `pending` reads as `review`; an unknown status changes nothing. Bumps `updatedAt` (like `setNoteStatus`). |
| `rollup(entries, key, opts?)` | `{values, lastText, lastAt, count, openCount, byField}` | `opts = {kind? ('ms' default), period?}`. Latest wins per field, ordered by `at`, then eid number. `to:null` removes the field from `values` but is still the latest in `byField[f] = {eid, from, to, at}`. `lastText` is decided by the latest entry that has non-empty text or `clearText` (a clear gives `''`); `lastAt` the `at` of the latest entry. |
| `projectEntries(entries, sourceOf?)` | `{comments, health, progress, fields, depComments, rowOverrides, notes}` | Exact current store shapes. See below. |

### Coalescing (inside `append`)

Merges into the LATEST entry on the same target (kind and key) when all hold:
the draft and that entry both have `origin 'card'`; neither is a `clearText` entry; same `period`;
`0 <= ctx.now - updatedAt <= windowMs` (inclusive); and no text is lost (new
text empty, OR old text empty, OR new text starts with old text). Then: earlier
`from`, later `to`; fields whose merged `to` equals the original `from` drop
out; new text replaces old when non-empty; links union; `updatedAt` moves, `at`
does not. If the merge leaves no text and no change, the entry is **removed**
from `entries`, and the returned object satisfies `isEmptyEntry(e)`.
`general` targets never coalesce.

### Projection rules

- `comments[key]` = `rollup.lastText` of `ms` entries on `key`: the latest entry with non-empty text or `clearText` decides, and a clear leaves the key absent.
- `health[key]` whenever the latest health `to` is not null, **0 included**. No equal-to-source rule.
- `progress[key]` unless `sourceOf(key,'progress') != null` and equal (mirrors `saveMsDialog`).
- `fields[key][f]` unless equal to `sourceOf(key, f)`; an empty object is omitted.
- `USR-` keys are treated exactly like any other key (the app reads and writes their
  overrides through the same stores).
- `depComments[key]`: the same rule over `dep` entries, clears included.
- `rowOverrides[ref] = {health: rowHealth ?? null, remarks: rowRemark ?? ''}` when either is set.
- `notes`: every `general` entry, in array order, as `{nid, text, status, links, period, at, updatedAt}`.

`sourceOf(key, field)` returns the schedule's own value; omit it (or return
`undefined`) to store everything.

## Migration (P64 payloads, schemaVersion 1)

| Signature | Returns |
|---|---|
| `migrateLegacy(payload, opts?)` | array of NEW entries (pure) |
| `importLegacy(entries, payload, opts?)` | `{added, replaced, skipped, shortTitles, noteCollections}` (mutates `entries`) |

`opts = {origin?, period?, now?, weekEndingDay?, existing?}` (`existing` is for
`migrateLegacy` only; `importLegacy` passes its own array).

- Each milestone key's comment, health, progress and field overrides become ONE
  `ms` entry: `origin 'carried'`, `status 'note'`, every `from` null. Empty
  comments are not carried.
- Each note becomes a `general` entry keeping `nid, status (normalised: pending
  to review, unknown to open), links, period, at, updatedAt`; `origin` is
  `opts.origin || 'carried'`.
- Each non-empty `dependencyComments` value becomes a `dep` entry; each `overrides`
  row becomes a `row` entry (`rowHealth` when health is not null, `rowRemark`
  always). Both use `opts.origin || 'carried'` and text `''` for rows.
- `period` for ms, dep and row entries: the week ending on or after
  `payload.reportDate`, at `opts.weekEndingDay`, else the weekday of
  `payload.timeline.dates[0]` (published files), else Sunday (the app default).
  With no `reportDate`, `opts.period`.
- `at`/`updatedAt`: `payload.exportedAt || payload.publishedAt || opts.now`.
- Idempotent: an entry whose `sig` is already in `existing` is skipped; a note
  whose `nid` exists is skipped by `migrateLegacy` and, in `importLegacy`,
  **replaced in place** when it differs (the app's `applyNotes()` rule).
- Short titles and note collections are not entries: `importLegacy` returns them
  untouched for the caller's own `MS_SHORT_TITLES` / `NOTE_COLLECTIONS`.

## Persistence

| Signature | Returns |
|---|---|
| `serialize(entries)` | JSON string `{schemaVersion:2, entries}` |
| `deserialize(json)` | entries array. Accepts that string, a bare array or `{entries}`; drops invalid entries; `pending` reads as `review`; bad JSON gives `[]` |
| `validatePayload(p)` | `{ok, errors[], warnings[], schemaVersion}`. v1 (or missing) must carry a legacy annotation field; v2 must carry an `entries` array (unreadable or duplicate-eid entries warn); anything else errors |

## Convenience

`create({now?, seq?, entries?})` returns `{entries, append(draft, ctx), edit(eid, patch, ctx),
remove(eid), setStatus(eids, status, ctx), rollup(key, opts), project(sourceOf),
importLegacy(payload, opts), serialize()}`. `now` is a clock function or a fixed
time, filled into every `ctx` that has none; `seq` is an eid floor.

Helpers: `normStatus, weekEndISO(date, weekDay), isEmptyEntry, compare (the
latest-wins order), nextEid(entries, floor), sigFor(kind, key, text, changes)`.
