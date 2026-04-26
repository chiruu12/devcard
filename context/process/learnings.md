# Learnings

Technical discoveries that should persist across sessions.

## GitHub API

- **Events API limit**: Only returns the last 300 events / ~30 days. Activity analysis must be labeled as "recent pattern", not "historical profile". Use repo `pushed_at` timestamps for supplementary long-term signals.
- **Rate limits without auth**: 60 requests/hour. A single DevCard generation for a 30-repo user needs ~65-100 calls. Always warn users to provide a token.
- **Rate limits with auth**: 5000 requests/hour. Sufficient for batch generation.
- **Repo language endpoint**: Returns bytes per language, not percentages. Calculate percentages ourselves.
- **Content endpoint returns base64**: File contents from the contents API are base64-encoded. Always decode before parsing.
- **Pagination via Link headers**: Repos endpoint returns max 100 per page. Must follow `rel="next"` links to get all repos.

## SVG Rendering for GitHub

- **GitHub SVG sanitizer strips**: foreignObject, script tags, external resources (fonts, images, stylesheets), iframe, embed, object
- **GitHub SVG allows**: CSS animations in `<style>` blocks, inline styles, system fonts
- **Font stack**: Must use system fonts only. `"Segoe UI", Ubuntu, "Helvetica Neue", sans-serif` for body, `"SF Mono", "Cascadia Code", Consolas, monospace` for code.
- **Size target**: Keep SVG under 30KB for fast loading in READMEs

## Dependency Parsing

- **pyproject.toml**: Use `tomllib` (stdlib 3.11+). Dependencies can be in `[project.dependencies]`, `[tool.poetry.dependencies]`, or `[tool.pdm.dependencies]`.
- **package.json**: Parse both `dependencies` and `devDependencies`. Package names may be scoped (`@org/pkg`).
- **requirements.txt**: Lines may have version specifiers, comments, `-r` includes, `--index-url`. Only extract the package name.
- **go.mod**: Dependencies in `require` block. Module paths include version suffix.
- **Cargo.toml**: Dependencies in `[dependencies]`, `[dev-dependencies]`, `[build-dependencies]`.

## Pydantic v2

- Use `model_dump_json(exclude_none=True)` for clean output — None fields should not appear in devcard.json
- Use `Field(description=...)` on every field — these propagate to JSON Schema generation
- Use `ConfigDict(extra="ignore")` on GitHub API models — forward compatibility when GitHub adds new fields
