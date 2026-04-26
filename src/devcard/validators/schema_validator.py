from __future__ import annotations

import json
from pathlib import Path

import jsonschema

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "schema" / "devcard.v1.schema.json"
)


def validate_devcard(data: dict, schema_path: Path | None = None) -> list[str]:
    path = schema_path or _SCHEMA_PATH
    with open(path) as f:
        schema = json.load(f)

    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in validator.iter_errors(data):
        path_parts = [str(p) for p in error.absolute_path]
        location = " → ".join(path_parts) if path_parts else "root"
        errors.append(f"{location}: {error.message}")
    return errors
