# DevCard v2 Quality Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make DevCard output truthful and agent-ready — fix Jupyter Notebook inflation, add org contributions, filter projects to high-signal only, relax dev type rules, generate auto-summary.

**Architecture:** Five independent changes to extractors/analyzers/models/pipeline. Each can be tested in isolation. Changes flow: models first (new fields), then extractors/analyzers (new logic), then pipeline (wiring), then renderers (display).

**Tech Stack:** Python, Pydantic, async httpx, GitHub Search API (`/search/issues`)

---

### Task 1: Add new models — OrgContribution + summary field

**Files:**
- Modify: `src/devcard/models.py`

**Step 1: Add OrgContribution model after Collaboration class (~line 159)**

```python
class OrgContribution(BaseModel):
    org: str = Field(description="GitHub organization login name")
    prs_opened: int = Field(default=0, description="Pull requests opened in this org's repos")
    prs_merged: int = Field(default=0, description="Pull requests merged in this org's repos")
    issues_opened: int = Field(default=0, description="Issues opened in this org's repos")
    commits: int = Field(default=0, description="Commits to this org's repos (estimated)")
```

**Step 2: Add org_contributions field to Collaboration**

```python
# Add after external_contributions field:
org_contributions: list[OrgContribution] = Field(
    default_factory=list,
    description="Detailed contribution breakdown per organization",
)
```

**Step 3: Add summary field to DevCard**

```python
# Add after enriched field:
summary: str | None = Field(
    default=None,
    description="Auto-generated one-line developer summary for agent consumption",
)
```

**Step 4: Run tests**

Run: `uv run pytest tests/ -q`
Expected: All existing tests still pass (new fields have defaults).

**Step 5: Commit**

```bash
git add src/devcard/models.py
git commit -m "feat: add OrgContribution model and summary field to DevCard"
```

---

### Task 2: Jupyter Notebook language weight (5%)

**Files:**
- Modify: `src/devcard/extractors/languages.py`
- Modify: `tests/test_extractors/test_languages.py`

**Step 1: Write the failing test**

Add to `tests/test_extractors/test_languages.py`:

```python
def test_jupyter_notebook_penalized():
    """Jupyter Notebook bytes should be weighted at 5% to reflect actual code content."""
    from devcard.extractors.languages import LANGUAGE_BYTE_WEIGHTS
    assert "Jupyter Notebook" in LANGUAGE_BYTE_WEIGHTS
    assert LANGUAGE_BYTE_WEIGHTS["Jupyter Notebook"] == 0.05
```

And add an async integration test with mock data where Jupyter dominates:

```python
LANG_RESPONSES_NOTEBOOK = {
    "/repos/testdev/nb-repo/languages": {"Jupyter Notebook": 1000000, "Python": 50000},
}

# ... (create mock transport + client for this)

async def test_jupyter_penalized_in_percentages(client_notebook, user, repos_notebook):
    result = await extract_languages(client_notebook, user, repos_notebook)
    assert result is not None
    python = next(l for l in result if l.name == "Python")
    jupyter = next(l for l in result if l.name == "Jupyter Notebook")
    # With 5% weight: Jupyter 1M*0.05=50K, Python 50K → each ~50%
    assert python.percentage > jupyter.percentage or abs(python.percentage - jupyter.percentage) < 10
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_extractors/test_languages.py -v`
Expected: FAIL — LANGUAGE_BYTE_WEIGHTS doesn't exist yet

**Step 3: Implement — add weight dict and apply in extract_languages**

In `src/devcard/extractors/languages.py`, add after LINGUIST_COLORS dict:

```python
LANGUAGE_BYTE_WEIGHTS: dict[str, float] = {
    "Jupyter Notebook": 0.05,
}
```

Then modify the aggregation loop (around line 61-62):

```python
        for lang, bytes_count in result.items():
            weight = LANGUAGE_BYTE_WEIGHTS.get(lang, 1.0)
            weighted = int(bytes_count * weight)
            totals[lang] = totals.get(lang, 0) + weighted
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_extractors/test_languages.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/devcard/extractors/languages.py tests/test_extractors/test_languages.py
git commit -m "feat: penalize Jupyter Notebook to 5% weight in language stats"
```

---

### Task 3: Project quality filter

**Files:**
- Modify: `src/devcard/extractors/projects.py`
- Modify: `tests/test_extractors/test_projects.py`

**Step 1: Write the failing test**

Add to `tests/test_extractors/test_projects.py`:

