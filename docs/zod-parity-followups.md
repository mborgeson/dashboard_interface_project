# Zod parity follow-ups

The `check-zod-parity.sh` PostToolUse hook compares fields declared in `backend/app/schemas/*.py` to fields in the matching `src/lib/api/schemas/<stem>.ts`. Anything in the Pydantic schema but missing from Zod is silently dropped at parse time — Zod's default `z.object()` strips unknowns.

Survey run on 2026-04-29 against all 22 backend schema files identified four files with real drift. **All four have since been closed** — live parity check returns zero missing fields across `property.ts`, `reporting.ts`, `construction.ts`, and `deal.ts` as of 2026-04-29.

## Status

| Priority | File | Status | Closing commit |
|----------|------|--------|----------------|
| 1 | `property.ts` | ✅ Closed | `c65eaf9` — fix(schemas): add flat backendPropertySchema for PropertyResponse parity (#4) |
| 2 | `reporting.ts` | ✅ Closed | `bf78179` — fix(schemas): add Zod schemas for all reporting response classes (#5) |
| 3 | `construction.ts` | ✅ Closed | `e1df8f9` — fix(schemas): close construction.ts Zod parity gap (#3) |
| 4 | `deal.ts` sub-class artifacts | ✅ Closed | `a184058` — fix(schemas): close deal.ts sub-class artifact parity gaps (#6) |

To re-verify locally:

```bash
for stem in property reporting construction deal; do
  py_fields=$(grep -E '^[[:space:]]{4}[a-z][a-z0-9_]*:[[:space:]]' backend/app/schemas/${stem}.py \
    | sed -E 's/^[[:space:]]+([a-z][a-z0-9_]*):.*/\1/' \
    | grep -vE '^(model_config|class_config|_)' | sort -u)
  zod_fields=$(grep -E '^[[:space:]]+[a-z][a-z0-9_]*:[[:space:]]*z\.' src/lib/api/schemas/${stem}.ts \
    | sed -E 's/^[[:space:]]+([a-z][a-z0-9_]*):.*/\1/' | sort -u)
  echo "=== $stem ==="
  comm -23 <(printf '%s\n' "$py_fields") <(printf '%s\n' "$zod_fields")
done
```

## Hook limitation (open)

`check-zod-parity.sh` is regex-based: it grabs every indented `name: type` line in the `.py` file and checks against every Zod field in the `.ts` file, with no awareness of Pydantic class boundaries. That's why a single-file Pydantic module with multiple response classes can generate noise even when each class has its own (correctly-shaped) Zod counterpart — the hook concatenates fields across classes.

A future iteration could parse the AST (via Python `ast` module) and emit one diff per class. Out of scope for the parity-closure work, but worth logging here so the next person hitting hook noise has context.
