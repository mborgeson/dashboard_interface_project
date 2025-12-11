# Claude-Flow Project Configuration

This directory contains project-specific configuration for Claude-Flow swarm orchestration.

## Directory Structure

```
.claude-flow/
├── README.md              # This file
├── docs/                  # Project-specific documentation for agents
├── templates/             # Task templates and prompts
└── workflows/             # Custom workflow definitions

.swarm/
├── memory.db              # SQLite database for reasoning bank & memory
├── memory/                # Persistent memory storage
├── metrics/               # Performance and agent metrics
├── logs/                  # Execution logs
└── checkpoints/           # State checkpoints for recovery
```

## Configuration Files

### `claude-flow.config.json` (Project Root)
Main configuration file controlling:
- **memory**: Retention, storage backend, size limits
- **reasoningBank**: Cross-session knowledge persistence
- **features**: Enable/disable capabilities
- **performance**: Agent limits, topology, caching
- **agents**: Specialist configurations for frontend/backend/testing

### `.mcp.json` (Project Root)
MCP server configuration with project-specific paths:
- `MEMORY_PATH`: Points to `.swarm/memory`
- `METRICS_PATH`: Points to `.swarm/metrics`
- `CLAUDE_FLOW_DB_PATH`: Points to `.swarm/memory.db`

## Usage

### Initialize Swarm for This Project
```bash
# From project root
npx claude-flow swarm init --topology adaptive
```

### Spawn Specialized Agents
```bash
# Frontend specialist
npx claude-flow agent spawn --type frontend --capabilities "react,typescript"

# Backend specialist
npx claude-flow agent spawn --type backend --capabilities "fastapi,python"

# QA specialist
npx claude-flow agent spawn --type tester --capabilities "playwright,vitest"
```

### Task Orchestration
```bash
# Run task with auto-agent selection
npx claude-flow task orchestrate "Implement user authentication" --priority high

# Check swarm status
npx claude-flow swarm status
```

## Project-Specific Agent Specializations

| Agent Type | Focus Areas | Directories |
|------------|-------------|-------------|
| **frontend** | React, TypeScript, TailwindCSS, Radix UI | `src/` |
| **backend** | FastAPI, Python, SQLAlchemy, Pydantic | `backend/` |
| **testing** | Vitest, Playwright, Pytest | `e2e/`, `backend/tests/` |

## Memory & Reasoning Bank

This project uses a local SQLite database (`.swarm/memory.db`) for:
- Cross-session memory persistence
- Reasoning bank for decision retrieval
- Agent coordination state
- Task history and outcomes

Memory is retained for **90 days** with automatic compression.

## Metrics

Performance metrics are stored in `.swarm/metrics/`:
- `agent-metrics.json`: Per-agent performance
- `task-metrics.json`: Task completion stats
- `performance.json`: Overall system performance
- `system-metrics.json`: Resource utilization