```python
async def test_projects_filters_noise():
    """Repos with no description, no stars, and stale should be filtered out."""
    user = GitHubUser(login="testdev")
    repos = [
        GitHubRepo(
            name="good-project", full_name="testdev/good-project",
            html_url="https://github.com/testdev/good-project",
            description="A real project", stargazers_count=5,
            pushed_at="2026-04-01T00:00:00Z", created_at="2024-01-01T00:00:00Z",
        ),
        GitHubRepo(
            name="homework-1", full_name="testdev/homework-1",
            html_url="https://github.com/testdev/homework-1",
            stargazers_count=0,
            pushed_at="2024-01-01T00:00:00Z", created_at="2023-06-01T00:00:00Z",
        ),
        GitHubRepo(
            name="dead-repo", full_name="testdev/dead-repo",
            html_url="https://github.com/testdev/dead-repo",
            stargazers_count=0,
            pushed_at="2023-01-01T00:00:00Z", created_at="2022-01-01T00:00:00Z",
        ),
    ]
    result = await extract_projects(None, user, repos)
    assert result is not None
    names = [p.name for p in result]
    assert "good-project" in names
    assert "homework-1" not in names
    assert "dead-repo" not in names


async def test_projects_caps_at_5():
    user = GitHubUser(login="testdev")
    repos = [
        GitHubRepo(
            name=f"repo-{i}", full_name=f"testdev/repo-{i}",
            html_url=f"https://github.com/testdev/repo-{i}",
            description="Has description", stargazers_count=10 - i,
            pushed_at="2026-04-01T00:00:00Z", created_at="2024-01-01T00:00:00Z",
        )
        for i in range(8)
    ]
    result = await extract_projects(None, user, repos)
    assert result is not None
    assert len(result) <= 5
```

**Step 2: Run to verify failure**

Run: `uv run pytest tests/test_extractors/test_projects.py::test_projects_filters_noise -v`

**Step 3: Implement filter logic**

In `src/devcard/extractors/projects.py`, modify `extract_projects`:

```python
_NOISE_KEYWORDS = {"assignment", "homework", "tutorial", "starter", "template", "boilerplate"}

def _is_noise(repo: GitHubRepo, now: datetime) -> bool:
    name_lower = repo.name.lower().replace("-", " ").replace("_", " ")
    if repo.stargazers_count == 0 and any(kw in name_lower for kw in _NOISE_KEYWORDS):
        return True
    if (not repo.description and repo.stargazers_count == 0
            and _status(repo, now) in ("archived", "stale")):
        return True
    return False
```

Update scoring to boost repos with description/topics:

```python
recency = _recency_bonus(repo, now)
desc_bonus = 5 if repo.description else 0
topic_bonus = 3 if repo.topics else 0
score = repo.stargazers_count * 3 + repo.forks_count * 2 + recency + desc_bonus + topic_bonus
```

Change `scored[:10]` to `scored[:5]`.

Add the noise filter before scoring:

```python
for repo in repos:
    if repo.fork or _is_noise(repo, now):
        continue
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_extractors/test_projects.py -v`

**Step 5: Commit**

```bash
git add src/devcard/extractors/projects.py tests/test_extractors/test_projects.py
git commit -m "feat: filter noisy projects, cap at 5, boost repos with descriptions"
```

---

### Task 4: Org contributions via GitHub Search API

**Files:**
- Modify: `src/devcard/github/client.py`
- Modify: `src/devcard/extractors/collaboration.py`
- Modify: `src/devcard/pipeline.py`

**Step 1: Add search methods to GitHubClient**

In `src/devcard/github/client.py`, add:

```python
async def search_user_prs_in_org(self, username: str, org: str) -> dict:
    url = f"/search/issues?q=author:{username}+org:{org}+type:pr&per_page=1"
    try:
        data = await self._request(url)
        total = data.get("total_count", 0) if isinstance(data, dict) else 0
        merged_url = f"/search/issues?q=author:{username}+org:{org}+type:pr+is:merged&per_page=1"
        merged_data = await self._request(merged_url)
        merged = merged_data.get("total_count", 0) if isinstance(merged_data, dict) else 0
        return {"total": total, "merged": merged}
    except GitHubAPIError:
        return {"total": 0, "merged": 0}

async def search_user_issues_in_org(self, username: str, org: str) -> int:
    url = f"/search/issues?q=author:{username}+org:{org}+type:issue&per_page=1"
    try:
        data = await self._request(url)
        return data.get("total_count", 0) if isinstance(data, dict) else 0
    except GitHubAPIError:
        return 0
```

**Step 2: Update collaboration extractor**

In `src/devcard/extractors/collaboration.py`, add org contribution fetching:

