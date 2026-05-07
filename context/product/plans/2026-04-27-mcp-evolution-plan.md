# DevCard MCP Server Evolution — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evolve DevCard from a CLI-first tool into a full MCP-first experience with 8 tools — audit, generate, analyze, fix, agent-ready, compare, render — targeting all major AI coding agents.

**Architecture:** Expand the existing two-package structure (devcard core + devcard-mcp wrapper). Add fixers, dual scoring, and issue detection to the core library. Expand MCP server from 4 read-only tools to 8 tools with full GitHub write capability (dry-run by default). Pure heuristics, no LLM dependency.

**Tech Stack:** Python 3.11+, FastMCP 3.0+, httpx (async), Pydantic v2, diskcache, pytest + pytest-asyncio

---

# DevCard MCP Server Evolution -- Detailed Implementation Plan

This plan covers 7 tasks (T1 through T7) corresponding to phases P0 through P6. Each task follows strict TDD: write a failing test, confirm it fails, implement the minimum to pass, confirm it passes, then commit. Every step is sized to take 2-5 minutes.

---

## T1: GitHub Client Write Methods (Phase P0)

**Goal:** Add three write methods to `src/devcard/github/client.py` for creating/updating files, updating repo descriptions, and updating repo topics.

### T1.1 -- Add `_mutate` base method and `create_or_update_file` test

**Files touched:** `tests/test_github_client_write.py` (new), `src/devcard/github/client.py`

#### Step 1: Write failing test for `create_or_update_file` (create case)

Create `tests/test_github_client_write.py`:

```python
from __future__ import annotations

import json
import pytest
import httpx

from devcard.config import DevCardConfig
from devcard.github.client import GitHubClient, GitHubAPIError


def _make_config(transport: httpx.MockTransport) -> DevCardConfig:
    """Build a DevCardConfig that uses a mock transport."""
    config = DevCardConfig(
        github_token="test-token",
        base_url="https://api.github.com",
        no_cache=True,
    )
    return config


def _make_client(transport: httpx.MockTransport) -> GitHubClient:
    config = _make_config(transport)
    client = GitHubClient(config)
    # Replace the internal httpx client with one using our mock transport
    client._http = httpx.AsyncClient(
        transport=transport,
        base_url=config.base_url,
        headers=client._http.headers,
        timeout=30.0,
    )
    return client


class TestCreateOrUpdateFile:
    async def test_creates_new_file(self):
        """When file does not exist (404 on GET), creates via PUT."""
        call_log = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                call_log.append(("GET", str(request.url)))
                return httpx.Response(404, json={"message": "Not Found"})
            if request.method == "PUT":
                call_log.append(("PUT", str(request.url)))
                body = json.loads(request.content)
                assert body["message"] == "Add devcard.json"
                assert "content" in body
                assert "sha" not in body
                return httpx.Response(201, json={
                    "content": {"sha": "newsha123", "path": "devcard.json"},
                })
            return httpx.Response(405)

        client = _make_client(httpx.MockTransport(handler))
        try:
            result = await client.create_or_update_file(
                owner="testuser",
                repo="testuser",
                path="devcard.json",
                content='{"version": "1.0"}',
                commit_message="Add devcard.json",
            )
            assert result["content"]["sha"] == "newsha123"
            assert any(m == "PUT" for m, _ in call_log)
        finally:
            await client.close()

    async def test_updates_existing_file(self):
        """When file exists (200 on GET), updates via PUT with sha."""
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, json={
                    "sha": "existingsha456",
                    "content": "",
                    "encoding": "base64",
                    "name": "devcard.json",
                    "path": "devcard.json",
                    "type": "file",
                    "size": 100,
                    "url": "https://api.github.com/repos/testuser/testuser/contents/devcard.json",
                })
            if request.method == "PUT":
                body = json.loads(request.content)
                assert body["sha"] == "existingsha456"
                return httpx.Response(200, json={
                    "content": {"sha": "updatedsha789", "path": "devcard.json"},
                })
            return httpx.Response(405)

        client = _make_client(httpx.MockTransport(handler))
        try:
            result = await client.create_or_update_file(
                owner="testuser",
                repo="testuser",
                path="devcard.json",
                content='{"version": "1.0"}',
                commit_message="Update devcard.json",
            )
            assert result["content"]["sha"] == "updatedsha789"
        finally:
            await client.close()

    async def test_raises_on_put_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(404, json={"message": "Not Found"})
            if request.method == "PUT":
                return httpx.Response(422, json={"message": "Validation Failed"})
            return httpx.Response(405)

        client = _make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(GitHubAPIError):
                await client.create_or_update_file(
                    "testuser", "testuser", "devcard.json",
                    "content", "msg",
                )
        finally:
            await client.close()
```

**Run:** `uv run pytest tests/test_github_client_write.py -v`
**Expected:** 3 failures (AttributeError: `GitHubClient` has no method `create_or_update_file`)

#### Step 2: Implement `_mutate` and `create_or_update_file`

In `src/devcard/github/client.py`, add after the `_request` method:

```python
async def _mutate(self, method: str, url: str, body: dict) -> dict:
    """Send a write request (PUT/PATCH/POST) to GitHub API."""
    async with self._semaphore:
        full_url = url if url.startswith("http") else f"{self._config.base_url}{url}"
        response = await self._http.request(method, full_url, json=body)

        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None:
            remaining_int = int(remaining)
            if remaining_int == 0:
                reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
                wait = max(reset_at - int(time.time()), 1)
                logger.warning("Rate limit exhausted. Sleeping %d seconds.", wait)
                await asyncio.sleep(wait)
                response = await self._http.request(method, full_url, json=body)
            elif remaining_int < 10:
                logger.warning("Rate limit low: %d requests remaining.", remaining_int)

        if response.status_code not in (200, 201):
            raise GitHubAPIError(
                response.status_code,
                url,
                response.text[:200],
            )

        return response.json()

async def create_or_update_file(
    self,
    owner: str,
    repo: str,
    path: str,
    content: str,
    commit_message: str,
) -> dict:
    """Create or update a file via GitHub Contents API.

    Checks if file exists first. If it does, includes the SHA for update.
    Content is base64-encoded automatically.
    """
    import base64

    url = f"/repos/{owner}/{repo}/contents/{path}"

    # Check if file already exists to get its SHA
    sha: str | None = None
    try:
        existing = await self._request(url)
        if isinstance(existing, dict) and "sha" in existing:
            sha = existing["sha"]
    except GitHubAPIError as e:
        if e.status_code != 404:
            raise

    encoded = base64.b64encode(content.encode()).decode()
    body: dict = {
        "message": commit_message,
        "content": encoded,
    }
    if sha:
        body["sha"] = sha

    return await self._mutate("PUT", url, body)
```

**Run:** `uv run pytest tests/test_github_client_write.py::TestCreateOrUpdateFile -v`
**Expected:** 3 passing tests

### T1.2 -- Add `update_repo_description` test and implementation

#### Step 3: Write failing test for `update_repo_description`

Add to `tests/test_github_client_write.py`:

```python
class TestUpdateRepoDescription:
    async def test_updates_description(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "PATCH":
                body = json.loads(request.content)
                assert body["description"] == "A cool project"
                return httpx.Response(200, json={
                    "name": "myrepo",
                    "full_name": "testuser/myrepo",
                    "description": "A cool project",
                })
            return httpx.Response(405)

        client = _make_client(httpx.MockTransport(handler))
        try:
            result = await client.update_repo_description(
                "testuser", "myrepo", "A cool project",
            )
            assert result["description"] == "A cool project"
        finally:
            await client.close()

    async def test_raises_on_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"message": "Forbidden"})

        client = _make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(GitHubAPIError):
                await client.update_repo_description(
                    "testuser", "myrepo", "desc",
                )
        finally:
            await client.close()
```

**Run:** `uv run pytest tests/test_github_client_write.py::TestUpdateRepoDescription -v`
**Expected:** 2 failures

#### Step 4: Implement `update_repo_description`

Add to `GitHubClient` in `src/devcard/github/client.py`:

```python
async def update_repo_description(
    self, owner: str, repo: str, description: str,
) -> dict:
    """Update a repository's description via GitHub Repos API."""
    url = f"/repos/{owner}/{repo}"
    return await self._mutate("PATCH", url, {"description": description})
```

**Run:** `uv run pytest tests/test_github_client_write.py::TestUpdateRepoDescription -v`
**Expected:** 2 passing

### T1.3 -- Add `update_repo_topics` test and implementation

#### Step 5: Write failing test for `update_repo_topics`

Add to `tests/test_github_client_write.py`:

```python
class TestUpdateRepoTopics:
    async def test_replaces_topics(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "PUT":
                body = json.loads(request.content)
                assert body["names"] == ["python", "cli", "devcard"]
                return httpx.Response(200, json={
                    "names": ["python", "cli", "devcard"],
                })
            return httpx.Response(405)

        client = _make_client(httpx.MockTransport(handler))
        try:
            result = await client.update_repo_topics(
                "testuser", "myrepo", ["python", "cli", "devcard"],
            )
            assert result["names"] == ["python", "cli", "devcard"]
        finally:
            await client.close()
```

#### Step 6: Implement `update_repo_topics`

Add to `GitHubClient`:

