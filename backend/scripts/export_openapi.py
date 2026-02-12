#!/usr/bin/env python
"""
Export OpenAPI specification to a static JSON file.

This script imports the FastAPI application and exports its OpenAPI schema
to docs/openapi.json for documentation and integration purposes.

Usage:
    python scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


def export_openapi():
    """Export OpenAPI spec to docs/openapi.json."""
    # Get the OpenAPI schema
    openapi_schema = app.openapi()

    if not openapi_schema:
        print("ERROR: Failed to generate OpenAPI schema")
        return False

    # Determine output path
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / "docs" / "openapi.json"

    # Ensure docs directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the schema to file
    try:
        with open(output_path, "w") as f:
            json.dump(openapi_schema, f, indent=2)
        print(f"✓ OpenAPI spec exported to: {output_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to write OpenAPI spec: {e}")
        return False


if __name__ == "__main__":
    success = export_openapi()
    sys.exit(0 if success else 1)
