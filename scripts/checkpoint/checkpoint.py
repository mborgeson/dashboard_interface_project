#!/usr/bin/env python3
"""
Project Checkpoint System - Generic Version

Provides save/restore functionality for project state including:
- Git state (branch, commit, uncommitted changes)
- File inventory by category
- Session metadata
- Project context snapshots

Usage:
    python checkpoint.py save [--name NAME] [--message MSG]
    python checkpoint.py restore --latest
    python checkpoint.py restore --id CHECKPOINT_ID
    python checkpoint.py list [--limit N]
    python checkpoint.py show CHECKPOINT_ID
    python checkpoint.py delete CHECKPOINT_ID
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Project root - automatically determined from script location
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROJECT_NAME = PROJECT_ROOT.name
CHECKPOINT_DIR = PROJECT_ROOT / ".checkpoints"
CHECKPOINT_INDEX = CHECKPOINT_DIR / "index.json"


def ensure_checkpoint_dir():
    """Ensure checkpoint directory exists."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    if not CHECKPOINT_INDEX.exists():
        CHECKPOINT_INDEX.write_text(json.dumps({
            "project_name": PROJECT_NAME,
            "project_path": str(PROJECT_ROOT),
            "checkpoints": []
        }, indent=2))


def get_git_state() -> dict:
    """Capture current git state."""
    try:
        # Current branch
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()

        # Current commit
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()

        # Commit message
        commit_msg = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()

        # Status (short form)
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()

        # Uncommitted diff
        diff = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout

        # Remote URL
        remote_url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()

        return {
            "branch": branch,
            "commit": commit,
            "commit_short": commit[:8] if commit else "unknown",
            "commit_message": commit_msg,
            "status": status,
            "has_uncommitted_changes": bool(status),
            "diff_size": len(diff),
            "remote_url": remote_url,
        }
    except Exception as e:
        return {"error": str(e)}


def auto_detect_file_categories() -> Dict[str, List[str]]:
    """Auto-detect file categories based on common project structures."""
    inventory = {
        "source_files": [],
        "test_files": [],
        "config_files": [],
        "documentation": [],
        "scripts": [],
    }

    # Common source directories
    src_dirs = ["src", "app", "lib", "core", "api", "components", "pages", "modules"]
    for src_dir in src_dirs:
        src_path = PROJECT_ROOT / src_dir
        if src_path.exists():
            for ext in ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.vue", "*.rs", "*.go"]:
                inventory["source_files"].extend([
                    str(f.relative_to(PROJECT_ROOT))
                    for f in src_path.rglob(ext)
                    if not any(part.startswith('.') for part in f.parts)
                ][:50])  # Limit to 50 files per category

    # Test files
    test_dirs = ["tests", "test", "spec", "__tests__"]
    for test_dir in test_dirs:
        test_path = PROJECT_ROOT / test_dir
        if test_path.exists():
            inventory["test_files"].extend([
                str(f.relative_to(PROJECT_ROOT))
                for f in test_path.rglob("*")
                if f.is_file() and f.suffix in [".py", ".js", ".ts", ".jsx", ".tsx"]
            ][:50])

    # Config files at root
    config_patterns = [
        "*.json", "*.yaml", "*.yml", "*.toml", "*.ini", "*.cfg",
        "*.config.js", "*.config.ts", "Makefile", "Dockerfile", "docker-compose*"
    ]
    for pattern in config_patterns:
        inventory["config_files"].extend([
            f.name for f in PROJECT_ROOT.glob(pattern) if f.is_file()
        ])

    # Documentation
    docs_path = PROJECT_ROOT / "docs"
    if docs_path.exists():
        inventory["documentation"].extend([
            str(f.relative_to(PROJECT_ROOT))
            for f in docs_path.rglob("*.md")
        ][:30])

    # Root markdown files
    inventory["documentation"].extend([
        f.name for f in PROJECT_ROOT.glob("*.md") if f.is_file()
    ])

    # Scripts
    scripts_path = PROJECT_ROOT / "scripts"
    if scripts_path.exists():
        inventory["scripts"].extend([
            str(f.relative_to(PROJECT_ROOT))
            for f in scripts_path.rglob("*")
            if f.is_file() and f.suffix in [".py", ".sh", ".bash", ".js"]
        ][:30])

    # Remove empty categories and duplicates
    return {k: list(set(v)) for k, v in inventory.items() if v}