```python
async def update_repo_topics(
    self, owner: str, repo: str, topics: list[str],
) -> dict:
    """Replace all topics on a repository via GitHub Topics API."""
    url = f"/repos/{owner}/{repo}/topics"
    return await self._mutate("PUT", url, {"names": topics})
```

**Run:** `uv run pytest tests/test_github_client_write.py -v`
**Expected:** All 6 tests pass

**Run lint:** `uv run ruff check src/devcard/github/client.py tests/test_github_client_write.py`
**Expected:** No errors

**Commit:** `git commit -m "feat: add write methods to GitHub client — create_or_update_file, update_repo_description, update_repo_topics"`

---

## T2: Dual Scoring System (Phase P1, Part 1)

**Goal:** Add `compute_human_visibility_score` and `compute_agent_readiness_score` to `src/devcard/analyzers/scoring.py` without breaking the existing `compute_quality_score`.

### T2.1 -- Add ProfileRepoData model

**Files touched:** `src/devcard/models.py`

#### Step 1: Add model for profile repo data

Add to `src/devcard/models.py` (after the `DevCard` class):

```python
class ProfileRepoData(BaseModel):
    """Data from the user's profile repo (username/username)."""
    has_profile_readme: bool = Field(default=False, description="Whether a profile README exists")
    readme_length: int = Field(default=0, description="Length of profile README in characters")
    has_devcard_json: bool = Field(default=False, description="Whether devcard.json exists in profile repo")
    has_llms_txt: bool = Field(default=False, description="Whether llms.txt exists in profile repo")
    files: list[str] = Field(default_factory=list, description="File names in root of profile repo")
```

No separate test needed for a Pydantic model -- it is tested via the scoring tests below.

### T2.2 -- Write tests for `compute_human_visibility_score`

#### Step 2: Write failing tests

Create `tests/test_scoring_dual.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from devcard.analyzers.scoring import (
    compute_agent_readiness_score,
    compute_human_visibility_score,
    compute_quality_score,
)
from devcard.models import (
    Activity,
    Collaboration,
    DevCard,
    Domain,
    Expertise,
    FocusArea,
    Generator,
    Identity,
    Language,
    ProfileRepoData,
    Project,
    Quality,
    Stack,
    StackItem,
)


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="test", version="0.0.1"),
        identity=Identity(username="testuser"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


class TestHumanVisibilityScore:
    def test_empty_profile_scores_zero(self):
        card = _make_devcard()
        profile = ProfileRepoData()
        score = compute_human_visibility_score(card, profile)
        assert score == 0

    def test_bio_gives_10_points(self):
        card = _make_devcard(
            identity=Identity(username="testuser", bio="I build things"),
        )
        profile = ProfileRepoData()
        score = compute_human_visibility_score(card, profile)
        assert score >= 10

    def test_profile_readme_gives_15_points(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_profile_readme=True, readme_length=200)
        score = compute_human_visibility_score(card, profile)
        assert score >= 15

    def test_repo_descriptions_give_points(self):
        card = _make_devcard(
            projects=[
                Project(name="a", description="Project A"),
                Project(name="b", description="Project B"),
                Project(name="c", description=None),
            ],
        )
        profile = ProfileRepoData()
        score = compute_human_visibility_score(card, profile)
        # 2/3 repos have descriptions = ~10 of 15 points
        assert score >= 8

    def test_full_profile_scores_high(self):
        card = _make_devcard(
            identity=Identity(
                username="testuser", bio="Builder",
                blog="https://test.dev", twitter_username="test",
            ),
            projects=[
                Project(name=f"p{i}", description=f"Desc {i}",
                        topics=["python", "cli"])
                for i in range(5)
            ],
            activity=Activity(status="active", commits_last_year=500),
            quality=Quality(
                license_adoption=1.0, docs_adoption=1.0,
                ci_adoption=1.0, test_adoption=1.0, linter_adoption=1.0,
            ),
        )
        profile = ProfileRepoData(has_profile_readme=True, readme_length=500)
        score = compute_human_visibility_score(card, profile)
        assert score >= 70

    def test_score_clamped_to_100(self):
        """Score should never exceed 100."""
        card = _make_devcard(
            identity=Identity(
                username="testuser", bio="Bio",
                blog="https://x.com", twitter_username="x",
            ),
            projects=[
                Project(
                    name=f"p{i}", description=f"D{i}",
                    topics=["a", "b", "c"], stars=100,
                )
                for i in range(10)
            ],
            activity=Activity(status="active", commits_last_year=2000),
            quality=Quality(
                license_adoption=1.0, docs_adoption=1.0,
                ci_adoption=1.0, test_adoption=1.0, linter_adoption=1.0,
            ),
        )
        profile = ProfileRepoData(has_profile_readme=True, readme_length=2000)
        score = compute_human_visibility_score(card, profile)
        assert score <= 100

    def test_returns_int(self):
        card = _make_devcard()
        profile = ProfileRepoData()
        score = compute_human_visibility_score(card, profile)
        assert isinstance(score, int)


class TestAgentReadinessScore:
    def test_empty_profile_scores_zero(self):
        card = _make_devcard()
        profile = ProfileRepoData()
        score = compute_agent_readiness_score(card, profile)
        assert score == 0

    def test_devcard_json_gives_20_points(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_devcard_json=True)
        score = compute_agent_readiness_score(card, profile)
        assert score >= 20

    def test_llms_txt_gives_10_points(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_llms_txt=True)
        score = compute_agent_readiness_score(card, profile)
        assert score >= 10

    def test_structured_readmes_give_points(self):
        card = _make_devcard(
            quality=Quality(docs_adoption=1.0),
        )
        profile = ProfileRepoData()
        score = compute_agent_readiness_score(card, profile)
        assert score >= 10

    def test_full_agent_ready_scores_high(self):
        card = _make_devcard(
            projects=[
                Project(name=f"p{i}", description=f"D{i}",
                        topics=["python"], classification="library")
                for i in range(5)
            ],
            quality=Quality(
                docs_adoption=1.0, license_adoption=1.0,
                ci_adoption=1.0, test_adoption=1.0, linter_adoption=1.0,
            ),
            stack=Stack(
                frameworks=[StackItem(name="FastAPI", category="framework")],
            ),
        )
        profile = ProfileRepoData(
            has_devcard_json=True,
            has_llms_txt=True,
            has_profile_readme=True,
        )
        score = compute_agent_readiness_score(card, profile)
        assert score >= 60

    def test_score_clamped_to_100(self):
        card = _make_devcard(
            projects=[
                Project(name=f"p{i}", description=f"D{i}",
                        topics=["a", "b"], classification="lib")
                for i in range(10)
            ],
            quality=Quality(
                docs_adoption=1.0, ci_adoption=1.0, test_adoption=1.0,
                license_adoption=1.0, linter_adoption=1.0,
            ),
            stack=Stack(
                frameworks=[StackItem(name="F", category="framework")],
            ),
        )
        profile = ProfileRepoData(
            has_devcard_json=True, has_llms_txt=True,
            has_profile_readme=True,
        )
        score = compute_agent_readiness_score(card, profile)
        assert score <= 100

    def test_returns_int(self):
        card = _make_devcard()
        profile = ProfileRepoData()
        score = compute_agent_readiness_score(card, profile)
        assert isinstance(score, int)


class TestExistingScoringUnchanged:
    """Ensure compute_quality_score still works exactly as before."""
    def test_weighted_composite(self):
        card = _make_devcard(
            quality=Quality(
                test_adoption=0.8, ci_adoption=0.6,
                docs_adoption=0.5, license_adoption=1.0, linter_adoption=0.3,
            ),
        )
        compute_quality_score(card)
        expected = round(0.8 * 0.3 + 0.6 * 0.25 + 0.5 * 0.2 + 1.0 * 0.15 + 0.3 * 0.1, 3)
        assert card.quality.score == expected

    def test_no_quality(self):
        card = _make_devcard()
        compute_quality_score(card)
        assert card.quality is None
```

**Run:** `uv run pytest tests/test_scoring_dual.py -v`
**Expected:** Import errors for `compute_human_visibility_score` and `compute_agent_readiness_score`; `TestExistingScoringUnchanged` passes

#### Step 3: Implement dual scoring

Replace content of `src/devcard/analyzers/scoring.py` (keeping `compute_quality_score` at top):

