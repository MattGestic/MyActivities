# Resource skeleton

Copy this whole folder to `Resources/<Category>/<resource-name>/` to propose a new resource.

```bash
cp -r Resources/_new-resource Resources/Components/my-thing
```

Then:

1. Fill in `RESOURCE.md` completely. Any placeholder left in place fails R4.
2. Put the resource itself alongside it.
3. Put a minimal runnable example in `example/`.
4. **Run the example.** Record what actually came back under Verification. Not what you expect it to do.
5. Complete the intake record at the bottom of `RESOURCE.md` against R1 to R8.
6. Add the catalogue row in `Resources/README.md`.
7. Delete this file from your copy.

Criteria and rationale: [`Governance/04-resource-governance.md`](../../Governance/04-resource-governance.md).

**Before you start, check R7.** If the resource came out of client work — Skeena, Ausenco, P6 schedules, cost or tonnage data — assume it carries traces until you have checked sample data, test fixtures, default values, comments, and any committed example output. Strip or synthesise before intake, not after.