```python
from devcard.models import Collaboration, OrgContribution

# Inside extract_collaboration, after fetching orgs:
org_contribs = []
for org in orgs:
    try:
        pr_data = await client.search_user_prs_in_org(user.login, org)
        issue_count = await client.search_user_issues_in_org(user.login, org)
        if pr_data["total"] > 0 or issue_count > 0:
            org_contribs.append(OrgContribution(
                org=org,
                prs_opened=pr_data["total"],
                prs_merged=pr_data["merged"],
                issues_opened=issue_count,
            ))
    except Exception:
        logger.warning("Failed to fetch org contributions for %s/%s", user.login, org)

return Collaboration(
    organizations=orgs,
    pull_requests_opened=pr_count,
    issues_opened=issue_count,
    external_contributions=external_count,
    org_contributions=org_contribs,
)
```

**Step 3: Run tests**

Run: `uv run pytest tests/ -q`

**Step 4: Commit**

```bash
git add src/devcard/github/client.py src/devcard/extractors/collaboration.py
git commit -m "feat: fetch org contribution details via GitHub Search API"
```

---

### Task 5: Relax dev type rules

**Files:**
- Modify: `mappings/dev_type_rules.yaml`
- Modify: `tests/test_analyzers.py`

**Step 1: Write the failing test**

Add to `tests/test_analyzers.py`:

```python
def test_ml_user_stack_only(self):
    """ML classification should work from stack alone, without topics."""
    card = _make_devcard(
        languages=[Language(name="Python", percentage=70.0)],
        projects=[Project(name="my-model")],
        stack=Stack(frameworks=[StackItem(name="PyTorch", category="framework")]),
        expertise=Expertise(),
    )
    assert analyze_developer_type(card) == "ml"
```

**Step 2: Rewrite dev_type_rules.yaml — split compound rules into separate entries**

```yaml
rules:
  # ML — any one signal is enough
  - conditions:
      topics_include_any: ["machine-learning", "deep-learning", "neural-network", "nlp", "computer-vision", "tensorflow", "pytorch", "generative-ai", "llm"]
    type: "ml"
  - conditions:
      stack_includes_any: ["tensorflow", "torch", "keras", "transformers", "scikit-learn", "openai", "anthropic", "langchain", "litellm", "huggingface-hub", "pytorch"]
    type: "ml"

  # Data — any one signal
  - conditions:
      topics_include_any: ["data-science", "data-analysis", "data-engineering", "data-visualization", "analytics", "pandas", "big-data", "etl"]
    type: "data"
  - conditions:
      stack_includes_any: ["pandas", "polars", "numpy", "scipy", "matplotlib", "plotly", "dash", "dask", "airflow", "mlflow"]
      primary_language: ["python", "r", "julia"]
    type: "data"

  # Embedded
  - conditions:
      topics_include_any: ["embedded", "firmware", "arduino", "iot", "rtos", "microcontroller"]
    type: "embedded"

  # Systems
  - conditions:
      topics_include_any: ["operating-system", "kernel", "compiler", "low-level", "systems-programming"]
    type: "systems"
  - conditions:
      primary_language: ["c", "c++", "rust", "zig"]
      topics_include_any: ["operating-system", "kernel", "compiler", "low-level"]
    type: "systems"

  # Security
  - conditions:
      topics_include_any: ["security", "cyber-security", "penetration-testing", "cryptography", "hacking", "reverse-engineering", "encryption", "privacy"]
    type: "security"

  # DevOps
  - conditions:
      topics_include_any: ["devops", "infrastructure", "ci-cd", "kubernetes", "docker", "terraform", "monitoring", "observability", "cloud-native", "serverless"]
    type: "devops"
  - conditions:
      stack_includes_any: ["ansible", "terraform", "kubernetes/client-go", "prometheus"]
    type: "devops"

  # Mobile
  - conditions:
      topics_include_any: ["android", "ios", "mobile", "react-native", "flutter", "swift"]
    type: "mobile"
  - conditions:
      stack_includes_any: ["swiftui", "uikit", "compose", "room", "retrofit", "alamofire"]
    type: "mobile"

  # Frontend
  - conditions:
      topics_include_any: ["react", "vue", "angular", "svelte", "frontend", "css", "html", "jamstack", "browser-extension"]
    type: "frontend"
  - conditions:
      stack_includes_any: ["react", "vue", "angular", "svelte", "next", "nuxt", "tailwindcss", "styled-components"]
    type: "frontend"
  - conditions:
      language_ratio_above:
        javascript: 0.5
        typescript: 0.5
    type: "frontend"

  # Backend
  - conditions:
      topics_include_any: ["api", "rest-api", "graphql", "microservices", "backend", "grpc"]
    type: "backend"
  - conditions:
      stack_includes_any: ["express", "fastify", "django", "flask", "fastapi", "gin", "echo", "spring-boot", "nestjs"]
    type: "backend"

  # Researcher
  - conditions:
      topics_include_any: ["research", "paper", "academic", "science", "phd"]
    type: "researcher"

  # Default
  - conditions: {}
    type: "full_stack"
```