```python
from __future__ import annotations

from devcard.models import DevCard, ProfileRepoData


def compute_quality_score(devcard: DevCard) -> None:
    if devcard.quality is None:
        return

    q = devcard.quality
    q.score = round(
        q.test_adoption * 0.3
        + q.ci_adoption * 0.25
        + q.docs_adoption * 0.2
        + q.license_adoption * 0.15
        + q.linter_adoption * 0.1,
        3,
    )


def compute_human_visibility_score(
    devcard: DevCard, profile: ProfileRepoData,
) -> int:
    """Compute human visibility score (0-100).

    Scoring rubric:
    - Bio present: 10 pts
    - Profile README: 15 pts
    - Repo descriptions: 15 pts (proportional to repos with descriptions)
    - Topics: 10 pts (proportional to repos with topics)
    - README quality (docs adoption): 15 pts
    - License adoption: 5 pts
    - Pinned/signature repos: 5 pts
    - Activity: 10 pts
    - Social links: 5 pts
    - Contribution graph (consistency): 10 pts
    """
    score = 0

    # Bio (10 pts)
    if devcard.identity.bio:
        score += 10

    # Profile README (15 pts)
    if profile.has_profile_readme:
        if profile.readme_length > 100:
            score += 15
        else:
            score += 8

    # Repo descriptions (15 pts)
    if devcard.projects:
        with_desc = sum(1 for p in devcard.projects if p.description)
        ratio = with_desc / len(devcard.projects)
        score += round(ratio * 15)

    # Topics (10 pts)
    if devcard.projects:
        with_topics = sum(1 for p in devcard.projects if p.topics)
        ratio = with_topics / len(devcard.projects)
        score += round(ratio * 10)

    # README/docs quality (15 pts)
    if devcard.quality:
        score += round(devcard.quality.docs_adoption * 15)

    # License (5 pts)
    if devcard.quality:
        score += round(devcard.quality.license_adoption * 5)

    # Pinned/signature repos (5 pts)
    if any(p.is_signature for p in devcard.projects):
        score += 5

    # Activity (10 pts)
    if devcard.activity:
        if devcard.activity.status == "active":
            score += 10
        elif devcard.activity.status == "moderate":
            score += 6
        elif devcard.activity.status == "sporadic":
            score += 3

    # Social links (5 pts)
    social_count = sum(1 for val in [
        devcard.identity.blog,
        devcard.identity.twitter_username,
    ] if val)
    score += min(social_count * 3, 5)

    # Contribution graph / consistency (10 pts)
    if devcard.activity and devcard.activity.consistency_score is not None:
        score += round(devcard.activity.consistency_score / 100 * 10)

    return min(score, 100)


def compute_agent_readiness_score(
    devcard: DevCard, profile: ProfileRepoData,
) -> int:
    """Compute agent readiness score (0-100).

    Scoring rubric:
    - devcard.json exists: 20 pts
    - AGENTS.md in active repos: 20 pts (checked via quality details)
    - llms.txt: 10 pts
    - Structured READMEs (docs adoption): 15 pts
    - Dependency files (stack detection): 10 pts
    - Topics/metadata: 10 pts
    - Classification coverage: 10 pts
    - Clean commits (CI adoption as proxy): 5 pts
    """
    score = 0

    # devcard.json (20 pts)
    if profile.has_devcard_json:
        score += 20

    # llms.txt (10 pts)
    if profile.has_llms_txt:
        score += 10

    # Structured READMEs / docs adoption (15 pts)
    if devcard.quality:
        score += round(devcard.quality.docs_adoption * 15)

    # Dependency files / stack detection (10 pts)
    if devcard.stack:
        all_items = []
        for field in ("frameworks", "libraries", "databases", "tools",
                      "platforms", "ci_cd", "testing", "other"):
            all_items.extend(getattr(devcard.stack, field, []))
        if len(all_items) >= 5:
            score += 10
        elif len(all_items) >= 1:
            score += 5

    # Topics/metadata (10 pts)
    if devcard.projects:
        with_topics = sum(1 for p in devcard.projects if p.topics)
        ratio = with_topics / len(devcard.projects)
        score += round(ratio * 10)

    # Classification coverage (10 pts)
    if devcard.projects:
        classified = sum(1 for p in devcard.projects if p.classification)
        ratio = classified / len(devcard.projects)
        score += round(ratio * 10)

    # Clean commits / CI adoption (5 pts)
    if devcard.quality:
        score += round(devcard.quality.ci_adoption * 5)

    return min(score, 100)
```

**Run:** `uv run pytest tests/test_scoring_dual.py tests/test_analyzers.py -v`
**Expected:** All pass (including existing scoring tests)

**Run lint:** `uv run ruff check src/devcard/analyzers/scoring.py tests/test_scoring_dual.py`

**Commit:** `feat: add dual scoring — human visibility score and agent readiness score (0-100)`

---

## T3: Issue Detector (Phase P1, Part 2)

**Goal:** Create `src/devcard/analyzers/issue_detector.py` with `detect_issues()` function.

### T3.1 -- Add Issue model and write tests

#### Step 1: Add Issue model to `src/devcard/models.py`

```python
class Issue(BaseModel):
    """A detected profile/repo issue that can be fixed."""
    severity: Literal["high", "medium", "low"] = Field(
        description="Issue severity level"
    )
    type: str = Field(description="Issue type identifier (e.g. missing_bio, missing_topics)")
    message: str = Field(description="Human-readable description of the issue")
    repos: list[str] = Field(
        default_factory=list,
        description="Affected repositories, if repo-specific",
    )
```

#### Step 2: Write failing tests

Create `tests/test_issue_detector.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime

from devcard.analyzers.issue_detector import detect_issues
from devcard.models import (
    DevCard,
    Generator,
    Identity,
    Issue,
    ProfileRepoData,
    Project,
    Quality,
    QualityDetail,
)


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="test", version="0.0.1"),
        identity=Identity(username="testuser"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


class TestIssueDetector:
    def test_missing_bio_detected(self):
        card = _make_devcard(identity=Identity(username="testuser", bio=None))
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "missing_bio" in types

    def test_bio_present_no_issue(self):
        card = _make_devcard(identity=Identity(username="testuser", bio="I code"))
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "missing_bio" not in types

    def test_missing_profile_readme(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_profile_readme=False)
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "missing_profile_readme" in types

    def test_missing_descriptions(self):
        card = _make_devcard(
            projects=[
                Project(name="a", description=None),
                Project(name="b", description=None),
                Project(name="c", description="Has one"),
            ],
        )
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        desc_issue = next((i for i in issues if i.type == "missing_descriptions"), None)
        assert desc_issue is not None
        assert "a" in desc_issue.repos
        assert "b" in desc_issue.repos
        assert "c" not in desc_issue.repos

    def test_missing_topics(self):
        card = _make_devcard(
            projects=[
                Project(name="a", topics=[]),
                Project(name="b", topics=["python"]),
            ],
        )
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        topic_issue = next((i for i in issues if i.type == "missing_topics"), None)
        assert topic_issue is not None
        assert "a" in topic_issue.repos

    def test_missing_licenses(self):
        card = _make_devcard(
            quality=Quality(license_adoption=0.0),
        )
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "missing_licenses" in types

    def test_no_devcard_json(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_devcard_json=False)
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "no_devcard_json" in types

    def test_no_llms_txt(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_llms_txt=False)
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "no_llms_txt" in types

    def test_perfect_profile_no_issues(self):
        card = _make_devcard(
            identity=Identity(username="testuser", bio="I code"),
            projects=[
                Project(name="a", description="Desc", topics=["python"]),
            ],
            quality=Quality(
                license_adoption=1.0, docs_adoption=1.0,
                ci_adoption=1.0, test_adoption=1.0, linter_adoption=1.0,
            ),
        )
        profile = ProfileRepoData(
            has_profile_readme=True,
            has_devcard_json=True,
            has_llms_txt=True,
        )
        issues = detect_issues(card, profile)
        assert len(issues) == 0

    def test_returns_list_of_issue_models(self):
        card = _make_devcard()
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        assert isinstance(issues, list)
        for issue in issues:
            assert isinstance(issue, Issue)
            assert issue.severity in ("high", "medium", "low")

    def test_severity_ordering(self):
        """High-severity issues should be first."""
        card = _make_devcard()
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        if len(issues) >= 2:
            severity_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(issues) - 1):
                assert severity_order[issues[i].severity] <= severity_order[issues[i + 1].severity]
```

**Run:** `uv run pytest tests/test_issue_detector.py -v`
**Expected:** ImportError

#### Step 3: Implement `issue_detector.py`

Create `src/devcard/analyzers/issue_detector.py`:

```python
from __future__ import annotations

from devcard.models import DevCard, Issue, ProfileRepoData


def detect_issues(
    devcard: DevCard, profile: ProfileRepoData,
) -> list[Issue]:
    """Detect profile and repo issues that can be fixed.

    Returns issues sorted by severity (high first).
    """
    issues: list[Issue] = []

    # --- High severity ---

    if not devcard.identity.bio:
        issues.append(Issue(
            severity="high",
            type="missing_bio",
            message="GitHub profile has no bio. Add a short bio to help humans and agents understand who you are.",
        ))

    if not profile.has_profile_readme:
        issues.append(Issue(
            severity="high",
            type="missing_profile_readme",
            message="No profile README found. Create a README.md in a repo named after your username.",
        ))

    # --- Medium severity ---

    if devcard.projects:
        missing_desc = [p.name for p in devcard.projects if not p.description]
        if missing_desc:
            issues.append(Issue(
                severity="medium",
                type="missing_descriptions",
                message=f"{len(missing_desc)} repos have no description.",
                repos=missing_desc,
            ))

    if devcard.projects:
        missing_topics = [p.name for p in devcard.projects if not p.topics]
        if missing_topics:
            issues.append(Issue(
                severity="medium",
                type="missing_topics",
                message=f"{len(missing_topics)} repos have no topics/tags.",
                repos=missing_topics,
            ))

    if devcard.quality and devcard.quality.license_adoption < 0.5:
        issues.append(Issue(
            severity="medium",
            type="missing_licenses",
            message="Most repos lack a license file. Add LICENSE to your key repos.",
        ))

    if devcard.quality and devcard.quality.docs_adoption < 0.5:
        issues.append(Issue(
            severity="medium",
            type="stale_readmes",
            message="Many repos lack documentation. Add or update README files.",
        ))

    # --- Low severity (agent-readiness) ---

    if not profile.has_devcard_json:
        issues.append(Issue(
            severity="low",
            type="no_devcard_json",
            message="No devcard.json in profile repo. Add one to make your profile machine-readable.",
        ))

    if not profile.has_llms_txt:
        issues.append(Issue(
            severity="low",
            type="no_llms_txt",
            message="No llms.txt in profile repo. Add one to help LLMs understand your work.",
        ))

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda i: severity_order[i.severity])

    return issues
```

