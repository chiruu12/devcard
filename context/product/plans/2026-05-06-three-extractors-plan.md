# Plan: Three New Extractors — Coding Habits, Code Review, Lines Changed

## Context

DevCard now has notable contributions (PR #9). We're adding 3 more extraction signals inspired by lowlighter/metrics to enrich developer profiles with coding style, review activity, and productivity metrics.

## Feature A: Coding Habits Extractor

### Model (`models.py`)
```python
class CodingHabits(BaseModel):
    indentation: Literal["spaces", "tabs", "mixed"] | None = Field(...)
    spaces_count: int = Field(default=0)
    tabs_count: int = Field(default=0)
    avg_line_length: float | None = Field(default=None)
    lines_analyzed: int = Field(default=0)
```
Add `coding_habits: CodingHabits | None` to `DevCard`.

### Client method (`github/client.py`)
```python
async def get_commit_detail(self, owner: str, repo: str, sha: str) -> dict | None
```
Calls `GET /repos/{owner}/{repo}/commits/{sha}`, returns files with patches.

### Extractor (`extractors/habits.py`)
- From events (already fetched), find up to 10 recent PushEvent commits
- Fetch commit diffs via `get_commit_detail`
- Analyze `+` lines in patches: count leading tabs vs spaces, measure line lengths
- Return `CodingHabits`

### Pipeline wiring
Add to concurrent `asyncio.gather` in `generate_devcard`, attach to `devcard.coding_habits`.

### Rendering
- Terminal: "Coding Habits" panel with indentation style, avg line length
- Markdown: "Coding Habits" section

### Tests
- Mock commit diff responses
- Test tabs detection, spaces detection, mixed
- Test avg line length calculation
- Test empty patches (return None gracefully)

## Feature B: Code Review Activity Extractor

### Model (`models.py`)
```python
class ReviewActivity(BaseModel):
    reviews_given: int = Field(default=0)
    approved: int = Field(default=0)
    changes_requested: int = Field(default=0)
    commented: int = Field(default=0)
    repos_reviewed: list[str] = Field(default_factory=list)
```
Add `review_activity: ReviewActivity | None` to `Collaboration`.

### Extractor (`extractors/reviews.py`)
- Filter existing events for `PullRequestReviewEvent`
- Count by `payload.review.state`: approved, changes_requested, commented, dismissed
- Track unique repo names reviewed
- Zero additional API calls

### Pipeline wiring
Run concurrently, attach to `devcard.collaboration.review_activity` (with same null-safety as notable).

### Rendering
- Terminal: "Code Reviews" panel with counts
- Markdown: "Code Reviews" section

### Tests
- Mock PullRequestReviewEvent events
- Test counting by state
- Test repos_reviewed deduplication
- Test no review events → None

## Feature C: Lines Changed Extractor

### Model (`models.py`)
```python
class RepoLines(BaseModel):
    repo: str = Field(description="Repository name")
    added: int = Field(default=0)
    deleted: int = Field(default=0)

class LinesChanged(BaseModel):
    total_added: int = Field(default=0)
    total_deleted: int = Field(default=0)
    by_repo: list[RepoLines] = Field(default_factory=list)
```
Add `lines_changed: LinesChanged | None` to `DevCard`.

### Client method (`github/client.py`)
```python
async def get_contributor_stats(self, owner: str, repo: str) -> list[dict]
```
Calls `GET /repos/{owner}/{repo}/stats/contributors`, returns list of contributor stats.

### Extractor (`extractors/lines.py`)
- For top 10 repos (by stars), fetch contributor stats
- Filter for the user's login
- Sum weekly additions/deletions
- Return sorted by total activity (added + deleted)

### Pipeline wiring
Add to concurrent `asyncio.gather`, attach to `devcard.lines_changed`.

### Rendering
- Terminal: "Lines Changed" panel with totals and top repos
- Markdown: "Lines Changed" section with table

### Tests
- Mock contributor stats responses
- Test user filtering
- Test aggregation across repos
- Test empty stats → None

## Implementation Order

All 3 can be implemented in parallel since they're independent:
1. Models for all 3 (single commit)
2. Client methods (habits + lines, single commit)
3. Extractors (3 parallel, separate commits)
4. Pipeline wiring (single commit)
5. Renderers (single commit)
6. Tests (3 files, single commit)
7. Schema update (single commit)

## Verification

1. `uv run pytest tests/` — all pass
2. `uv run ruff check src/ tests/` — clean
3. `uv run devcard generate <username>` — all 3 new sections appear
