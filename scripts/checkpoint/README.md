# Project Checkpoint System

A project state snapshot and restore system.

## Quick Start

```bash
# Save a checkpoint
python scripts/checkpoint/checkpoint.py save --name "my-checkpoint" --message "Description"

# Restore latest checkpoint (displays context)
python scripts/checkpoint/checkpoint.py restore --latest

# List all checkpoints
python scripts/checkpoint/checkpoint.py list

# Show checkpoint details
python scripts/checkpoint/checkpoint.py show <checkpoint_id>
```

## What Gets Saved

Each checkpoint captures:

- **Git State**: Branch, commit hash, uncommitted changes diff
- **Project Info**: Auto-detected type (Python, Node.js, etc.)
- **File Inventory**: Source files, tests, configs, documentation
- **Key Files**: README.md, package.json, requirements.txt, etc.
- **Timestamp**: When the checkpoint was created

## Commands

### Save
```bash
python scripts/checkpoint/checkpoint.py save [--name NAME] [--message MSG]
```
Creates a new checkpoint. Auto-generates ID based on timestamp.

### Restore
```bash
python scripts/checkpoint/checkpoint.py restore --latest
python scripts/checkpoint/checkpoint.py restore --id <checkpoint_id>
```
Displays project context from a saved checkpoint. Non-destructive.

### List
```bash
python scripts/checkpoint/checkpoint.py list [--limit N]
```
Shows available checkpoints. Default limit is 10.

### Show
```bash
python scripts/checkpoint/checkpoint.py show <checkpoint_id>
```
Displays detailed information about a specific checkpoint.

### Delete
```bash
python scripts/checkpoint/checkpoint.py delete <checkpoint_id>
```
Removes a checkpoint permanently.

## Storage

Checkpoints are stored in `.checkpoints/` directory:

```
.checkpoints/
├── index.json           # Checkpoint index
└── <checkpoint_id>/
    ├── checkpoint.json  # Full state metadata
    ├── uncommitted.diff # Git diff (if changes present)
    └── [key files]      # Backed up project files
```

## Integration with Claude Code

When starting a new session, restore context with:
```
python scripts/checkpoint/checkpoint.py restore --latest
```

Before ending a session, save state with:
```
python scripts/checkpoint/checkpoint.py save --name "session-end" --message "Progress description"
```