def get_project_info() -> dict:
    """Extract project information from common config files."""
    info = {
        "name": PROJECT_NAME,
        "path": str(PROJECT_ROOT),
        "detected_type": "unknown",
        "dependencies": {},
    }

    # Check for package.json (Node.js)
    package_json = PROJECT_ROOT / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            info["detected_type"] = "nodejs"
            info["version"] = data.get("version", "unknown")
            info["dependencies"]["npm"] = len(data.get("dependencies", {}))
            info["dependencies"]["npm_dev"] = len(data.get("devDependencies", {}))
        except:
            pass

    # Check for pyproject.toml or requirements.txt (Python)
    pyproject = PROJECT_ROOT / "pyproject.toml"
    requirements = PROJECT_ROOT / "requirements.txt"
    if pyproject.exists() or requirements.exists():
        info["detected_type"] = "python"
        if requirements.exists():
            try:
                lines = requirements.read_text().strip().split("\n")
                info["dependencies"]["pip"] = len([l for l in lines if l and not l.startswith("#")])
            except:
                pass

    # Check for Cargo.toml (Rust)
    cargo = PROJECT_ROOT / "Cargo.toml"
    if cargo.exists():
        info["detected_type"] = "rust"

    # Check for go.mod (Go)
    gomod = PROJECT_ROOT / "go.mod"
    if gomod.exists():
        info["detected_type"] = "go"

    return info


