# DevCard Implementation Plan

## Context

DevCard is a Python CLI tool that generates structured developer identity cards from GitHub profiles. No sign-up, no LLM. The project has comprehensive docs and conventions but 0 lines of code. This plan builds the full MVP: `devcard generate <username>` → `devcard.json` + terminal output + embeddable SVG card.

---

## Phase A: Scaffolding

### pyproject.toml
- Build backend: `hatchling` with `src` layout
- Entry point: `[project.scripts] devcard = "devcard.cli:app"`
- Core deps: `typer[all]>=0.12`, `httpx>=0.27`, `pydantic>=2.0`, `diskcache>=5.6`, `rich>=13.0`, `pyyaml>=6.0`, `jsonschema>=4.20`
- Optional extras: `[enrich]` → `litellm>=1.0`, `[png]` → `cairosvg>=2.7`
- Dev deps in `[dependency-groups]`: `pytest>=8.0`, `pytest-asyncio>=0.23`, `ruff>=0.4`
- `[tool.ruff]` config: target Python 3.11, line-length 100, select `["E", "F", "I", "UP"]`
- `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`

### Directory structure
Create all `__init__.py` stubs (empty files) under `src/devcard/` for:
- `github/`, `extractors/`, `analyzers/`, `renderers/`, `renderers/themes/`, `output/`, `validators/`, `enrichment/`

Create empty dirs with `.gitkeep`: `tests/fixtures/`, `mappings/`, `schema/examples/`, `gallery/`, `docs/`

### Stub CLI
`src/devcard/cli.py` — minimal typer app with `app = typer.Typer()` and a placeholder `generate` command that just prints "Not implemented yet". Enough to verify `uv run devcard --help` works.

### Verify
`uv sync` + `uv run devcard --help` must succeed.

---

## Phase B: Foundation (Steps 2, 3, 4 — can parallelize agents)

### B1: JSON Schema — `schema/devcard.v1.schema.json`

JSON Schema Draft 2020-12. Top-level object with properties:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `$schema` | string (const) | yes | Schema URI |
| `version` | string (const "1.0") | yes | Schema version |
| `generated_at` | string (date-time) | yes | ISO 8601 timestamp |
| `generator` | object | yes | Tool name + version |
| `identity` | object | yes | Name, username, bio, avatar, location, company, blog, twitter, hireable, public_repos, followers, following, created_at |
| `languages` | array of `{name, percentage, color, bytes}` | no | Sorted by percentage desc |
| `stack` | object `{frameworks, libraries, databases, tools, platforms, ci_cd, testing, other}` — each an array of `{name, category, source}` | no | Categorized technology stack |
| `activity` | object `{status, commits_last_year, current_streak, longest_streak, peak_hours, timezone_estimate, heatmap}` | no | Recent activity patterns |
| `projects` | array of `{name, description, url, stars, forks, language, topics, status, maturity, classification}` | no | Top projects |
| `collaboration` | object `{organizations, pull_requests_opened, issues_opened, contribution_style, external_contributions}` | no | Collaboration signals |
| `quality` | object `{score, ci_adoption, test_adoption, docs_adoption, license_adoption, linter_adoption, details}` | no | Practice quality signals |
| `expertise` | object `{domains, profile_type, focus_areas}` | no | Inferred expertise areas with confidence |
| `enriched` | object | no | Optional LLM-generated content (post-MVP) |

All fields must have `description` properties (agent-first design). Every sub-object defined as `$defs` at schema root.

### B1 cont: Schema examples
- `schema/examples/minimal.devcard.json` — only required fields (identity + generator)
- `schema/examples/torvalds.devcard.json` — fully populated, realistic data for Linus Torvalds
- `schema/examples/karpathy.devcard.json` — fully populated for Andrej Karpathy

### B2: Pydantic Models

**`src/devcard/models.py`** — All core models with `Field(description=...)` on every field:

