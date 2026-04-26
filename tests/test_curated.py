from __future__ import annotations

from datetime import UTC, datetime

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
    OrgContribution,
    Project,
    Quality,
    QualityDetail,
    Stack,
    StackItem,
)
from devcard.output.curated import curate_for_agent


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser", name="Test User", bio="I build things"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


def _full_devcard() -> DevCard:
    return _make_devcard(
        summary="ML engineer specializing in Python. Active, ~500 commits/year.",
        languages=[
            Language(name="Python", percentage=60.0, color="#3572A5", bytes=1000000),
            Language(name="TypeScript", percentage=25.0, color="#3178c6", bytes=500000),
            Language(name="Go", percentage=15.0, color="#00ADD8", bytes=200000),
        ],
        stack=Stack(
            frameworks=[StackItem(name="FastAPI", category="framework", source="repo1")],
            libraries=[StackItem(name="httpx", category="library", source="repo1")],
            tools=[StackItem(name="docker", category="tool", source="repo2")],
        ),
        projects=[
            Project(
                name="cool-project",
                description="A cool project",
                url="https://github.com/test/cool",
                stars=100,
                forks=20,
                language="Python",
                topics=["ml", "ai"],
                status="active",
                maturity="mature",
                classification="library",
            ),
            Project(name="another-one", stars=50, language="TypeScript", status="maintained"),
        ],
        expertise=Expertise(
            domains=[Domain(name="Machine Learning", confidence=0.85)],
            profile_type="ml",
            focus_areas=[FocusArea(name="Neural Networks", evidence=["pytorch", "tensorflow"])],
        ),
        collaboration=Collaboration(
            organizations=["orgA"],
            contribution_style="contributor",
            org_contributions=[
                OrgContribution(org="orgA", prs_opened=5, prs_merged=3, issues_opened=2, commits=15)
            ],
        ),
        activity=Activity(
            status="active",
            commits_last_year=500,
            peak_hours=[10, 14, 16],
            timezone_estimate="UTC+5:30",
            heatmap=[
                [5, 3, 0, 0, 0, 0, 0, 0, 2, 4, 8, 6, 3, 5, 7, 4, 3, 2, 1, 0, 0, 0, 0, 0],
                [4, 2, 0, 0, 0, 0, 0, 0, 3, 5, 7, 5, 4, 6, 8, 5, 2, 1, 0, 0, 0, 0, 0, 0],
                [6, 4, 1, 0, 0, 0, 0, 0, 4, 6, 9, 7, 5, 7, 9, 6, 4, 3, 2, 0, 0, 0, 0, 0],
                [3, 1, 0, 0, 0, 0, 0, 0, 1, 3, 5, 4, 2, 4, 6, 3, 1, 0, 0, 0, 0, 0, 0, 0],
                [5, 3, 0, 0, 0, 0, 0, 0, 3, 5, 8, 6, 4, 6, 8, 5, 3, 2, 1, 0, 0, 0, 0, 0],
                [2, 1, 0, 0, 0, 0, 0, 0, 0, 1, 2, 1, 0, 1, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ],
        ),
        quality=Quality(
            score=0.65,
            ci_adoption=0.8,
            test_adoption=0.6,
            docs_adoption=0.5,
            license_adoption=0.9,
            linter_adoption=0.3,
            details=[QualityDetail(repo="cool-project", signals=["ci", "testing", "license"])],
        ),
    )


class TestCurateForAgent:
    def test_full_devcard_has_all_sections(self):
        curated = curate_for_agent(_full_devcard())
        assert "summary" in curated
        assert "identity" in curated
        assert "languages" in curated
        assert "stack" in curated
        assert "projects" in curated
        assert "expertise" in curated
        assert "collaboration" in curated
        assert "activity" in curated
        assert "quality" in curated

    def test_minimal_devcard_has_identity(self):
        curated = curate_for_agent(_make_devcard())
        assert curated["identity"]["username"] == "testuser"
        assert "languages" not in curated
        assert "stack" not in curated

    def test_identity_excludes_avatar(self):
        dc = _make_devcard(
            identity=Identity(
                username="test", avatar_url="https://example.com/avatar.png", public_gists=5
            )
        )
        curated = curate_for_agent(dc)
        assert "avatar_url" not in curated["identity"]
        assert "public_gists" not in curated["identity"]

    def test_languages_limited_to_8(self):
        langs = [Language(name=f"Lang{i}", percentage=100 / 10) for i in range(10)]
        curated = curate_for_agent(_make_devcard(languages=langs))
        assert len(curated["languages"]["items"]) == 8

    def test_languages_has_coding_ratio(self):
        curated = curate_for_agent(_full_devcard())
        assert "coding_ratio" in curated["languages"]

    def test_languages_exclude_bytes_and_color(self):
        curated = curate_for_agent(_full_devcard())
        for lang in curated["languages"]["items"]:
            assert "bytes" not in lang
            assert "color" not in lang

    def test_stack_excludes_source(self):
        curated = curate_for_agent(_full_devcard())
        for category_items in curated["stack"].values():
            for item in category_items:
                assert isinstance(item, str)

    def test_projects_exclude_forks_and_topics(self):
        curated = curate_for_agent(_full_devcard())
        for proj in curated["projects"]:
            assert "forks" not in proj
            assert "topics" not in proj
            assert "url" not in proj
            assert "maturity" not in proj
            assert "classification" not in proj

    def test_expertise_excludes_evidence(self):
        curated = curate_for_agent(_full_devcard())
        focus_areas = curated["expertise"]["focus_areas"]
        assert isinstance(focus_areas[0], str)

    def test_activity_has_stats_not_heatmap(self):
        curated = curate_for_agent(_full_devcard())
        activity = curated["activity"]
        assert "heatmap" not in activity
        assert "current_streak" not in activity
        assert "longest_streak" not in activity
        assert "commits_per_week" in activity
        assert "consistency" in activity
        assert "active_days_per_week" in activity

    def test_activity_commits_per_week(self):
        curated = curate_for_agent(_full_devcard())
        assert curated["activity"]["commits_per_week"] == round(500 / 52, 1)

    def test_quality_excludes_details(self):
        curated = curate_for_agent(_full_devcard())
        assert "details" not in curated["quality"]
        assert "score" in curated["quality"]
        assert "ci_adoption" in curated["quality"]


class TestConsistencyComputation:
    def test_uniform_heatmap_is_high(self):
        uniform = [[5] * 24 for _ in range(7)]
        dc = _make_devcard(activity=Activity(status="active", heatmap=uniform))
        curated = curate_for_agent(dc)
        assert curated["activity"]["consistency"] == "high"

    def test_sporadic_heatmap_is_low(self):
        sporadic = [[0] * 24 for _ in range(7)]
        sporadic[0] = [100] * 24
        dc = _make_devcard(activity=Activity(status="moderate", heatmap=sporadic))
        curated = curate_for_agent(dc)
        assert curated["activity"]["consistency"] == "low"

    def test_no_heatmap_fallback_active(self):
        dc = _make_devcard(activity=Activity(status="active"))
        curated = curate_for_agent(dc)
        assert curated["activity"]["consistency"] == "high"

    def test_no_heatmap_fallback_dormant(self):
        dc = _make_devcard(activity=Activity(status="dormant"))
        curated = curate_for_agent(dc)
        assert curated["activity"]["consistency"] == "low"

    def test_empty_heatmap(self):
        dc = _make_devcard(activity=Activity(status="sporadic", heatmap=[]))
        curated = curate_for_agent(dc)
        assert curated["activity"]["consistency"] == "low"