**Step 3: Run tests**

Run: `uv run pytest tests/test_analyzers.py -v`

**Step 4: Commit**

```bash
git add mappings/dev_type_rules.yaml tests/test_analyzers.py
git commit -m "feat: relax dev type rules — split AND conditions into separate OR entries"
```

---

### Task 6: Auto-generated summary

**Files:**
- Modify: `src/devcard/pipeline.py`

**Step 1: Add summary generation function**

```python
def _generate_summary(devcard: DevCard) -> str:
    parts = []

    profile = devcard.expertise.profile_type if devcard.expertise else "developer"
    profile_display = profile.replace("_", " ").title() if profile else "Developer"
    primary_lang = devcard.languages[0].name if devcard.languages else None

    if primary_lang:
        parts.append(f"{profile_display} specializing in {primary_lang}")
    else:
        parts.append(profile_display)

    top_projects = [p for p in devcard.projects[:2] if p.stars > 0 or p.description]
    if top_projects:
        proj_strs = []
        for p in top_projects:
            if p.description and len(p.description) < 60:
                proj_strs.append(f"{p.name} ({p.description})")
            else:
                proj_strs.append(p.name)
        parts.append(f"Builds {', '.join(proj_strs)}")

    if devcard.collaboration and devcard.collaboration.org_contributions:
        top_org = devcard.collaboration.org_contributions[0]
        parts.append(f"Contributor at {top_org.org} ({top_org.prs_opened} PRs)")

    if devcard.activity:
        status = devcard.activity.status.title()
        commits = devcard.activity.commits_last_year
        if commits:
            parts.append(f"{status}, ~{commits:,} commits/year")
        else:
            parts.append(status)

    return ". ".join(parts) + "."
```

**Step 2: Wire into pipeline — after analyzers, before return**

```python
devcard.summary = _generate_summary(devcard)
```

**Step 3: Run tests**

Run: `uv run pytest tests/ -q`

**Step 4: Commit**

```bash
git add src/devcard/pipeline.py
git commit -m "feat: auto-generate one-line summary for agent consumption"
```

---

### Task 7: Update schema + renderers + regenerate gallery

**Files:**
- Modify: `schema/devcard.v1.schema.json`
- Modify: `src/devcard/renderers/terminal.py`
- Modify: `src/devcard/renderers/svg_card.py`

**Step 1: Add org_contributions and summary to JSON Schema**

Add `summary` property to top-level, add `org_contributions` inside Collaboration $def, add OrgContribution to $defs.

**Step 2: Update terminal renderer — show summary at top, org contributions in collab section**

**Step 3: Update SVG renderer — show summary below bio in header**

**Step 4: Regenerate gallery SVGs with new data**

```bash
uv run devcard generate karpathy --format svg --theme dark -o gallery/karpathy-dark.svg
# ... repeat for all themes + torvalds
```

**Step 5: Run full test suite + lint**

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
```

**Step 6: Commit**

```bash
git add schema/ src/devcard/renderers/ gallery/
git commit -m "feat: update schema, renderers, and gallery for v2 fields"
```

---

### Task 8: Final verification with real profiles

**Step 1: Test with chiruu12**

```bash
uv run devcard generate chiruu12 --format json 2>/dev/null | python3 -c "
import sys, json; d=json.load(sys.stdin)
print('Summary:', d.get('summary'))
print('Profile:', d.get('expertise',{}).get('profile_type'))
print('Top lang:', d.get('languages',[{}])[0].get('name'))
print('Projects:', len(d.get('projects',[])))
print('Org contribs:', d.get('collaboration',{}).get('org_contributions'))
"
```

Expected:
- Summary: meaningful one-liner mentioning ML/Python
- Profile type: "ml" (not "full_stack")
- Top language: "Python" (not "Jupyter Notebook")
- Projects: ≤5, no homework/assignments
- Org contributions: Jenkins PRs if available

**Step 2: Test with karpathy**

```bash
uv run devcard generate karpathy --format terminal
```

**Step 3: Push**

```bash
git push
```