```
DevCard — top-level container
  ├── version: str = "1.0"
  ├── generated_at: datetime
  ├── generator: Generator (name, version, url)
  ├── identity: Identity (required)
  │     username, name, bio, avatar_url, location, company, blog,
  │     twitter_username, hireable, public_repos, public_gists,
  │     followers, following, created_at
  ├── languages: list[Language] = []
  │     name, percentage, color (optional), bytes (optional)
  ├── stack: Stack (optional)
  │     frameworks, libraries, databases, tools, platforms, ci_cd,
  │     testing, other — each list[StackItem(name, category, source)]
  ├── activity: Activity (optional)
  │     status: Literal["active", "moderate", "sporadic", "dormant"]
  │     commits_last_year (optional, estimated), current_streak,
  │     longest_streak, peak_hours: list[int], timezone_estimate,
  │     heatmap: list[list[int]] (7x24)
  ├── projects: list[Project] = []
  │     name, description, url, stars, forks, language, topics,
  │     status: Literal["active", "maintained", "inactive", "archived"]
  │     maturity: Literal["mature", "growing", "new", "stale"]
  │     classification (optional, filled by analyzer)
  ├── collaboration: Collaboration (optional)
  │     organizations: list[str], pull_requests_opened, issues_opened,
  │     contribution_style (optional, filled by analyzer),
  │     external_contributions: int
  ├── quality: Quality (optional)
  │     score: float (0-1), ci_adoption, test_adoption, docs_adoption,
  │     license_adoption, linter_adoption — each float (0-1)
  │     details: list[QualityDetail(repo, signals)]
  ├── expertise: Expertise (optional)
  │     domains: list[Domain(name, confidence: float 0-1)]
  │     profile_type (optional, filled by analyzer)
  │     focus_areas: list[FocusArea(name, evidence)]
  └── enriched: Enriched (optional, post-MVP)
```

Key rules:
- `Optional[X]` with `default=None` for all non-required fields
- `list[X]` with `default_factory=list`, never None for lists
- Use `Literal` for small fixed sets (status, maturity), not enums
- Enums only for `ProfileType` (full_stack, backend, frontend, devops, data, ml, mobile, systems, security, embedded, researcher, other)
- Pure data containers — no methods, no computed properties

**`src/devcard/github/models.py`** — GitHub API response models:

```
GitHubUser — model_config = ConfigDict(extra="ignore")
  login, name, bio, avatar_url, location, company, blog,
  twitter_username, hireable, public_repos, public_gists,
  followers, following, created_at, type

GitHubRepo — model_config = ConfigDict(extra="ignore")
  name, full_name, description, html_url, homepage, language,
  stargazers_count, forks_count, fork, archived, disabled,
  pushed_at, created_at, updated_at, topics, default_branch,
  size, open_issues_count, license (optional dict)

GitHubEvent — model_config = ConfigDict(extra="ignore")
  type, created_at, repo (dict with name), payload (dict),
  public, actor (optional dict)

GitHubContent — model_config = ConfigDict(extra="ignore")
  name, path, type ("file" | "dir"), size, content (optional, base64),
  encoding (optional), sha, url
```

### B3: Mapping Files

**`mappings/dependencies.yaml`** — 400+ entries organized by ecosystem:

```yaml
python:
  fastapi: { category: "framework", name: "FastAPI" }
  django: { category: "framework", name: "Django" }
  flask: { category: "framework", name: "Flask" }
  sqlalchemy: { category: "database", name: "SQLAlchemy" }
  pytest: { category: "testing", name: "pytest" }
  # ... 60+ Python packages

javascript:
  react: { category: "framework", name: "React" }
  next: { category: "framework", name: "Next.js" }
  express: { category: "framework", name: "Express" }
  # ... 80+ JS/TS packages

go:
  # ... 30+ Go modules

rust:
  # ... 30+ Rust crates

ruby:
  # ... 20+ Ruby gems

java:
  # ... 30+ Java/Maven packages

# Also: php, csharp, swift, kotlin
```

**`mappings/topics_to_domains.yaml`** — ~100 GitHub topic → domain mappings:
```yaml
machine-learning: "Machine Learning"
deep-learning: "Machine Learning"
web-development: "Web Development"
devops: "DevOps"
# ...
```

**`mappings/file_patterns.yaml`** — signal detection patterns:
```yaml
ci:
  - ".github/workflows"
  - ".gitlab-ci.yml"
  - "Jenkinsfile"
  - ".circleci"
  - ".travis.yml"
testing:
  - "tests"
  - "test"
  - "__tests__"
  - "spec"
  - "pytest.ini"
  - "jest.config.*"
docs:
  - "docs"
  - "doc"
  - "README.md"
  - "CONTRIBUTING.md"
containerization:
  - "Dockerfile"
  - "docker-compose.yml"
  - ".dockerignore"
iac:
  - "terraform"
  - "ansible"
  - "kubernetes"
  - "k8s"
  - "helm"
linting:
  - ".eslintrc*"
  - "ruff.toml"
  - ".flake8"
  - ".pylintrc"
  - ".prettierrc*"
  - "biome.json"
```

