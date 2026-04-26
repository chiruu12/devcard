# DevCard v2: Agent-Ready Quality Improvements

## Context

DevCard v1 works end-to-end but produces misleading signals. Jupyter Notebook dominates language stats (96% for a Python ML dev), org contributions are invisible, projects are padded with dead repos, and the dev type classifier is too strict. A hiring agent reading the current output would misjudge the developer.

## Changes

### 1. Language Intelligence — Jupyter Notebook 5% weight

Jupyter Notebook bytes in GitHub's language API include base64-encoded images, HTML output cells, JSON metadata — only ~5% is actual executable code. Apply a 0.05x multiplier to Jupyter Notebook bytes before calculating percentages.

- Add `LANGUAGE_BYTE_WEIGHTS` dict in `extractors/languages.py`
- `{"Jupyter Notebook": 0.05}` — apply before percentage calculation
- All other languages default to 1.0x
- Result: Python becomes the primary language for notebook-heavy profiles

### 2. Org Contribution Details

New `org_contributions` field in the `collaboration` model. For each org the user belongs to, query the GitHub Search API for the user's PRs and issues in that org.

- New model: `OrgContribution(org: str, prs_opened: int, prs_merged: int, issues_opened: int, commits: int)`
- New field: `Collaboration.org_contributions: list[OrgContribution]`
- Fetch via: `GET /search/issues?q=author:{user}+org:{org}+type:pr` and `+type:issue`
- New client methods: `search_user_prs_in_org()`, `search_user_issues_in_org()`
- Add to schema: `org_contributions` array in Collaboration $def
- Pipeline: after fetching orgs, fan out search queries per org

### 3. Project Quality Filter

Replace "top 10 by score" with "top 5 high-signal projects."

- Filter OUT: repos with (no description AND no stars AND status in [stale, archived])
- Filter OUT: repos where name contains "assignment", "homework" and stars == 0
- Cap at 5 instead of 10
- Boost scoring: repos with description get +5, repos with topics get +3, repos with detected dep files get +3

### 4. Dev Type Rules — Relaxed Matching

Current rules require ALL conditions to match (AND). Change to: each condition group is scored, and if total score exceeds a threshold, the type matches.

Simpler approach: split compound rules into separate entries. E.g., the ML rule becomes:
- Rule: topics include ML terms → "ml"
- Rule: stack includes ML frameworks → "ml"
- Rule: primary language Python + stack includes ML libs → "ml"

First match still wins, but each rule is easier to satisfy individually.

### 5. Auto-Generated Summary

New field: `DevCard.summary: str | None` — a one-liner built from extracted data, no LLM.

Template: `"{profile_type} specializing in {primary_language}. {top_project_sentence}. {org_sentence}. {activity_status}, ~{commits}/year."`

Generated in pipeline after all extractors and analyzers complete.

## Files to Modify

| File | Change |
|------|--------|
| `src/devcard/extractors/languages.py` | Add LANGUAGE_BYTE_WEIGHTS, apply before % calc |
| `src/devcard/extractors/projects.py` | Quality filter, cap at 5, boost scoring |
| `src/devcard/extractors/collaboration.py` | Fetch org contributions via search API |
| `src/devcard/models.py` | Add OrgContribution model, summary field |
| `src/devcard/github/client.py` | Add search_user_prs_in_org, search_user_issues_in_org |
| `src/devcard/pipeline.py` | Wire org contributions, generate summary |
| `src/devcard/analyzers/developer_type.py` | Split compound rules |
| `mappings/dev_type_rules.yaml` | Break AND rules into separate OR entries |
| `schema/devcard.v1.schema.json` | Add org_contributions, summary |
| `src/devcard/renderers/terminal.py` | Show org contributions, summary |
| `src/devcard/renderers/svg_card.py` | Show summary in header area |
| Tests | Update for new fields and behavior |

## Verification

1. `devcard generate chiruu12` — Python is primary language, not Jupyter Notebook
2. `devcard generate chiruu12` — profile_type is "ml" not "full_stack"
3. `devcard generate chiruu12` — org contributions show Jenkins PRs/issues
4. `devcard generate chiruu12` — projects are 5 high-signal repos, no dead assignments
5. `devcard generate chiruu12` — summary reads naturally for an agent
6. `uv run pytest` — all tests pass
7. `uv run ruff check src/ tests/` — clean
