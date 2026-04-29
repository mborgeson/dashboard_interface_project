# Claude Code setup

This repo uses Claude Code (`claude.ai/code`). The committed `.mcp.json` references a few MCP servers that need per-developer wrapper scripts living under `.claude/scripts/` to keep secrets out of git.

`.claude/` is globally gitignored, so the wrapper scripts are **not** in the repo. New collaborators must create them locally before the affected MCP servers will start.

## Required wrapper scripts

`.mcp.json` expects these scripts to exist at runtime:

| Server | Script | Reads from |
|--------|--------|------------|
| `postgres` | `.claude/scripts/postgres-mcp.sh` | `DATABASE_URL` in `.env` |
| `firecrawl` | `.claude/scripts/firecrawl-mcp.sh` | `FIRECRAWL_API_KEY` in `.env` |
| `github` | `.claude/scripts/github-mcp.sh` | `gh auth token` (run `gh auth login` first) |

Each script reads its credential at process start, exports it (or passes as arg), and `exec`s the underlying `npx -y @modelcontextprotocol/server-*` binary.

## Bootstrapping

1. Copy `.env.example` → `.env` and fill in `DATABASE_URL`, `FIRECRAWL_API_KEY`, etc.
2. Run `gh auth login` so the github wrapper can pull a token.
3. Create the three scripts under `.claude/scripts/` using the templates below.
4. `chmod +x .claude/scripts/*.sh`.
5. Restart Claude Code so MCP servers reconnect.

## Script templates

### `.claude/scripts/postgres-mcp.sh`

```bash
#!/usr/bin/env bash
set -e
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../.." && pwd)"
val=$(grep -E '^DATABASE_URL=' "$project_root/.env" | head -1 | cut -d= -f2-)
val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
[ -z "$val" ] && { echo "DATABASE_URL not set in .env" >&2; exit 1; }
exec npx -y @modelcontextprotocol/server-postgres "$val"
```

### `.claude/scripts/firecrawl-mcp.sh`

```bash
#!/usr/bin/env bash
set -e
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../.." && pwd)"
val=$(grep -E '^FIRECRAWL_API_KEY=' "$project_root/.env" | head -1 | cut -d= -f2-)
val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
[ -z "$val" ] && { echo "FIRECRAWL_API_KEY not set in .env" >&2; exit 1; }
export FIRECRAWL_API_KEY="$val"
exec npx -y firecrawl-mcp
```

### `.claude/scripts/github-mcp.sh`

```bash
#!/usr/bin/env bash
set -e
token=$(gh auth token 2>/dev/null)
[ -z "$token" ] && { echo "no token from \`gh auth token\` — run \`gh auth login\`" >&2; exit 1; }
export GITHUB_PERSONAL_ACCESS_TOKEN="$token"
exec npx -y @modelcontextprotocol/server-github
```

## Hooks

The committed `.claude/settings.json` wires up six hook scripts under `.claude/hooks/`. Those scripts **are** committed (they're not in the global ignore — only `.claude/scripts/` is treated as personal). No setup needed beyond a normal clone.

## Troubleshooting

- **MCP server fails silently on startup**: run the wrapper directly from the project root (`bash .claude/scripts/postgres-mcp.sh`) to see the stderr.
- **`gh auth token` returns nothing**: re-run `gh auth login` and pick the github.com host.
- **`.env` not found**: the wrappers walk two directories up from their own location; the scripts must live exactly at `.claude/scripts/<name>.sh`.