**`mappings/dev_type_rules.yaml`** — ordered decision tree (first match wins):
```yaml
rules:
  - conditions:
      primary_language: ["python", "r", "julia"]
      topics_include_any: ["machine-learning", "deep-learning", "data-science", "ai"]
    type: "ml"
  - conditions:
      primary_language: ["python", "r"]
      topics_include_any: ["data-analysis", "data-engineering", "pandas"]
    type: "data"
  # ... ~20 rules covering all ProfileType values
  - conditions: {}  # default fallback
    type: "full_stack"
```

**`src/devcard/mappings.py`** — loader:
- Loads all 4 YAML files at module import time using `pyyaml`
- Exposes: `DEPENDENCIES: dict`, `TOPICS_TO_DOMAINS: dict`, `FILE_PATTERNS: dict`, `DEV_TYPE_RULES: list`
- Uses `importlib.resources` or `pathlib` to resolve file paths relative to project root

---

## Phase C: GitHub Client

### `src/devcard/config.py`
```
DevCardConfig:
  github_token: str | None  — resolved via: --token flag > GITHUB_TOKEN env > `gh auth token` subprocess
  base_url: str = "https://api.github.com"
  cache_dir: Path = ~/.cache/devcard
  cache_ttl: int = 3600  (1 hour)
  max_repos: int = 30
  no_cache: bool = False
```
Token resolution as a `@classmethod` or standalone function. The `gh auth token` fallback uses `subprocess.run` with capture, ignoring errors.

### `src/devcard/github/cache.py`
- Wraps `diskcache.Cache`
- `get(url: str) -> dict | None` — returns cached JSON or None
- `set(url: str, data: dict, ttl: int)` — stores JSON response
- Key format: `"GET:{url}"`
- Honors `no_cache` config flag (skip cache entirely)

### `src/devcard/github/client.py`
```
class GitHubClient:
  __init__(config: DevCardConfig)
    - Creates httpx.AsyncClient with auth headers if token present
    - Creates Semaphore(10)
    - Creates cache instance

  async _request(url: str) -> dict
    - Acquires semaphore
    - Checks cache first
    - Makes HTTP GET via httpx
    - Reads X-RateLimit-Remaining; warns at <10, sleeps at 0
    - Caches response on success
    - Raises GitHubAPIError on non-200

  async get_user(username: str) -> GitHubUser
  async get_repos(username: str) -> list[GitHubRepo]
    - Paginated (100 per page), follows Link headers
    - Returns non-fork only, sorted by stars desc, limited to max_repos
  async get_repo_languages(owner: str, repo: str) -> dict[str, int]
  async get_repo_contents(owner: str, repo: str, path: str = "") -> list[GitHubContent]
  async get_repo_topics(owner: str, repo: str) -> list[str]
  async get_user_events(username: str) -> list[GitHubEvent]
    - Fetches up to 3 pages (300 events max)
  async get_user_orgs(username: str) -> list[str]
    - Returns org login names

  async close()  — closes httpx client + cache
```

Custom `GitHubAPIError` exception with status code, endpoint, and message.

---

## Phase D: First E2E

