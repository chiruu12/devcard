from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_MAPPINGS_DIR = Path(__file__).resolve().parent.parent.parent / "mappings"


def _load_yaml(filename: str) -> dict | list:
    path = _MAPPINGS_DIR / filename
    if not path.exists():
        logger.warning("Mapping file not found: %s", path)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _flatten_dependencies(raw: dict) -> dict[str, dict]:
    flat: dict[str, dict] = {}
    for _ecosystem, packages in raw.items():
        if isinstance(packages, dict):
            flat.update(packages)
    return flat


_raw_deps = _load_yaml("dependencies.yaml")
DEPENDENCIES: dict[str, dict] = _flatten_dependencies(_raw_deps)

TOPICS_TO_DOMAINS: dict[str, str] = _load_yaml("topics_to_domains.yaml")

FILE_PATTERNS: dict[str, list[str]] = _load_yaml("file_patterns.yaml")

_raw_rules = _load_yaml("dev_type_rules.yaml")
DEV_TYPE_RULES: list[dict] = _raw_rules.get("rules", []) if isinstance(_raw_rules, dict) else []