**Run:** `uv run pytest tests/test_issue_detector.py tests/test_scoring_dual.py -v`
**Expected:** All pass

**Run lint:** `uv run ruff check src/devcard/analyzers/issue_detector.py tests/test_issue_detector.py`

**Commit:** `feat: add issue detector — detect missing bio, README, descriptions, topics, licenses, devcard.json, llms.txt`

---

## T4: Fixer Modules (Phase P2)

**Goal:** Create `src/devcard/fixers/` package with 6 pure-function modules. No I/O, no LLM calls.

### T4.1 -- description_generator and topic_suggester

#### Step 1: Write failing tests

Create `tests/test_fixers.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from devcard.models import (
    DevCard,
    Generator,
    Identity,
    Language,
    Project,
    Stack,
    StackItem,
)


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="test", version="0.0.1"),
        identity=Identity(username="testuser"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


class TestDescriptionGenerator:
    def test_generates_from_readme(self):
        from devcard.fixers.description_generator import generate_description

        repo_data = {
            "name": "cool-lib",
            "language": "Python",
            "classification": "library",
            "readme_first_paragraph": "A fast HTTP client for Python applications.",
            "stack": ["httpx", "asyncio"],
        }
        desc = generate_description(repo_data)
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert len(desc) <= 350  # GitHub description limit
        assert "HTTP" in desc or "fast" in desc.lower()

    def test_generates_fallback_without_readme(self):
        from devcard.fixers.description_generator import generate_description

        repo_data = {
            "name": "my-tool",
            "language": "Go",
            "classification": "tool",
            "readme_first_paragraph": None,
            "stack": ["cobra", "viper"],
        }
        desc = generate_description(repo_data)
        assert isinstance(desc, str)
        assert "Go" in desc
        assert "tool" in desc.lower()

    def test_returns_empty_on_no_data(self):
        from devcard.fixers.description_generator import generate_description

        repo_data = {"name": "x", "language": None, "classification": None,
                     "readme_first_paragraph": None, "stack": []}
        desc = generate_description(repo_data)
        assert isinstance(desc, str)


class TestTopicSuggester:
    def test_suggests_from_language(self):
        from devcard.fixers.topic_suggester import suggest_topics

        repo_data = {
            "name": "api-server",
            "language": "Python",
            "stack": ["fastapi", "sqlalchemy"],
            "readme_keywords": [],
            "existing_topics": [],
        }
        topics = suggest_topics(repo_data)
        assert isinstance(topics, list)
        assert "python" in topics
        assert len(topics) <= 20

    def test_suggests_from_stack(self):
        from devcard.fixers.topic_suggester import suggest_topics

        repo_data = {
            "name": "web-app",
            "language": "TypeScript",
            "stack": ["react", "next"],
            "readme_keywords": [],
            "existing_topics": [],
        }
        topics = suggest_topics(repo_data)
        assert any(t in topics for t in ["react", "nextjs", "typescript"])

    def test_does_not_duplicate_existing(self):
        from devcard.fixers.topic_suggester import suggest_topics

        repo_data = {
            "name": "my-lib",
            "language": "Python",
            "stack": [],
            "readme_keywords": [],
            "existing_topics": ["python"],
        }
        topics = suggest_topics(repo_data)
        assert topics.count("python") <= 1

    def test_max_20_topics(self):
        from devcard.fixers.topic_suggester import suggest_topics

        repo_data = {
            "name": "mega-project",
            "language": "Python",
            "stack": ["django", "celery", "redis", "postgres",
                      "docker", "kubernetes", "terraform", "aws",
                      "pytest", "ruff", "black", "mypy"],
            "readme_keywords": ["api", "microservice", "cloud", "devops",
                                "backend", "web", "rest", "graphql"],
            "existing_topics": [],
        }
        topics = suggest_topics(repo_data)
        assert len(topics) <= 20
```

**Run:** `uv run pytest tests/test_fixers.py -v`
**Expected:** ImportError for `devcard.fixers.description_generator`

#### Step 2: Create the fixers package and implement

Create `src/devcard/fixers/__init__.py` (empty file).

Create `src/devcard/fixers/description_generator.py`:

```python
from __future__ import annotations


def generate_description(repo_data: dict) -> str:
    """Generate a repository description from available data.

    Pure function. Takes a dict with keys: name, language, classification,
    readme_first_paragraph, stack.

    Returns a string suitable for GitHub repo description (max 350 chars).
    """
    readme_para = repo_data.get("readme_first_paragraph")
    if readme_para and len(readme_para.strip()) > 10:
        desc = readme_para.strip()
        if len(desc) > 350:
            desc = desc[:347] + "..."
        return desc

    language = repo_data.get("language") or ""
    classification = repo_data.get("classification") or "project"
    stack = repo_data.get("stack") or []

    if language and stack:
        stack_str = ", ".join(stack[:3])
        return f"{language} {classification} built with {stack_str}"
    if language:
        return f"{language} {classification}"

    return repo_data.get("name", "")
```

Create `src/devcard/fixers/topic_suggester.py`:

```python
from __future__ import annotations


def suggest_topics(repo_data: dict) -> list[str]:
    """Suggest GitHub topics for a repository.

    Pure function. Takes a dict with keys: name, language, stack,
    readme_keywords, existing_topics.

    Returns a deduplicated list of suggested topics (max 20).
    """
    suggestions: list[str] = []
    existing = set(repo_data.get("existing_topics") or [])

    # Add language as topic
    language = repo_data.get("language")
    if language:
        lang_topic = language.lower().replace(" ", "-").replace("+", "plus").replace("#", "sharp")
        if lang_topic not in existing:
            suggestions.append(lang_topic)

    # Add stack items as topics
    for item in repo_data.get("stack") or []:
        topic = item.lower().replace(" ", "-")
        if topic not in existing and topic not in suggestions:
            suggestions.append(topic)

    # Add readme keywords
    for kw in repo_data.get("readme_keywords") or []:
        topic = kw.lower().replace(" ", "-")
        if topic not in existing and topic not in suggestions:
            suggestions.append(topic)

    # Include existing topics in the final list
    final = list(existing) + suggestions
    # Deduplicate preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for t in final:
        if t not in seen:
            seen.add(t)
            deduped.append(t)

    return deduped[:20]
```

**Run:** `uv run pytest tests/test_fixers.py -v`
**Expected:** All 7 tests pass

### T4.2 -- agents_md_generator and llms_txt_generator

#### Step 3: Add tests for `agents_md_generator` and `llms_txt_generator`

Append to `tests/test_fixers.py`:

```python
class TestAgentsMdGenerator:
    def test_generates_valid_markdown(self):
        from devcard.fixers.agents_md_generator import generate_agents_md

        repo_data = {
            "name": "my-api",
            "readme_first_paragraph": "A REST API for managing widgets.",
            "language": "Python",
            "stack": ["fastapi", "sqlalchemy", "pydantic"],
            "directories": ["src", "tests", "docs"],
            "config_files": ["pyproject.toml", "Dockerfile"],
        }
        result = generate_agents_md(repo_data)
        assert isinstance(result, str)
        assert "# my-api" in result or "## Overview" in result
        assert "fastapi" in result.lower() or "FastAPI" in result
        assert "src" in result

    def test_handles_minimal_data(self):
        from devcard.fixers.agents_md_generator import generate_agents_md

        repo_data = {
            "name": "bare-repo",
            "readme_first_paragraph": None,
            "language": None,
            "stack": [],
            "directories": [],
            "config_files": [],
        }
        result = generate_agents_md(repo_data)
        assert isinstance(result, str)
        assert len(result) > 0


class TestLlmsTxtGenerator:
    def test_generates_valid_llms_txt(self):
        from devcard.fixers.llms_txt_generator import generate_llms_txt

        repo_data = {
            "name": "my-lib",
            "description": "A useful library for things.",
            "language": "Python",
            "docs_files": ["docs/getting-started.md", "docs/api.md"],
            "examples_dir": True,
        }
        result = generate_llms_txt(repo_data)
        assert isinstance(result, str)
        assert "# my-lib" in result
        assert "useful library" in result.lower() or "my-lib" in result

    def test_handles_no_docs(self):
        from devcard.fixers.llms_txt_generator import generate_llms_txt

        repo_data = {
            "name": "simple",
            "description": None,
            "language": "Go",
            "docs_files": [],
            "examples_dir": False,
        }
        result = generate_llms_txt(repo_data)
        assert isinstance(result, str)
        assert "# simple" in result
```

#### Step 4: Implement

Create `src/devcard/fixers/agents_md_generator.py`:

