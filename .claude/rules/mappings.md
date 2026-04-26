---
paths:
  - "mappings/**/*.yaml"
  - "src/devcard/mappings.py"
---

# Mapping File Conventions

## Structure
Mapping YAML files are pure data — no logic, no conditionals. They are loaded once at import time by `src/devcard/mappings.py` and exposed as Python dicts.

## Rules
- Keep entries alphabetically sorted within each section for easy diffing
- Every entry must have a category/domain value — no empty values
- Use lowercase for all keys (package names, topic slugs)
- Use Title Case for display name values (`"FastAPI"`, `"PostgreSQL"`)
- `dependencies.yaml`: keyed by package name, value is `{ category, name }`. Organized by ecosystem section (Python, JavaScript, Go, Rust, etc.)
- `topics_to_domains.yaml`: keyed by GitHub topic slug, value is expertise domain
- `file_patterns.yaml`: keyed by signal type (ci, testing, docs, containerization, iac, linting), value is list of file/directory globs
- `dev_type_rules.yaml`: ordered list of rule objects with `conditions` and `type` fields. First match wins. Must end with a default/fallback rule.
- When adding a new mapping entry, add it to the correct alphabetical position
- When adding a new ecosystem to `dependencies.yaml`, include at least 20 entries covering the most popular packages
- Changes to mapping files do NOT require code changes — the loader is generic