### `src/devcard/extractors/identity.py`
Signature: `async def extract_identity(client, user, repos, **kwargs) -> Identity | None`
- 1:1 mapping from `GitHubUser` fields to `Identity` fields
- Returns None if user is somehow invalid (shouldn't happen but convention says never raise)

### `src/devcard/pipeline.py`
```
async def generate_devcard(username: str, config: DevCardConfig) -> DevCard:
  1. Create GitHubClient
  2. Fetch user via client.get_user()
  3. Fetch repos via client.get_repos()
  4. Run identity extractor
  5. Assemble DevCard with identity + generator metadata
  6. Close client
  7. Return DevCard
```

### `src/devcard/output/json_output.py`
- `def to_json(devcard: DevCard) -> str` — `model_dump_json(indent=2, exclude_none=True)`
- Prepends `$schema` field pointing to the schema URL

### Update `src/devcard/cli.py`
- `generate` command: takes `username` arg, `--token`, `--format`, `-o/--output` options
- Resolves config, calls `asyncio.run(generate_devcard(...))`, writes output
- Rich error panel on failure, exit code 1
- Progress/status to stderr via Rich console

**Milestone**: `uv run devcard generate torvalds` → JSON with identity section populated.

---

## Phase E: Core Extractors

### E1: Independent extractors (can run as parallel agent)

**`extractors/languages.py`** — `extract_languages(client, user, repos) -> list[Language] | None`
- For each non-fork repo, call `client.get_repo_languages(owner, repo)` concurrently via `asyncio.gather`
- Aggregate bytes across all repos per language
- Calculate percentage of total bytes
- Sort by percentage descending
- Map to `Language` objects (include color from hardcoded LINGUIST_COLORS dict)

**`extractors/activity.py`** — `extract_activity(client, user, repos) -> Activity | None`
- Fetch events via `client.get_user_events()`
- Filter to PushEvents
- Build 7x24 heatmap (day-of-week × hour-of-day) from event timestamps
- Calculate peak hours (top 3 hours by commit count)
- Estimate timezone from peak hours (assume peak = 10am-7pm local)
- Determine status: active (events in last 7 days) / moderate (last 30) / sporadic (last 90) / dormant
- Use repo `pushed_at` timestamps as supplementary signal for `commits_last_year` estimate

**`extractors/projects.py`** — `extract_projects(client, user, repos) -> list[Project] | None`
- Score each non-fork repo: `stars*3 + forks*2 + recency_bonus`
- Recency bonus: +10 if pushed in last 30 days, +5 if 90 days
- Take top 10
- Determine status from `pushed_at`: active (<30d), maintained (<90d), inactive (<365d), archived
- Determine maturity from age + stars: mature (>2yr + >50 stars), growing (<2yr + >10 stars), new (<6mo), stale (>1yr inactive)

**`extractors/collaboration.py`** — `extract_collaboration(client, user, repos) -> Collaboration | None`
- From events: count PullRequestEvent and IssuesEvent where repo owner != username
- Fetch orgs via `client.get_user_orgs()`
- external_contributions = count of events on repos not owned by user

**`extractors/quality.py`** — `extract_quality(client, user, repos, root_listings) -> Quality | None`
- Takes pre-fetched `root_listings: dict[str, list[GitHubContent]]` (repo name → dir listing)
- For each repo, check root listing against `FILE_PATTERNS` from mappings
- Calculate adoption rates: `ci_adoption = repos_with_ci / total_repos`
- Same for test, docs, license, linter
- Composite score: `tests*0.3 + ci*0.25 + docs*0.2 + license*0.15 + linter*0.1`
- Build `QualityDetail` per repo listing which signals were found

### E2: Dependent extractors + orchestration

**`extractors/stack.py`** — `extract_stack(client, user, repos, root_listings) -> Stack | None`
- Parser registry: dict mapping filename → parser function
  - `package.json` → parse JSON, extract keys from `dependencies` + `devDependencies`
  - `requirements.txt` → line-by-line, strip version specifiers/comments
  - `pyproject.toml` → `tomllib`, check `[project.dependencies]`, `[tool.poetry.dependencies]`, `[tool.pdm.dependencies]`
  - `go.mod` → regex for `require` block entries
  - `Cargo.toml` → `tomllib`, `[dependencies]` + `[dev-dependencies]`
  - `Gemfile` → regex for `gem "name"` lines
  - `pom.xml` → regex for `<artifactId>` (basic, not full XML parse)
  - `composer.json` → parse JSON, `require` + `require-dev` keys
- For each non-fork repo:
  1. Check `root_listings` for known dep file names
  2. For each found dep file, fetch content via `client.get_repo_contents(owner, repo, filename)`
  3. Decode base64 content
  4. Run the matching parser → list of package names
  5. Look up each package in `DEPENDENCIES` mapping → `StackItem(name, category, source=repo)`
- Deduplicate by name across repos
- Group by category into Stack fields (frameworks, libraries, databases, etc.)

**`extractors/expertise.py`** — `extract_expertise(client, user, repos, *, languages, stack) -> Expertise | None`
- Input: already-computed languages and stack from previous extractors
- From repo topics: look up each in `TOPICS_TO_DOMAINS` → domain with confidence 0.7
- From stack categories: infer domain (e.g., "framework:React" → "Web Development") with confidence 0.5
- From primary languages: infer domain (e.g., Python + ML libs → "Machine Learning") with confidence 0.3
- Merge: if same domain appears multiple times, take max confidence + boost 0.1 per additional signal (cap 1.0)
- Sort domains by confidence descending
- `focus_areas`: top 3-5 domains with evidence strings

### Extractor orchestration — update `extractors/__init__.py` + `pipeline.py`
- Pipeline fetches root dir listings once per repo (1 API call each) before extractors run
- Phase 1 (`asyncio.gather`): identity, languages, activity, projects, collaboration + stack, quality (all independent, stack and quality receive root_listings)
- Phase 2 (sequential after phase 1): expertise (needs languages + stack output)
- Pipeline assembles DevCard from all extractor outputs

---

## Phase F: Analyzers

All analyzers are sync functions that take the assembled `DevCard` and mutate/augment specific fields.

### `analyzers/developer_type.py`
- `def analyze_developer_type(devcard: DevCard) -> str`
- Loads `DEV_TYPE_RULES` from mappings
- For each rule, check conditions against devcard data:
  - `primary_language`: check if devcard's top language is in the list
  - `topics_include_any`: check if any project topics match
  - `stack_includes_any`: check if any stack items match
  - `has_quality_signal`: check quality adoption thresholds
- First matching rule wins → return its `type` string
- Default fallback: `"full_stack"`

### `analyzers/project_classifier.py`
- `def classify_projects(devcard: DevCard) -> None` (mutates project.classification in-place)
- Heuristics per project:
  - Has `lib` or `sdk` in name/topics, or primary use as dependency → `"library"`
  - Has web-app indicators (framework deps, `app` in name) → `"application"`
  - CLI tool indicators → `"tool"`
  - Has `framework` in topics → `"framework"`
  - Heavy docs/wiki content → `"docs"`
  - Tutorial/learning indicators → `"learning"`
  - Default: `"application"`

### `analyzers/contribution_style.py`
- `def analyze_contribution_style(devcard: DevCard) -> str`
- Logic:
  - Many repos with high stars, few external contributions → `"maintainer"`
  - Many external PRs/issues, contributor to other orgs → `"contributor"`
  - Mostly personal repos, few collaborations → `"solo_builder"`
  - Many forked/starred repos, wide topic spread → `"explorer"`

### `analyzers/scoring.py`
- `def compute_quality_score(devcard: DevCard) -> None` (mutates quality.score)
- Weighted composite: `tests*0.3 + ci*0.25 + docs*0.2 + license*0.15 + linter*0.1`
- Already computed in quality extractor, but this analyzer can recalculate if needed

### Wire into pipeline
- After all extractors complete and DevCard is assembled:
  1. `devcard.expertise.profile_type = analyze_developer_type(devcard)`
  2. `classify_projects(devcard)`
  3. `devcard.collaboration.contribution_style = analyze_contribution_style(devcard)`
  4. `compute_quality_score(devcard)` (if not already done in extractor)

---

## Phase G: Renderers

### G1: Terminal renderer — `renderers/terminal.py`
- `def render_terminal(devcard: DevCard) -> str` (returns Rich-formatted string via Console capture)
- Sections (each a Rich Panel or Table):
  - **Header**: name, @username, bio, profile type badge, location
  - **Languages**: horizontal bars with colors, percentage labels
  - **Stack**: pills grouped by category (framework, library, db, tool...)
  - **Quality**: mini-bars for each metric (CI, tests, docs, license, linter) + composite score
  - **Focus Areas**: tag-style with confidence percentage
  - **Activity**: status indicator (colored), peak hours, streak info
  - **Top Projects**: Rich Table with name, stars, forks, language, status columns
  - **Footer**: generation timestamp, devcard version

### G1 cont: JSON/YAML output
- `output/json_output.py` — already stubbed in Phase D, finalize with `$schema` field
- `output/yaml_output.py` — `def to_yaml(devcard: DevCard) -> str` using `yaml.dump(devcard.model_dump(exclude_none=True))`

### G1 cont: Validator — `validators/schema_validator.py`
- `def validate_devcard(data: dict, schema_path: Path | None = None) -> list[str]`
- Loads schema from `schema/devcard.v1.schema.json` (default)
- Uses `jsonschema.validate()`, returns list of error messages (empty = valid)

### G1 cont: CLI updates
- Default output: terminal + JSON file
- `--format` choices: `json`, `yaml`, `terminal`, `svg`, `all`
- `devcard validate <file>` command
- Progress spinner during generation (Rich status)

### G2: SVG Card Renderer

**`renderers/themes/base.py`** — Theme dataclass:
```
@dataclass
class Theme:
  name: str
  background: str      # hex color
  foreground: str       # hex for primary text
  secondary: str        # hex for secondary text
  accent: str           # hex for highlights
  border: str           # hex for card border
  border_radius: int    # px
  font_family: str      # system font stack
  font_mono: str        # monospace font stack
  bar_colors: list[str] # colors for language bars
  card_width: int = 495 # px (standard GitHub card width)
  card_padding: int = 25
```

**5 theme files** (each exports a `THEME` constant):
- `default.py` — light: white bg, dark text, blue accent
- `dark.py` — dark: #0d1117 bg (GitHub dark), white text, cyan accent
- `minimal.py` — monochrome: white bg, black text, gray accent
- `neon.py` — dark bg, bright neon colors (pink/cyan/green accents)
- `terminal_green.py` — black bg, green mono text, terminal aesthetic

**`renderers/svg_card.py`**:
- `def render_svg(devcard: DevCard, theme: Theme | None = None) -> str`
- Build SVG as f-strings (no XML library needed)
- Root element: `<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">`
- Embedded `<style>` block with CSS animations (fade-in for sections)
- System fonts only: `"Segoe UI", Ubuntu, "Helvetica Neue", sans-serif` for body, `"SF Mono", "Cascadia Code", Consolas, monospace` for code
- Sections (vertical stack, each calculates its own height):
  1. Header: name, @username, profile type badge
  2. Language DNA: colored horizontal bars proportional to percentage
  3. Stack pills: rounded rects with text
  4. Quality indicators: mini progress bars
  5. Focus areas: tag-style rounded rects
  6. Top projects: compact list with star counts
  7. Footer: "Generated by devcard" + timestamp
- Dynamic height: each section function returns `(svg_fragment, height)`, total viewBox height = sum
- **LINGUIST_COLORS dict**: hardcoded hex colors for top 30 languages (Python=#3572A5, JavaScript=#f1e05a, TypeScript=#3178c6, etc.)
- Avatar: colored circle with user's initials (no external image)
- Target: under 30KB output

### CLI SVG wiring
- `--format svg` option
- `--theme` option: choices from theme names
- `-o` flag: if not provided, write `{username}.svg` to current dir

---

## Phase H: Polish + Tests

### Additional CLI commands
- `devcard me` — detect username from `git config user.name` + `gh api user`, then call generate
- `devcard compare <user1> <user2>` — generate both, render side-by-side terminal comparison (Rich Columns)

### Test fixtures — `tests/fixtures/`
- `user_torvalds.json` — mock GitHubUser response
- `repos_torvalds.json` — mock repos list (5-10 repos)
- `repo_languages_linux.json` — mock languages response
- `repo_contents_linux.json` — mock root directory listing
- `events_torvalds.json` — mock events response
- `orgs_torvalds.json` — mock orgs response
- Also: a minimal user fixture (user with 0 repos) for edge case testing

### Tests
- **Extractor tests**: one test file per extractor, using `httpx.MockTransport` with fixture JSON. Assert returned model has expected values, assert None on API failure.
- **Analyzer tests**: construct Pydantic models directly, pass to analyzers, assert correct classifications.
- **Renderer tests**: render a fully-populated DevCard, assert terminal output contains expected sections, assert SVG is valid XML with no foreignObject and under 50KB.
- **Integration test**: full pipeline with all API calls mocked, validate output against JSON schema. Mark `@pytest.mark.slow`.
- **CLI tests**: `CliRunner` to test `generate`, `validate`, `me` commands with mocked pipeline.

---

## End-to-End Verification

1. `uv run devcard generate torvalds --token $GITHUB_TOKEN` — produces JSON + terminal + SVG
2. `uv run devcard validate <generated.json>` — passes
3. SVG opens correctly in browser
4. `uv run pytest` — all pass
5. `uv run ruff check src/ tests/` — clean