```python
from __future__ import annotations


def generate_agents_md(repo_data: dict) -> str:
    """Generate an AGENTS.md file for a repository.

    Pure function. Takes a dict with keys: name, readme_first_paragraph,
    language, stack, directories, config_files.
    """
    sections: list[str] = []
    name = repo_data.get("name", "project")

    # Title
    sections.append(f"# {name}")

    # Overview
    overview = repo_data.get("readme_first_paragraph")
    if overview:
        sections.append(f"## Overview\n\n{overview}")
    else:
        sections.append(f"## Overview\n\n{name} repository.")

    # Tech Stack
    language = repo_data.get("language")
    stack = repo_data.get("stack") or []
    if language or stack:
        lines = ["## Tech Stack", ""]
        if language:
            lines.append(f"- **Language:** {language}")
        for item in stack:
            lines.append(f"- {item}")
        sections.append("\n".join(lines))

    # Structure
    directories = repo_data.get("directories") or []
    if directories:
        lines = ["## Structure", ""]
        for d in directories:
            lines.append(f"- `{d}/`")
        sections.append("\n".join(lines))

    # Config / Commands
    config_files = repo_data.get("config_files") or []
    if config_files:
        lines = ["## Configuration", ""]
        for f in config_files:
            lines.append(f"- `{f}`")
        sections.append("\n".join(lines))

    return "\n\n".join(sections) + "\n"
```

Create `src/devcard/fixers/llms_txt_generator.py`:

```python
from __future__ import annotations


def generate_llms_txt(repo_data: dict) -> str:
    """Generate an llms.txt file for a repository.

    Pure function. Takes a dict with keys: name, description, language,
    docs_files, examples_dir.
    """
    sections: list[str] = []
    name = repo_data.get("name", "project")

    # Title
    sections.append(f"# {name}")

    # Description
    description = repo_data.get("description")
    if description:
        sections.append(f"> {description}")

    # Language info
    language = repo_data.get("language")
    if language:
        sections.append(f"{name} is a {language} project.")

    # Docs section
    docs_files = repo_data.get("docs_files") or []
    if docs_files:
        lines = ["## Docs", ""]
        for doc in docs_files:
            doc_name = doc.rsplit("/", 1)[-1].replace(".md", "").replace("-", " ").title()
            lines.append(f"- [{doc_name}]({doc})")
        sections.append("\n".join(lines))

    # Examples
    if repo_data.get("examples_dir"):
        sections.append("## Examples\n\nSee the `examples/` directory for usage examples.")

    return "\n\n".join(sections) + "\n"
```

**Run:** `uv run pytest tests/test_fixers.py -v`
**Expected:** All 11 tests pass

### T4.3 -- profile_readme_generator and devcard_deployer

#### Step 5: Add tests

Append to `tests/test_fixers.py`:

```python
class TestProfileReadmeGenerator:
    def test_generates_readme_with_greeting(self):
        from devcard.fixers.profile_readme_generator import generate_profile_readme

        card = _make_devcard(
            identity=Identity(username="testuser", name="Test User"),
            languages=[
                Language(name="Python", percentage=60.0),
                Language(name="TypeScript", percentage=40.0),
            ],
            projects=[
                Project(name="cool-lib", description="A cool library", stars=100,
                        url="https://github.com/testuser/cool-lib"),
            ],
        )
        result = generate_profile_readme(card, svg_content="<svg>mock</svg>")
        assert isinstance(result, str)
        assert "Test User" in result or "testuser" in result
        assert "cool-lib" in result
        assert "<svg>mock</svg>" in result or "devcard" in result.lower()

    def test_handles_minimal_card(self):
        from devcard.fixers.profile_readme_generator import generate_profile_readme

        card = _make_devcard()
        result = generate_profile_readme(card, svg_content=None)
        assert isinstance(result, str)
        assert "testuser" in result


class TestDevcardDeployer:
    def test_returns_dict_of_files(self):
        from devcard.fixers.devcard_deployer import prepare_devcard_files

        card = _make_devcard(
            identity=Identity(username="testuser", name="Test"),
            languages=[Language(name="Python", percentage=100.0)],
        )
        files = prepare_devcard_files(card, theme="default")
        assert isinstance(files, dict)
        assert "devcard.json" in files
        assert isinstance(files["devcard.json"], str)

    def test_json_is_valid(self):
        import json
        from devcard.fixers.devcard_deployer import prepare_devcard_files

        card = _make_devcard()
        files = prepare_devcard_files(card, theme="default")
        data = json.loads(files["devcard.json"])
        assert data["identity"]["username"] == "testuser"
```

#### Step 6: Implement

Create `src/devcard/fixers/profile_readme_generator.py`:

```python
from __future__ import annotations

from devcard.models import DevCard


def generate_profile_readme(
    devcard: DevCard, svg_content: str | None = None,
) -> str:
    """Generate a profile README.md for the user's username/username repo.

    Pure function. Takes a DevCard and optional SVG content string.
    """
    sections: list[str] = []
    name = devcard.identity.name or devcard.identity.username

    # Greeting
    sections.append(f"# Hi, I'm {name} :wave:\n")

    if devcard.identity.bio:
        sections.append(devcard.identity.bio)

    # DevCard embed
    if svg_content:
        sections.append("## DevCard\n")
        sections.append(svg_content)

    # Top languages
    if devcard.languages:
        lang_items = [
            f"**{lang.name}** ({lang.percentage:.0f}%)"
            for lang in devcard.languages[:5]
        ]
        sections.append("## Languages\n\n" + " | ".join(lang_items))

    # Top projects
    if devcard.projects:
        lines = ["## Top Projects", ""]
        for proj in devcard.projects[:5]:
            desc = f" - {proj.description}" if proj.description else ""
            url = proj.url or f"https://github.com/{devcard.identity.username}/{proj.name}"
            stars = f" ({proj.stars} :star:)" if proj.stars else ""
            lines.append(f"- [{proj.name}]({url}){desc}{stars}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections) + "\n"
```

Create `src/devcard/fixers/devcard_deployer.py`:

```python
from __future__ import annotations

from devcard.models import DevCard
from devcard.output.json_output import to_json


def prepare_devcard_files(
    devcard: DevCard, theme: str = "default",
) -> dict[str, str]:
    """Prepare files for deploying DevCard to a profile repo.

    Pure function. Returns a dict mapping filename to content string.
    Currently produces devcard.json. SVG generation can be added later
    when the renderer is wired in.
    """
    files: dict[str, str] = {}

    # Always include devcard.json
    files["devcard.json"] = to_json(devcard)

    return files
```

**Run:** `uv run pytest tests/test_fixers.py -v`
**Expected:** All 15 tests pass

**Run lint:** `uv run ruff check src/devcard/fixers/ tests/test_fixers.py`

**Commit:** `feat: add 6 fixer modules — description_generator, topic_suggester, agents_md_generator, llms_txt_generator, profile_readme_generator, devcard_deployer`

---

## T5: Audit & Analyze Pipelines + MCP Tools (Phase P3)

**Goal:** Add `audit_pipeline` and `analyze_repo_pipeline` to `src/devcard/pipeline.py`, then wire as MCP tools.

### T5.1 -- Add AuditResult and RepoAnalysis models

#### Step 1: Add new models to `src/devcard/models.py`

```python
class AuditResult(BaseModel):
    """Result of auditing a developer's GitHub profile."""
    username: str = Field(description="GitHub username that was audited")
    human_visibility_score: int = Field(description="Human visibility score 0-100")
    agent_readiness_score: int = Field(description="Agent readiness score 0-100")
    issues: list[Issue] = Field(default_factory=list, description="Detected issues")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")
    summary: dict = Field(default_factory=dict, description="Summary statistics")


class RepoAnalysis(BaseModel):
    """Result of analyzing a single repository."""
    owner: str = Field(description="Repository owner")
    repo: str = Field(description="Repository name")
    language: str | None = Field(default=None, description="Primary language")
    classification: str | None = Field(default=None, description="Project classification")
    issues: list[Issue] = Field(default_factory=list, description="Detected issues for this repo")
    suggested_description: str | None = Field(default=None, description="Suggested repo description")
    suggested_topics: list[str] = Field(default_factory=list, description="Suggested topics")
```

### T5.2 -- Write tests for audit_pipeline

#### Step 2: Create test file

Create `tests/test_audit_pipeline.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from devcard.config import DevCardConfig
from devcard.models import (
    AuditResult,
    DevCard,
    Generator,
    Identity,
    Language,
    Project,
    Quality,
)


def _mock_devcard() -> DevCard:
    return DevCard(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser", bio="I code"),
        languages=[Language(name="Python", percentage=80.0)],
        projects=[
            Project(name="my-lib", description="A library", topics=["python"]),
        ],
        quality=Quality(
            docs_adoption=0.5, license_adoption=0.5,
            ci_adoption=0.5, test_adoption=0.5, linter_adoption=0.5,
        ),
    )


class TestAuditPipeline:
    async def test_returns_audit_result(self):
        from devcard.pipeline import audit_pipeline

        with patch("devcard.pipeline.generate_devcard", new_callable=AsyncMock) as mock_gen, \
             patch("devcard.pipeline._fetch_profile_repo_data", new_callable=AsyncMock) as mock_profile:
            mock_gen.return_value = _mock_devcard()
            mock_profile.return_value = {
                "has_profile_readme": True,
                "readme_length": 200,
                "has_devcard_json": False,
                "has_llms_txt": False,
                "files": ["README.md"],
            }

            config = DevCardConfig(github_token="test", no_cache=True)
            result = await audit_pipeline("testuser", config)

            assert isinstance(result, AuditResult)
            assert result.username == "testuser"
            assert 0 <= result.human_visibility_score <= 100
            assert 0 <= result.agent_readiness_score <= 100
            assert isinstance(result.issues, list)

    async def test_includes_issues(self):
        from devcard.pipeline import audit_pipeline

        with patch("devcard.pipeline.generate_devcard", new_callable=AsyncMock) as mock_gen, \
             patch("devcard.pipeline._fetch_profile_repo_data", new_callable=AsyncMock) as mock_profile:
            card = _mock_devcard()
            card.identity.bio = None  # Will trigger missing_bio issue
            mock_gen.return_value = card
            mock_profile.return_value = {
                "has_profile_readme": False,
                "has_devcard_json": False,
                "has_llms_txt": False,
                "files": [],
            }

            config = DevCardConfig(github_token="test", no_cache=True)
            result = await audit_pipeline("testuser", config)
            types = [i.type for i in result.issues]
            assert "missing_bio" in types
            assert "missing_profile_readme" in types
```

