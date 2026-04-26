# DevCard Schema Design

## Principles
1. **Agent-first**: Every field has a `description` in the JSON Schema. Agents read descriptions to understand semantics.
2. **Graceful degradation**: All sections except `identity` and `generator` are optional. A DevCard with just a name is valid.
3. **No opinion, just signal**: The schema reports what it observes (languages, activity patterns, quality signals). It does not rate developers as "good" or "bad".
4. **Versioned**: Schema version in `$schema` field. Breaking changes require a new major version.

## Key Design Decisions
- `languages` uses percentage, not raw bytes — percentages are comparable across developers
- `stack` categorizes technologies, not just lists them — agents need "what kind of tool" not just "tool name"
- `activity.status` is a 4-level enum, not a score — discrete levels are more useful for agent decisions
- `quality` section measures practices, not code quality — we can detect CI/tests/docs presence, not code correctness
- `expertise.domains` uses confidence scores (0-1) — agents can threshold at their preferred level

## Schema Location
- Definition: `schema/devcard.v1.schema.json`
- Examples: `schema/examples/`
- Validator: `src/devcard/validators/schema_validator.py`
