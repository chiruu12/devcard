# DevCard V2: Review Triage & PR Plan

## Context

We received a 15-point review of DevCard's current output quality. Before building anything, we need to separate signal from noise — several items are already implemented, some are API-infeasible, and a few are genuinely high-impact. The strategy is: create a `v2` branch, land small focused PRs into it, then merge `v2` → `main` for release.

---

## Review Triage

### Already Done (reviewer didn't check the code)

| # | Claim | Reality |
|---|-------|---------|
| 7 | "Agent format needed" | `agent_card.py` + `curated.py` already ship a compact key:value agent format |
| 8 | "llms.txt needed" | `llms_txt.py` already implements the llmstxt.org spec |
| 9 | "SVG card renderer needed" | `svg_card.py` is production-ready: 5 themes, GitHub-safe, <30KB, tested |
| 13 | "Error handling & rate limits" | Graceful None-on-failure, diskcache, semaphore(10), rate-limit sleep already in place |
| 1a | "Split logic vs presentation languages" | `languages.py` already weights: Jupyter at 5%, markup at 10%, Dockerfile at 0% |

### Wrong Signal / API-Infeasible

| # | Suggestion | Why it's wrong |
|---|-----------|---------------|
| 1b | "Detect language trends over time" | GitHub Events API only returns last 300 events (~30 days). No historical language data per-repo over time. Repo `created_at` + primary language gives a very rough signal but it's unreliable (repos change languages). **Skip.** |
| 3b | "Scan commit messages for domain keywords" | Would require fetching commits per repo — at 30 repos × 30 commits = 900 extra API calls. Blows the 60-call unauthenticated budget and even with auth is wasteful for marginal signal. **Skip.** |
| 3c | "Check for model-training scripts (train.py, model.py)" | We already have root_listings. We could check for these filenames cheaply. **Worth doing** as part of skill-depth PR — low-cost, adds signal. |
| 11 | "GitHub Action" | Separate distribution concern, not a quality improvement. Do after V2 core is solid. **Defer.** |
| 12 | "MCP server wrapper" | Separate project. **Defer.** |
| 14 | "CONTRIBUTING.md" | Community concern, not output quality. **Defer.** |
| 15 | "SCHEMA.md / THEMES.md" | Documentation. Nice but doesn't improve output. **Defer.** |

### High-Impact Improvements (V2 scope)

| # | Item | Impact | Effort |
|---|------|--------|--------|
| 2 | **Signature project + narrative** | Adds personality, makes card memorable | Medium |
| 3a | **Starred repos for interests** + skill levels | Boosts domain confidence above 0.7, adds depth | Medium |
| 3c | **File-pattern domain signals** (train.py etc.) | Cheap boost to expertise accuracy | Small |
| 4 | **Oscillation Score + text sparkline** | Replaces vague "low consistency" label | Medium |
| 5 | **Maintainer detection** (repos with external contributors) | Enriches collaboration profile | Small |
| 6 | **Per-project quality breakdown + recommendations** | Actionable output, not just a number | Medium |
| 10 | **Compare command** | Viral feature, side-by-side diff | Large |

---

## PR Plan (ordered by dependency & impact)

### PR 1: Language DNA improvements
**Files:** `src/devcard/extractors/languages.py`, `src/devcard/models.py`, renderers
- Expose the logic/presentation split explicitly in the model (add `category: Literal["logic", "presentation", "markup", "data"]` to `Language`)
- Show "coding ratio" — percentage of logic-only languages vs total
- Improve how renderers surface this (e.g., terminal shows "92% logic code")

### PR 2: Signature project + project narratives
**Files:** `src/devcard/extractors/projects.py`, `src/devcard/analyzers/project_classifier.py`, `src/devcard/models.py`, renderers
- Add `is_signature: bool` to `Project` model
- Heuristic: highest composite score (stars*3 + complexity signals + internal reuse)
- Add `narrative: str | None` to `Project` — one-line heuristic description (e.g., "Deep ML foundations — custom training pipeline with 500+ stars")
- Narrative built from: classification + domain + top language + star count
- Add `config` classification type to project_classifier

### PR 3: Skill-depth signals (starred repos + file patterns + skill levels)
**Files:** `src/devcard/github/client.py`, `src/devcard/extractors/expertise.py`, `src/devcard/models.py`, mappings
- Add `get_starred_repos(username, limit=100)` to GitHub client
- Use starred repos as interest signal (topics from starred repos → domain confidence boost of 0.4)
- Scan root_listings for domain-indicator files (train.py, model.py, Makefile, deploy.yaml, etc.) → confidence boost
- Add `skill_level: Literal["beginner", "intermediate", "advanced", "expert"]` to `Domain` model
- Level heuristic: beginner (<3 packages in domain), intermediate (3-8), advanced (8-15 + projects), expert (15+ packages + high-star projects)

### PR 4: Activity oscillation score + sparkline
**Files:** `src/devcard/extractors/activity.py`, `src/devcard/models.py`, `src/devcard/renderers/terminal.py`, `src/devcard/output/curated.py`
- Add `consistency_score: int` (0-100) to `Activity` model, computed from heatmap std deviation (upgrade existing `_compute_consistency()` from curated.py into the extractor)
- Add `consistency_description: str` (e.g., "bursty, heavy Tuesdays & Fridays")
- Generate description from: peak days + peak hours + score bucket
- Add text sparkline to terminal renderer: `Mon ▁▃▇▅▂▁▁ Sun` using heatmap row sums

### PR 5: Maintainer detection + collaboration enrichment
**Files:** `src/devcard/extractors/collaboration.py`, `src/devcard/models.py`
- For repos with >1 contributor, check if user is an admin/owner → `is_maintainer: bool` on repos
- Count repos where user is maintainer + repo has external contributors
- Add `maintained_projects_with_contributors: int` to Collaboration model
- Improve contribution_style analyzer to use this signal

### PR 6: Per-project quality + recommendations
**Files:** `src/devcard/extractors/quality.py`, `src/devcard/models.py`, renderers
- Expose existing per-repo `QualityDetail` data in outputs (it's computed but hidden)
- Add `recommendations: list[str]` to Quality model
- Generate tips from gaps: "Add CI to ProjectX — no GitHub Actions found", "Add tests to ProjectY"
- Terminal renderer shows top 3 recommendations
- SVG/markdown show recommendations section

### PR 7: Compare command
**Files:** `src/devcard/cli.py`, `src/devcard/renderers/terminal.py` (new compare renderer)
- `devcard compare user1 user2` CLI command
- Runs two pipelines concurrently
- Side-by-side terminal output using Rich Columns
- Highlights: language overlap/differences, domain overlap, quality score comparison, activity comparison
- JSON format: outputs both cards + diff summary

---

## Verification

For each PR:
1. `uv run pytest` — all tests pass
2. `uv run ruff check src/ tests/` — clean
3. New features have tests (~80% coverage of new code)
4. Manual test: `uv run devcard generate chiruu12 --format terminal` shows the new data
5. SVG still renders correctly and stays under 30KB

For V2 release:
- `v2` branch merged to `main`
- All 7 PRs landed and tested together
- Run against 3-4 diverse profiles (ML dev, frontend dev, full-stack, systems programmer) to verify quality

---

## What we're NOT doing in V2

- Language trends over time (API limitation)
- Commit message scanning (too many API calls)
- GitHub Action (separate distribution concern)
- MCP server (separate project)
- CONTRIBUTING.md, SCHEMA.md, THEMES.md (post-V2 docs sprint)
