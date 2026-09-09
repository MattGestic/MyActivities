# [Resource Name]

**Category:** [Components / Templates / Snippets]
**Version:** 1.0.0
**Owner:** [Name]
**Added:** [YYYY-MM-DD]
**Last reviewed:** [YYYY-MM-DD]
**Status:** [Active / Stale / Retired]

## Purpose

[One or two sentences. What it does and what problem it removes. Not how it works.]

## When to use it

[The specific situation this is the right answer to.]

## When not to use it

[The adjacent situation where it is the wrong answer. If this section is empty, R6 has not been done properly.]

## Inputs

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| [name] | [type] | [Y/N] | [default] | [notes] |

## Outputs

| Name | Type | Notes |
|---|---|---|
| [name] | [type] | [notes] |

## Dependencies

| Dependency | Version | Why | Optional |
|---|---|---|---|
| [none] | — | — | — |

[State explicitly if there are none. State explicitly if a build step is required.]

## Integration

```
[Minimal copy-paste integration. Real code, not pseudocode.]
```

Steps:
1. [step]
2. [step]

## Working example

Location: `example/`

```
[The minimal example, or the command to run it.]
```

## Verification

**This section records an actual run, not an intention.**

| Date | What was run | Environment | Result |
|---|---|---|---|
| [YYYY-MM-DD] | [command or action] | [browser/runtime/version] | [what actually came back] |

## Known limitations

[Explicit list. Edge cases, scope boundaries, things deliberately not handled.]

[A resource with "no known limitations" fails R6 — it means nobody looked.]

## Licence and attribution

| Source | Licence | Notes |
|---|---|---|
| Original work | — | — |

## Changelog

| Version | Date | Change | Breaking |
|---|---|---|---|
| 1.0.0 | [date] | Initial intake | — |

## Known copies in projects

[Projects holding a copy, so a breaking change can be propagated deliberately. There is no automatic propagation.]

| Project | Branch | Version held |
|---|---|---|
| [none] | — | — |

---

## Intake record

All mandatory criteria must pass. See `Governance/04-resource-governance.md`.

| # | Criterion | Result | Evidence / what was changed to pass |
|---|---|---|---|
| R1 | Genuinely reusable | [Pass/Fail] | [named second use case, or the two projects using it] |
| R2 | No project coupling | [Pass/Fail] | [what was parameterised out] |
| R3 | Self-contained | [Pass/Fail] | [dependencies declared and pinned] |
| R4 | Documented | [Pass/Fail] | [this file complete, no placeholders left] |
| R5 | Demonstrated | [Pass/Fail] | [the run recorded under Verification] |
| R6 | Limits stated | [Pass/Fail] | [limitations section populated] |
| R7 | Clean of sensitive content | [Pass/Fail] | [what was stripped or synthesised — sample data, fixtures, defaults, comments, example outputs] |
| R8 | Licence-safe | [Pass/Fail] | [licence recorded, attribution present] |

**Advisory** (not blocking, recorded for the catalogue):

| # | Criterion | Met |
|---|---|---|
| A1 | Has automated tests | [Y/N] |
| A2 | Works standalone, no build step | [Y/N] |
| A3 | Theme-aware or style-agnostic | [Y/N/NA] |
| A4 | Accessible (keyboard, contrast, semantics) | [Y/N/NA] |

**Admitted by:** [Name] · **Date:** [YYYY-MM-DD]