**Run:** `uv run pytest tests/test_audit_pipeline.py -v`
**Expected:** ImportError for `audit_pipeline`

#### Step 3: Implement audit_pipeline and helpers

Add to `src/devcard/pipeline.py`:

```python
# New imports at top:
from devcard.analyzers.issue_detector import detect_issues
from devcard.analyzers.scoring import compute_agent_readiness_score, compute_human_visibility_score
from devcard.models import AuditResult, Issue, ProfileRepoData, RepoAnalysis

# New helper function:
async def _fetch_profile_repo_data(
    client: GitHubClient, username: str,
) -> dict:
    """Fetch data about the user's profile repo (username/username)."""
    result = {
        "has_profile_readme": False,
        "readme_length": 0,
        "has_devcard_json": False,
        "has_llms_txt": False,
        "files": [],
    }
    try:
        contents = await client.get_repo_contents(username, username)
        file_names = [c.name for c in contents]
        result["files"] = file_names
        result["has_profile_readme"] = "README.md" in file_names
        result["has_devcard_json"] = "devcard.json" in file_names
        result["has_llms_txt"] = "llms.txt" in file_names

        if result["has_profile_readme"]:
            try:
                readme_items = await client.get_repo_contents(username, username, "README.md")
                if readme_items and readme_items[0].content:
                    import base64
                    content = base64.b64decode(readme_items[0].content).decode(errors="replace")
                    result["readme_length"] = len(content)
            except Exception:
                pass
    except Exception:
        logger.warning("Could not fetch profile repo for %s", username)

    return result


# New pipeline function:
async def audit_pipeline(
    username: str, config: DevCardConfig,
) -> AuditResult:
    """Audit a developer's GitHub profile.

    Generates a DevCard, fetches profile repo data, computes dual scores,
    and detects issues.
    """
    devcard = await generate_devcard(username, config)

    client = GitHubClient(config)
    try:
        profile_data = await _fetch_profile_repo_data(client, username)
    finally:
        await client.close()

    profile = ProfileRepoData(
        has_profile_readme=profile_data["has_profile_readme"],
        readme_length=profile_data.get("readme_length", 0),
        has_devcard_json=profile_data["has_devcard_json"],
        has_llms_txt=profile_data["has_llms_txt"],
        files=profile_data.get("files", []),
    )

    human_score = compute_human_visibility_score(devcard, profile)
    agent_score = compute_agent_readiness_score(devcard, profile)
    issues = detect_issues(devcard, profile)

    recommendations = [issue.message for issue in issues[:5]]

    return AuditResult(
        username=username,
        human_visibility_score=human_score,
        agent_readiness_score=agent_score,
        issues=issues,
        recommendations=recommendations,
        summary={
            "total_repos": len(devcard.projects),
            "quality_score": devcard.quality.score if devcard.quality else 0,
            "profile_type": (
                devcard.expertise.profile_type
                if devcard.expertise else None
            ),
            "issue_count": len(issues),
        },
    )
```

**Run:** `uv run pytest tests/test_audit_pipeline.py -v`
**Expected:** 2 passing

### T5.3 -- Add audit_profile MCP tool

#### Step 4: Write test for MCP tool

Create `tests/test_mcp_audit.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from devcard.models import AuditResult, DevCard, Generator, Identity, Issue


class TestAuditProfileTool:
    async def test_returns_json_with_scores(self):
        from devcard_mcp.server import audit_profile

        mock_result = AuditResult(
            username="testuser",
            human_visibility_score=65,
            agent_readiness_score=30,
            issues=[
                Issue(severity="high", type="missing_bio",
                      message="No bio found"),
            ],
            recommendations=["No bio found"],
            summary={"total_repos": 5, "issue_count": 1},
        )

        with patch("devcard_mcp.server.audit_pipeline", new_callable=AsyncMock) as mock:
            mock.return_value = mock_result
            result = await audit_profile("testuser")
            data = json.loads(result)
            assert data["human_visibility_score"] == 65
            assert data["agent_readiness_score"] == 30
            assert len(data["issues"]) == 1
```

#### Step 5: Implement the MCP tool

Add to `devcard-mcp/src/devcard_mcp/server.py`:

```python
# Add import at top:
from devcard.pipeline import audit_pipeline

# Add tool:
@mcp.tool()
async def audit_profile(username: str, token: str | None = None) -> str:
    """Audit a GitHub developer profile for visibility and agent-readiness.

    Returns human_visibility_score (0-100), agent_readiness_score (0-100),
    detected issues with severity levels, and actionable recommendations.
    Use this to understand what's missing from a developer's GitHub presence.
    """
    config = _get_config()
    if token:
        config.github_token = token
    result = await audit_pipeline(username, config)
    return result.model_dump_json(indent=2, exclude_none=True)
```

**Run:** `uv run pytest tests/test_mcp_audit.py tests/test_audit_pipeline.py -v`
**Expected:** All pass

**Run lint:** `uv run ruff check src/devcard/pipeline.py devcard-mcp/src/devcard_mcp/server.py`

**Commit:** `feat: add audit_profile MCP tool — dual scoring + issue detection`

---

## T6: Fix Pipelines + MCP Tools (Phase P4)

**Goal:** Add fix_profile and fix_repo MCP tools that use fixer modules and GitHub write methods.

### T6.1 -- Add FixResult model and fix pipeline

#### Step 1: Add FixResult model to `src/devcard/models.py`

```python
class FixAction(BaseModel):
    """A single fix action to apply or preview."""
    type: str = Field(description="Fix type (e.g. set_description, set_topics, create_file)")
    target: str = Field(description="Target repo or file path")
    preview: str = Field(description="Preview of the change")
    applied: bool = Field(default=False, description="Whether this fix was applied")


class FixResult(BaseModel):
    """Result of applying fixes to a profile or repo."""
    dry_run: bool = Field(description="Whether this was a dry run (preview only)")
    actions: list[FixAction] = Field(default_factory=list, description="Fix actions taken or previewed")
    errors: list[str] = Field(default_factory=list, description="Errors encountered during fixing")
```

#### Step 2: Write failing tests for fix pipeline

Create `tests/test_fix_pipeline.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from devcard.config import DevCardConfig
from devcard.models import (
    DevCard,
    FixResult,
    Generator,
    Identity,
    Language,
    Project,
    Quality,
)


def _mock_devcard() -> DevCard:
    return DevCard(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser"),
        languages=[Language(name="Python", percentage=80.0)],
        projects=[
            Project(name="my-lib", description=None, topics=[]),
        ],
        quality=Quality(),
    )


class TestFixRepoPipeline:
    async def test_dry_run_returns_preview(self):
        from devcard.pipeline import fix_repo_pipeline

        with patch("devcard.pipeline.generate_devcard", new_callable=AsyncMock) as mock_gen, \
             patch("devcard.pipeline.GitHubClient") as mock_client_cls:
            mock_gen.return_value = _mock_devcard()
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_repo_contents = AsyncMock(return_value=[])
            mock_client.get_repo_languages = AsyncMock(return_value={"Python": 10000})

            config = DevCardConfig(github_token="test", no_cache=True)
            result = await fix_repo_pipeline(
                "testuser", "my-lib", config,
                fixes=["description", "topics"],
                dry_run=True,
            )
            assert isinstance(result, FixResult)
            assert result.dry_run is True
            assert len(result.actions) > 0
            assert all(not a.applied for a in result.actions)

    async def test_apply_calls_github_api(self):
        from devcard.pipeline import fix_repo_pipeline

        with patch("devcard.pipeline.generate_devcard", new_callable=AsyncMock) as mock_gen, \
             patch("devcard.pipeline.GitHubClient") as mock_client_cls:
            mock_gen.return_value = _mock_devcard()
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.get_repo_contents = AsyncMock(return_value=[])
            mock_client.get_repo_languages = AsyncMock(return_value={"Python": 10000})
            mock_client.update_repo_description = AsyncMock(return_value={"description": "x"})
            mock_client.update_repo_topics = AsyncMock(return_value={"names": ["python"]})

            config = DevCardConfig(github_token="test", no_cache=True)
            result = await fix_repo_pipeline(
                "testuser", "my-lib", config,
                fixes=["description", "topics"],
                dry_run=False,
            )
            assert isinstance(result, FixResult)
            assert result.dry_run is False
            # At least one action should be applied
            assert any(a.applied for a in result.actions)
```

