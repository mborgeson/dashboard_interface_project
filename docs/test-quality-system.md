# Test quality system

A coordinated set of Claude Code automations covering the full testing lifecycle for the dashboard_interface_project: evaluation, design, implementation, review, and durable solutions.

## Components at a glance

| Component | Type | Purpose | Where it lives |
|-----------|------|---------|----------------|
| `test-architect` | Agent (subagent) | Senior strategist — evaluates posture, reviews failures, designs solutions, delegates work | `.claude/agents/test-architect.md` |
| `test-engineer` | Agent (subagent) | Implementer — writes/refactors tests, runs them, opens PRs | `.claude/agents/test-engineer.md` |
| `/test-triage` | Skill | Playbook for high-failure-rate triage (50%+ red) | `.claude/skills/test-triage/SKILL.md` |
| `/test-posture-review` | Skill | Quarterly review of coverage, reliability, gates, runtime | `.claude/skills/test-posture-review/SKILL.md` |
| `validate-workflow.sh` | Hook | PostToolUse on `.github/workflows/*.yml` — YAML syntax + actionlint | `.claude/hooks/validate-workflow.sh` (committed) |
| settings.json wire-up | Hook config | Wires `validate-workflow.sh` into PostToolUse Write\|Edit | `.claude/settings.json` (committed) |

## How the pieces fit together

```
                       ┌─────────────────────────────┐
                       │  CI / dev shows failures    │
                       └──────────────┬──────────────┘
                                      │
                                      ▼
                  ┌───────────────────────────────────┐
                  │   /test-triage  (skill / playbook)│
                  └──────────────┬────────────────────┘
                                 │ pulls artifacts, clusters errors
                                 ▼
                       ┌───────────────────────┐
                       │     test-architect    │ ← thinks, doesn't edit
                       │   (subagent, lifecycle) │
                       └─────┬─────────┬───────┘
                             │         │
              implementation │         │ documentation
                             ▼         ▼
                   ┌────────────────┐  ┌─────────────────────┐
                   │  test-engineer │  │ documentation-expert │
                   │  (subagent)    │  │  (built-in subagent) │
                   └────────────────┘  └─────────────────────┘
                             │
                             ▼
                       new branch + PR
```

`/test-posture-review` runs orthogonally — quarterly or pre-release, it produces a coverage / reliability / gate report that feeds into `test-architect`'s strategic backlog.

`validate-workflow.sh` runs automatically (no Claude action required) whenever a `.yml` under `.github/workflows/` is edited, catching syntax issues before CI sees them.

## When to invoke what

- **Test run is mostly red (50%+ failures)** → `/test-triage <PR>`. Walks you through artifact pull → error clustering → root-cause hypothesis. Output feeds `test-architect`.
- **Quarterly health check** → `/test-posture-review`. Produces a structured posture report.
- **Need test code written/fixed** → `Agent(subagent_type="test-engineer", ...)` directly, OR let `test-architect` delegate.
- **Need test strategy or root-cause review** → `Agent(subagent_type="test-architect", ...)`.
- **Workflow file edit** → no manual action; `validate-workflow.sh` runs automatically.

## Bootstrapping for new collaborators

The agent and skill files live under `.claude/agents/` and `.claude/skills/`, both of which are gitignored (the project's `.claude/` is treated as personal artifacts, same pattern as `.claude/scripts/` per [docs/claude-code-setup.md](claude-code-setup.md)). The hook script and settings.json wire-up **are** committed.

To get the same agents and skills locally:

1. Create the four files using the templates in the **Templates** section below.
2. Restart Claude Code (so the agents and skills get picked up).
3. Verify with `bash -n .claude/hooks/validate-workflow.sh` (syntax check) and by listing skills in any conversation — `/test-triage` and `/test-posture-review` should appear.

## Conventions reflected in the system

These are the assumptions the agents and skills are built on. If any drift, update the agent/skill files to match:

- Backend: pytest, SQLite in-memory unit tests, postgres-on-CI integration, parallel via `-n auto`
- Frontend: vitest, colocated tests or `__tests__/` subfolder, fixture factories like `makeBackendDeal`
- E2E: Playwright, `e2e/`, 4 workers in CI, 30s test timeout, `data-testid` > role > text for locators
- Mandates from CLAUDE.md: extraction logic, financial calcs, API endpoints, Zod schemas
- Workflow rot patterns to watch: `continue-on-error: true`, `||` masking, deprecated Node 20 actions, requirements drift

## Templates

> Copy these into the corresponding paths under `.claude/`. The hook script and settings update are already in this PR.

### `.claude/agents/test-architect.md`

```markdown
---
name: test-architect
description: Senior test strategist for the dashboard_interface_project. Use proactively when (a) test failures spike, (b) test coverage gaps are suspected, (c) a new feature is being designed and needs a test plan, or (d) CI gates need rethinking. Evaluates testing posture across the full lifecycle, reviews failing test runs, identifies root causes vs symptoms, and designs long-lasting solutions. Delegates implementation to test-engineer and write-ups to documentation-expert. Read-leaning.
tools: Read, Grep, Glob, Bash, Agent
---

[full body — see .claude/agents/test-architect.md in your local checkout]
```

### `.claude/agents/test-engineer.md`

```markdown
---
name: test-engineer
description: Implementation specialist for tests in the dashboard_interface_project. Use when test-architect (or the user) needs concrete code: writing new tests, refactoring brittle tests, fixing specific failures. Knows project conventions (vitest, pytest, Playwright). Operates with edit access — actually changes files, runs tests, commits to its own branches.
tools: Read, Write, Edit, MultiEdit, Bash, Grep, Glob
---

[full body — see .claude/agents/test-engineer.md in your local checkout]
```

### Skill files

The `/test-triage` and `/test-posture-review` skill files are too long to paste cleanly here — see the originals in `.claude/skills/test-triage/SKILL.md` and `.claude/skills/test-posture-review/SKILL.md` on the originating workstation.

## Related

- [docs/claude-code-setup.md](claude-code-setup.md) — wrapper script bootstrap (postgres, firecrawl, github MCP)
- [docs/zod-parity-followups.md](zod-parity-followups.md) — Zod parity backlog (closed)
- `.claude/hooks/` — full set of project hooks (protect-paths, auto-format, check-zod-parity, nudge-migration, async test-runner, session-status, **validate-workflow**)