def generate_checkpoint_id() -> str:
    """Generate unique checkpoint ID."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_checkpoint(name: Optional[str] = None, message: Optional[str] = None) -> str:
    """Save a new checkpoint."""
    ensure_checkpoint_dir()

    checkpoint_id = generate_checkpoint_id()
    checkpoint_path = CHECKPOINT_DIR / checkpoint_id
    checkpoint_path.mkdir(parents=True, exist_ok=True)

    # Gather state
    checkpoint_data = {
        "id": checkpoint_id,
        "name": name or f"checkpoint-{checkpoint_id}",
        "message": message or "Manual checkpoint",
        "timestamp": datetime.now().isoformat(),
        "project": get_project_info(),
        "git": get_git_state(),
        "files": auto_detect_file_categories(),
    }

    # Save checkpoint metadata
    (checkpoint_path / "checkpoint.json").write_text(
        json.dumps(checkpoint_data, indent=2)
    )

    # Save git diff if there are uncommitted changes
    if checkpoint_data["git"].get("has_uncommitted_changes"):
        diff = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout
        (checkpoint_path / "uncommitted.diff").write_text(diff)

    # Backup key project files if they exist
    key_files = [
        "README.md",
        "CHANGELOG.md",
        "package.json",
        "pyproject.toml",
        "requirements.txt",
    ]
    for key_file in key_files:
        src = PROJECT_ROOT / key_file
        if src.exists():
            shutil.copy(src, checkpoint_path / key_file)

    # Update index
    index = json.loads(CHECKPOINT_INDEX.read_text())
    index["checkpoints"].insert(0, {
        "id": checkpoint_id,
        "name": checkpoint_data["name"],
        "message": checkpoint_data["message"],
        "timestamp": checkpoint_data["timestamp"],
        "git_commit": checkpoint_data["git"].get("commit_short", "unknown"),
        "git_branch": checkpoint_data["git"].get("branch", "unknown"),
        "project_type": checkpoint_data["project"].get("detected_type", "unknown"),
    })
    CHECKPOINT_INDEX.write_text(json.dumps(index, indent=2))

    print(f"Checkpoint saved: {checkpoint_id}")
    print(f"  Name: {checkpoint_data['name']}")
    print(f"  Project: {PROJECT_NAME} ({checkpoint_data['project'].get('detected_type', 'unknown')})")
    print(f"  Git: {checkpoint_data['git'].get('branch', 'unknown')}@{checkpoint_data['git'].get('commit_short', 'unknown')}")
    if checkpoint_data['git'].get('has_uncommitted_changes'):
        print(f"  Uncommitted changes: {checkpoint_data['git'].get('diff_size', 0)} bytes")

    return checkpoint_id


def list_checkpoints(limit: int = 10) -> list:
    """List available checkpoints."""
    ensure_checkpoint_dir()

    index = json.loads(CHECKPOINT_INDEX.read_text())
    checkpoints = index.get("checkpoints", [])[:limit]

    if not checkpoints:
        print(f"No checkpoints found for {PROJECT_NAME}.")
        return []

    print(f"\nCheckpoints for: {PROJECT_NAME}")
    print(f"{'='*80}")
    print(f"{'ID':<18} {'Name':<25} {'Branch':<15} {'Commit':<10} {'Type':<10}")
    print(f"{'-'*80}")

    for cp in checkpoints:
        print(f"{cp['id']:<18} {cp.get('name', 'unnamed')[:23]:<25} "
              f"{cp.get('git_branch', '?')[:13]:<15} {cp.get('git_commit', '?'):<10} "
              f"{cp.get('project_type', '?'):<10}")

    print(f"\nShowing {len(checkpoints)} of {len(index.get('checkpoints', []))} checkpoints")
    return checkpoints


def get_latest_checkpoint() -> Optional[dict]:
    """Get the most recent checkpoint."""
    ensure_checkpoint_dir()

    index = json.loads(CHECKPOINT_INDEX.read_text())
    checkpoints = index.get("checkpoints", [])

    return checkpoints[0] if checkpoints else None


def show_checkpoint(checkpoint_id: str) -> Optional[dict]:
    """Show details of a specific checkpoint."""
    checkpoint_path = CHECKPOINT_DIR / checkpoint_id / "checkpoint.json"

    if not checkpoint_path.exists():
        print(f"Checkpoint not found: {checkpoint_id}")
        return None

    data = json.loads(checkpoint_path.read_text())

    print(f"\n{'='*70}")
    print(f"Checkpoint: {data['id']}")
    print(f"{'='*70}")
    print(f"Name: {data.get('name', 'unnamed')}")
    print(f"Message: {data.get('message', 'No message')}")
    print(f"Timestamp: {data.get('timestamp', 'unknown')}")

    print(f"\nProject Info:")
    print(f"  Name: {data['project'].get('name', 'unknown')}")
    print(f"  Type: {data['project'].get('detected_type', 'unknown')}")
    if data['project'].get('version'):
        print(f"  Version: {data['project'].get('version')}")

    print(f"\nGit State:")
    print(f"  Branch: {data['git'].get('branch', 'unknown')}")
    print(f"  Commit: {data['git'].get('commit', 'unknown')}")
    print(f"  Message: {data['git'].get('commit_message', 'unknown')}")
    print(f"  Uncommitted Changes: {'Yes' if data['git'].get('has_uncommitted_changes') else 'No'}")
    if data['git'].get('has_uncommitted_changes'):
        print(f"  Diff Size: {data['git'].get('diff_size', 0)} bytes")

    print(f"\nFile Inventory:")
    for category, files in data.get('files', {}).items():
        if files:
            print(f"  {category}: {len(files)} files")

    return data


def restore_checkpoint(checkpoint_id: str = None, latest: bool = False) -> bool:
    """Restore project context from a checkpoint (displays info only - non-destructive)."""
    if latest:
        cp = get_latest_checkpoint()
        if not cp:
            print("No checkpoints available to restore.")
            return False
        checkpoint_id = cp["id"]

    checkpoint_path = CHECKPOINT_DIR / checkpoint_id / "checkpoint.json"

    if not checkpoint_path.exists():
        print(f"Checkpoint not found: {checkpoint_id}")
        return False

    data = json.loads(checkpoint_path.read_text())

    print(f"\n{'='*70}")
    print(f"RESTORING CONTEXT FROM CHECKPOINT: {checkpoint_id}")
    print(f"{'='*70}")

    # Display context summary
    print(f"\nProject: {data['project'].get('name', 'Unknown')}")
    print(f"Type: {data['project'].get('detected_type', 'Unknown')}")
    print(f"Git: {data['git'].get('branch', 'unknown')}@{data['git'].get('commit_short', 'unknown')}")
    print(f"Saved: {data.get('timestamp', 'unknown')}")

    print(f"\n{'='*70}")
    print("PROJECT CONTEXT SUMMARY")
    print(f"{'='*70}")

    print("\n## Git State at Checkpoint:")
    print(f"  Branch: {data['git'].get('branch', 'unknown')}")
    print(f"  Commit: {data['git'].get('commit', 'unknown')[:12]}...")
    print(f"  Message: {data['git'].get('commit_message', 'unknown')}")

    if data['git'].get('has_uncommitted_changes'):
        print(f"\n  ⚠ Had uncommitted changes ({data['git'].get('diff_size', 0)} bytes)")
        diff_path = CHECKPOINT_DIR / checkpoint_id / "uncommitted.diff"
        if diff_path.exists():
            print(f"  Diff saved at: {diff_path}")

    print("\n## File Summary:")
    for category, files in data.get('files', {}).items():
        if files:
            print(f"  {category.replace('_', ' ').title()}: {len(files)} files")

    print(f"\n{'='*70}")
    print("Context restored successfully!")
    print(f"{'='*70}")
    print("\nNote: This is a non-destructive restore. It displays the saved context")
    print("but does not modify any files. Use the git information above to")
    print("manually checkout the saved commit if needed.")

    return True


def delete_checkpoint(checkpoint_id: str) -> bool:
    """Delete a checkpoint."""
    checkpoint_path = CHECKPOINT_DIR / checkpoint_id

    if not checkpoint_path.exists():
        print(f"Checkpoint not found: {checkpoint_id}")
        return False

    shutil.rmtree(checkpoint_path)

    # Update index
    index = json.loads(CHECKPOINT_INDEX.read_text())
    index["checkpoints"] = [cp for cp in index["checkpoints"] if cp["id"] != checkpoint_id]
    CHECKPOINT_INDEX.write_text(json.dumps(index, indent=2))

    print(f"Deleted checkpoint: {checkpoint_id}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description=f"Project Checkpoint System for {PROJECT_NAME}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s save --name "before-refactor" --message "About to refactor auth"
  %(prog)s list
  %(prog)s show 20260108_143000
  %(prog)s restore --latest
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Save command
    save_parser = subparsers.add_parser("save", help="Save a new checkpoint")
    save_parser.add_argument("--name", "-n", help="Checkpoint name")
    save_parser.add_argument("--message", "-m", help="Checkpoint message")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from checkpoint")
    restore_parser.add_argument("--latest", action="store_true", help="Restore latest checkpoint")
    restore_parser.add_argument("--id", help="Checkpoint ID to restore")

    # List command
    list_parser = subparsers.add_parser("list", help="List checkpoints")
    list_parser.add_argument("--limit", "-l", type=int, default=10, help="Max checkpoints to show")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show checkpoint details")
    show_parser.add_argument("checkpoint_id", help="Checkpoint ID")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a checkpoint")
    delete_parser.add_argument("checkpoint_id", help="Checkpoint ID")

    args = parser.parse_args()

    if args.command == "save":
        save_checkpoint(name=args.name, message=args.message)
    elif args.command == "restore":
        if args.latest:
            restore_checkpoint(latest=True)
        elif args.id:
            restore_checkpoint(checkpoint_id=args.id)
        else:
            print("Error: Specify --latest or --id")
            sys.exit(1)
    elif args.command == "list":
        list_checkpoints(limit=args.limit)
    elif args.command == "show":
        show_checkpoint(args.checkpoint_id)
    elif args.command == "delete":
        delete_checkpoint(args.checkpoint_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