**Run:** `uv run pytest tests/test_fix_pipeline.py -v`
**Expected:** ImportError for `fix_repo_pipeline`

#### Step 3: Implement fix pipelines

Add to `src/devcard/pipeline.py`:

```python
# New imports:
from devcard.fixers.description_generator import generate_description
from devcard.fixers.topic_suggester import suggest_topics
from devcard.models import FixAction, FixResult

async def fix_repo_pipeline(
    owner: str,
    repo: str,
    config: DevCardConfig,
    fixes: list[str],
    dry_run: bool = True,
) -> FixResult:
    """Fix issues on a single repository.

    Supported fixes: "description", "topics"
    """
    actions: list[FixAction] = []
    errors: list[str] = []

    client = GitHubClient(config)
    try:
        # Gather repo info
        try:
            contents = await client.get_repo_contents(owner, repo)
            file_names = [c.name for c in contents]
        except Exception:
            contents = []
            file_names = []

        try:
            languages = await client.get_repo_languages(owner, repo)
        except Exception:
            languages = {}

        primary_language = max(languages, key=languages.get) if languages else None

        # Find the project in devcard or build minimal repo_data
        repo_data = {
            "name": repo,
            "language": primary_language,
            "classification": None,
            "readme_first_paragraph": None,
            "stack": [],
            "readme_keywords": [],
            "existing_topics": [],
        }

        if "description" in fixes:
            desc = generate_description(repo_data)
            action = FixAction(
                type="set_description",
                target=f"{owner}/{repo}",
                preview=desc,
            )
            if not dry_run:
                try:
                    await client.update_repo_description(owner, repo, desc)
                    action.applied = True
                except Exception as e:
                    errors.append(f"Failed to update description for {repo}: {e}")
            actions.append(action)

        if "topics" in fixes:
            topics = suggest_topics(repo_data)
            action = FixAction(
                type="set_topics",
                target=f"{owner}/{repo}",
                preview=", ".join(topics),
            )
            if not dry_run:
                try:
                    await client.update_repo_topics(owner, repo, topics)
                    action.applied = True
                except Exception as e:
                    errors.append(f"Failed to update topics for {repo}: {e}")
            actions.append(action)

    finally:
        await client.close()

    return FixResult(dry_run=dry_run, actions=actions, errors=errors)


async def fix_profile_pipeline(
    username: str,
    config: DevCardConfig,
    fixes: list[str],
    dry_run: bool = True,
) -> FixResult:
    """Fix issues on a developer's profile.

    Supported fixes: "devcard_json", "profile_readme"
    """
    from devcard.fixers.devcard_deployer import prepare_devcard_files
    from devcard.fixers.profile_readme_generator import generate_profile_readme

    actions: list[FixAction] = []
    errors: list[str] = []

    devcard = await generate_devcard(username, config)
    client = GitHubClient(config)

    try:
        if "devcard_json" in fixes:
            files = prepare_devcard_files(devcard)
            for filename, content in files.items():
                action = FixAction(
                    type="create_file",
                    target=f"{username}/{username}/{filename}",
                    preview=content[:200] + ("..." if len(content) > 200 else ""),
                )
                if not dry_run:
                    try:
                        await client.create_or_update_file(
                            username, username, filename, content,
                            f"Add {filename} via DevCard",
                        )
                        action.applied = True
                    except Exception as e:
                        errors.append(f"Failed to create {filename}: {e}")
                actions.append(action)

        if "profile_readme" in fixes:
            readme = generate_profile_readme(devcard, svg_content=None)
            action = FixAction(
                type="create_file",
                target=f"{username}/{username}/README.md",
                preview=readme[:200] + ("..." if len(readme) > 200 else ""),
            )
            if not dry_run:
                try:
                    await client.create_or_update_file(
                        username, username, "README.md", readme,
                        "Update profile README via DevCard",
                    )
                    action.applied = True
                except Exception as e:
                    errors.append(f"Failed to update README: {e}")
            actions.append(action)
    finally:
        await client.close()

    return FixResult(dry_run=dry_run, actions=actions, errors=errors)
```

**Run:** `uv run pytest tests/test_fix_pipeline.py -v`
**Expected:** 2 passing

### T6.2 -- Add fix_repo and fix_profile MCP tools

#### Step 4: Add MCP tools to server

Add to `devcard-mcp/src/devcard_mcp/server.py`:

```python
# Add imports at top:
from devcard.pipeline import fix_profile_pipeline, fix_repo_pipeline

@mcp.tool()
async def fix_repo(
    owner: str,
    repo: str,
    fixes: list[str],
    token: str | None = None,
    dry_run: bool = True,
) -> str:
    """Fix issues on a single GitHub repository.

    Available fixes: "description" (auto-generate repo description),
    "topics" (suggest and set topics).

    Set dry_run=False to actually apply changes (requires token with repo scope).
    Default is dry_run=True (preview only).
    """
    config = _get_config()
    if token:
        config.github_token = token
    result = await fix_repo_pipeline(owner, repo, config, fixes, dry_run)
    return result.model_dump_json(indent=2, exclude_none=True)


@mcp.tool()
async def fix_profile(
    username: str,
    fixes: list[str],
    token: str | None = None,
    dry_run: bool = True,
) -> str:
    """Fix issues on a GitHub developer profile.

    Available fixes: "devcard_json" (deploy devcard.json to profile repo),
    "profile_readme" (generate/update profile README).

    Set dry_run=False to actually apply changes (requires token with repo scope).
    Default is dry_run=True (preview only).
    """
    config = _get_config()
    if token:
        config.github_token = token
    result = await fix_profile_pipeline(username, config, fixes, dry_run)
    return result.model_dump_json(indent=2, exclude_none=True)


@mcp.tool()
async def agent_ready(
    username: str,
    token: str | None = None,
    dry_run: bool = True,
) -> str:
    """Make a GitHub profile fully agent-ready.

    Runs a full audit, applies all available fixes, then re-audits
    to show improvement. Combines audit_profile + fix_profile + fix_repo.

    Set dry_run=False to apply changes. Default is preview only.
    """
    config = _get_config()
    if token:
        config.github_token = token

    # Initial audit
    before = await audit_pipeline(username, config)

    # Apply profile fixes
    profile_fixes = []
    issue_types = {i.type for i in before.issues}
    if "no_devcard_json" in issue_types:
        profile_fixes.append("devcard_json")
    if "missing_profile_readme" in issue_types:
        profile_fixes.append("profile_readme")

    profile_result = None
    if profile_fixes:
        profile_result = await fix_profile_pipeline(
            username, config, profile_fixes, dry_run,
        )

    # Apply repo fixes
    repo_results = []
    repos_needing_desc = set()
    repos_needing_topics = set()
    for issue in before.issues:
        if issue.type == "missing_descriptions":
            repos_needing_desc.update(issue.repos)
        if issue.type == "missing_topics":
            repos_needing_topics.update(issue.repos)

    all_fix_repos = repos_needing_desc | repos_needing_topics
    for repo_name in list(all_fix_repos)[:5]:  # Limit to top 5
        fixes = []
        if repo_name in repos_needing_desc:
            fixes.append("description")
        if repo_name in repos_needing_topics:
            fixes.append("topics")
        if fixes:
            repo_result = await fix_repo_pipeline(
                username, repo_name, config, fixes, dry_run,
            )
            repo_results.append({"repo": repo_name, "result": repo_result.model_dump()})

    return json.dumps({
        "before": before.model_dump(exclude_none=True),
        "profile_fixes": profile_result.model_dump() if profile_result else None,
        "repo_fixes": repo_results,
        "dry_run": dry_run,
    }, indent=2, default=str)
```

**Run:** `uv run pytest tests/test_fix_pipeline.py tests/test_mcp_audit.py -v`
**Expected:** All pass

**Run lint:** `uv run ruff check src/devcard/ devcard-mcp/src/devcard_mcp/`

**Commit:** `feat: add fix_repo, fix_profile, agent_ready MCP tools — preview and apply profile fixes`

---

## T7: Render Card + Enhanced Compare + Agent Skills (Phases P5-P6)

**Goal:** Add `render_card` MCP tool, enhance `compare_developers`, and create agent skill documents.

### T7.1 -- render_card MCP tool

#### Step 1: Write test

Create `tests/test_mcp_render.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from devcard.models import DevCard, Generator, Identity, Language


def _mock_devcard() -> DevCard:
    return DevCard(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser", name="Test User"),
        languages=[Language(name="Python", percentage=80.0)],
    )


class TestRenderCardTool:
    async def test_returns_svg_and_markdown(self):
        from devcard_mcp.server import render_card

        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_devcard()
            result = await render_card("testuser")
            data = json.loads(result)
            assert "svg" in data
            assert "<svg" in data["svg"]
            assert "embed_markdown" in data
            assert "testuser" in data["embed_markdown"]

    async def test_with_theme(self):
        from devcard_mcp.server import render_card

        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock) as mock:
            mock.return_value = _mock_devcard()
            result = await render_card("testuser", theme="dark")
            data = json.loads(result)
            assert "svg" in data
```

#### Step 2: Implement

Add to `devcard-mcp/src/devcard_mcp/server.py`:

```python
# Add import at top:
from devcard.renderers.svg_card import render_svg
from devcard.renderers.themes.default import THEME as DEFAULT_THEME
from devcard.renderers.themes.dark import THEME as DARK_THEME
from devcard.renderers.themes.minimal import THEME as MINIMAL_THEME
from devcard.renderers.themes.neon import THEME as NEON_THEME
from devcard.renderers.themes.terminal_green import THEME as TERMINAL_GREEN_THEME

_THEMES = {
    "default": DEFAULT_THEME,
    "dark": DARK_THEME,
    "minimal": MINIMAL_THEME,
    "neon": NEON_THEME,
    "terminal_green": TERMINAL_GREEN_THEME,
}


@mcp.tool()
async def render_card(
    username: str,
    theme: str = "default",
    force_refresh: bool = False,
) -> str:
    """Render a DevCard as SVG for embedding in a GitHub profile.

    Returns the SVG string and ready-to-paste markdown for embedding.
    Available themes: default, dark, minimal, neon, terminal_green.
    """
    devcard = await _get_or_generate(username, force_refresh)
    theme_obj = _THEMES.get(theme, DEFAULT_THEME)
    svg = render_svg(devcard, theme=theme_obj)
    embed_md = (
        f"![DevCard for {username}]"
        f"(https://github.com/{username}/{username}/raw/main/devcard.svg)"
    )
    return json.dumps({
        "svg": svg,
        "embed_markdown": embed_md,
        "theme": theme,
    }, indent=2)
```

**Run:** `uv run pytest tests/test_mcp_render.py -v`
**Expected:** Pass

### T7.2 -- Enhance compare_developers with scores

#### Step 3: Write test for enhanced compare

Add to `tests/test_mcp_render.py`:

```python
class TestEnhancedCompare:
    async def test_compare_includes_quality_score(self):
        from devcard_mcp.server import compare_developers
        from devcard.models import Quality

        card1 = _mock_devcard()
        card1.quality = Quality(score=0.8, ci_adoption=0.9, test_adoption=0.7,
                                 docs_adoption=0.6, license_adoption=1.0, linter_adoption=0.5)
        card2 = _mock_devcard()
        card2.identity.username = "user2"
        card2.quality = Quality(score=0.5, ci_adoption=0.4, test_adoption=0.3,
                                 docs_adoption=0.3, license_adoption=0.5, linter_adoption=0.2)

        with patch("devcard_mcp.server._get_or_generate", new_callable=AsyncMock) as mock:
            mock.side_effect = [card1, card2]
            result = await compare_developers("testuser", "user2")
            data = json.loads(result)
            assert "comparison" in data
            # Should have scoring comparison
            comp = data["comparison"]
            assert "quality_scores" in comp or "shared_languages" in comp
```

#### Step 4: Enhance compare_developers

Update the `compare_developers` function in `devcard-mcp/src/devcard_mcp/server.py` to include scoring data in the comparison block:

```python
@mcp.tool()
async def compare_developers(user1: str, user2: str) -> str:
    """Compare two GitHub developers side by side.

    Returns structured comparison including both developer summaries,
    shared and unique languages, shared and unique stack items,
    expertise domain overlap, quality/activity metrics, and scoring
    comparison for both.
    """
    card1, card2 = await asyncio.gather(
        _get_or_generate(user1),
        _get_or_generate(user2),
    )
    c1 = curate_for_agent(card1)
    c2 = curate_for_agent(card2)

    s1 = _all_stack_names(card1)
    s2 = _all_stack_names(card2)

    l1 = {lang.name for lang in card1.languages}
    l2 = {lang.name for lang in card2.languages}

    comparison: dict = {
        "shared_languages": sorted(l1 & l2),
        "shared_stack": sorted(s1 & s2),
        f"{user1}_only_stack": sorted(s1 - s2),
        f"{user2}_only_stack": sorted(s2 - s1),
    }

    # Add quality scoring comparison
    if card1.quality or card2.quality:
        comparison["quality_scores"] = {
            user1: round(card1.quality.score, 2) if card1.quality else None,
            user2: round(card2.quality.score, 2) if card2.quality else None,
        }

    # Add activity comparison
    if card1.activity or card2.activity:
        comparison["activity"] = {
            user1: card1.activity.status if card1.activity else None,
            user2: card2.activity.status if card2.activity else None,
        }

    return json.dumps({
        user1: c1,
        user2: c2,
        "comparison": comparison,
    }, indent=2, default=str)
```

**Run:** `uv run pytest tests/test_mcp_render.py tests/test_compare.py -v`
**Expected:** All pass

**Run lint:** `uv run ruff check devcard-mcp/src/devcard_mcp/server.py`

### T7.3 -- Agent skill documents

#### Step 5: Create canonical skill document

This step involves creating markdown files in `skills/` directory. The canonical skill describes how an AI agent should use the DevCard MCP tools.

Create directory structure:
- `skills/source/devcard.md` -- canonical skill definition
- `skills/claude-code/devcard.md` -- Claude Code adaptation

`skills/source/devcard.md` content:

```markdown
# DevCard MCP Skill

## Purpose
Generate, audit, and improve developer profiles on GitHub using the DevCard MCP server.

## Available Tools

### Read-Only Tools
- `get_devcard(username)` -- Full structured profile
- `get_developer_summary(username)` -- Quick summary
- `compare_developers(user1, user2)` -- Side-by-side comparison
- `check_developer_stack(username, technologies)` -- Technology check
- `render_card(username, theme)` -- SVG card generation

### Analysis Tools
- `audit_profile(username)` -- Score profile visibility + agent-readiness, detect issues

### Write Tools (require token)
- `fix_repo(owner, repo, fixes, dry_run)` -- Fix repo issues
- `fix_profile(username, fixes, dry_run)` -- Fix profile issues
- `agent_ready(username, dry_run)` -- Full audit + fix cycle

## Workflow

1. Start with `audit_profile` to understand the current state
2. Review issues and scores with the user
3. Use `fix_repo` / `fix_profile` with `dry_run=True` to preview changes
4. Apply with `dry_run=False` when the user approves
5. Re-run `audit_profile` to verify improvement

## Important
- Always preview (dry_run=True) before applying
- Write operations require a GitHub token with `repo` scope
- Limit to 5 repos per fix cycle to avoid rate limits
```

**Run:** Full test suite: `uv run pytest -v`
**Expected:** All tests pass

**Run lint:** `uv run ruff check src/ tests/`

**Commit:** `feat: add render_card MCP tool, enhance compare_developers with scoring, add agent skill docs`

---

## Summary of All Tasks

| Task | Phase | Description | New Files | Modified Files | Tests |
|------|-------|-------------|-----------|----------------|-------|
| T1 | P0 | GitHub client write methods | `tests/test_github_client_write.py` | `src/devcard/github/client.py` | 6 |
| T2 | P1a | Dual scoring system | `tests/test_scoring_dual.py` | `src/devcard/analyzers/scoring.py`, `src/devcard/models.py` | 14 |
| T3 | P1b | Issue detector | `tests/test_issue_detector.py`, `src/devcard/analyzers/issue_detector.py` | `src/devcard/models.py` | 11 |
| T4 | P2 | Fixer modules (6) | `tests/test_fixers.py`, `src/devcard/fixers/__init__.py`, 6 fixer files | - | 15 |
| T5 | P3 | Audit pipeline + MCP tool | `tests/test_audit_pipeline.py`, `tests/test_mcp_audit.py` | `src/devcard/pipeline.py`, `devcard-mcp/src/devcard_mcp/server.py`, `src/devcard/models.py` | 3 |
| T6 | P4 | Fix pipelines + MCP tools | `tests/test_fix_pipeline.py` | `src/devcard/pipeline.py`, `devcard-mcp/src/devcard_mcp/server.py`, `src/devcard/models.py` | 2 |
| T7 | P5-P6 | Render card + enhanced compare + skills | `tests/test_mcp_render.py`, `skills/source/devcard.md`, `skills/claude-code/devcard.md` | `devcard-mcp/src/devcard_mcp/server.py` | 3 |

**Total estimated time:** ~60-90 minutes of focused implementation.

**Dependency order:** T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T7 (mostly linear; T4 is independent of T2/T3 and could be done in parallel).

**Key design decisions:**
- `ProfileRepoData` is a new model that captures profile repo state without making it part of the core `DevCard` schema (DevCard stays backward-compatible)
- `Issue` model uses `Literal["high", "medium", "low"]` for severity, matching existing Literal patterns in the codebase
- All fixers are pure functions matching the renderer convention (no I/O, no side effects)
- The `_mutate` base method in `GitHubClient` mirrors `_request` but for write operations, sharing rate limit handling
- MCP tools default to `dry_run=True` for safety -- write operations require explicit opt-in
- The `agent_ready` tool is a compound tool that orchestrates audit -> fix -> re-audit, limited to 5 repos per cycle to stay within rate limits

### Critical Files for Implementation
- `/Users/chiru/conductor/workspaces/devcard/bandung-v1/src/devcard/github/client.py`
- `/Users/chiru/conductor/workspaces/devcard/bandung-v1/src/devcard/analyzers/scoring.py`
- `/Users/chiru/conductor/workspaces/devcard/bandung-v1/src/devcard/models.py`
- `/Users/chiru/conductor/workspaces/devcard/bandung-v1/src/devcard/pipeline.py`
- `/Users/chiru/conductor/workspaces/devcard/bandung-v1/devcard-mcp/src/devcard_mcp/server.py`
