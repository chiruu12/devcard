from __future__ import annotations

from datetime import UTC, datetime

from devcard.analyzers.scoring import (
    compute_agent_readiness_score,
    compute_human_visibility_score,
)
from devcard.models import (
    Activity,
    CommitQuality,
    DevCard,
    Generator,
    Identity,
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
        assert compute_human_visibility_score(card, profile) == 0

    def test_bio_gives_10_points(self):
        card = _make_devcard(identity=Identity(username="u", bio="I build things"))
        profile = ProfileRepoData()
        assert compute_human_visibility_score(card, profile) >= 10

    def test_profile_readme_gives_15_points(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_profile_readme=True, readme_length=200)
        assert compute_human_visibility_score(card, profile) >= 15

    def test_repo_descriptions_give_points(self):
        card = _make_devcard(
            projects=[
                Project(name="a", description="Repo A"),
                Project(name="b", description="Repo B"),
                Project(name="c"),
            ],
        )
        profile = ProfileRepoData()
        assert compute_human_visibility_score(card, profile) >= 8

    def test_full_profile_scores_high(self):
        card = _make_devcard(
            identity=Identity(
                username="u",
                bio="Full-stack dev",
                blog="https://example.com",
                twitter_username="udev",
            ),
            projects=[
                Project(
                    name="big",
                    description="Main project",
                    topics=["python", "cli"],
                    is_signature=True,
                ),
                Project(
                    name="lib",
                    description="A library",
                    topics=["lib"],
                ),
            ],
            quality=Quality(
                docs_adoption=0.9,
                license_adoption=0.8,
                ci_adoption=0.7,
            ),
            activity=Activity(status="active", consistency_score=80),
        )
        profile = ProfileRepoData(has_profile_readme=True, readme_length=500)
        assert compute_human_visibility_score(card, profile) >= 70

    def test_score_clamped_to_100(self):
        card = _make_devcard(
            identity=Identity(
                username="u",
                bio="Full-stack",
                blog="https://blog.dev",
                twitter_username="udev",
            ),
            projects=[
                Project(
                    name=f"p{i}",
                    description=f"Project {i}",
                    topics=["t1", "t2"],
                    is_signature=True,
                )
                for i in range(20)
            ],
            quality=Quality(
                docs_adoption=1.0,
                license_adoption=1.0,
                ci_adoption=1.0,
            ),
            activity=Activity(status="active", consistency_score=100),
        )
        profile = ProfileRepoData(has_profile_readme=True, readme_length=5000)
        score = compute_human_visibility_score(card, profile)
        assert score <= 100

    def test_returns_int(self):
        card = _make_devcard(
            identity=Identity(username="u", bio="test"),
        )
        profile = ProfileRepoData()
        result = compute_human_visibility_score(card, profile)
        assert isinstance(result, int)


class TestAgentReadinessScore:
    def test_empty_profile_scores_zero(self):
        card = _make_devcard()
        profile = ProfileRepoData()
        assert compute_agent_readiness_score(card, profile) == 0

    def test_devcard_json_gives_5_bonus_points(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_devcard_json=True)
        assert compute_agent_readiness_score(card, profile) == 5

    def test_llms_txt_gives_5_bonus_points(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_llms_txt=True)
        assert compute_agent_readiness_score(card, profile) == 5

    def test_structured_readmes_give_points(self):
        card = _make_devcard(
            quality=Quality(docs_adoption=1.0),
        )
        profile = ProfileRepoData()
        assert compute_agent_readiness_score(card, profile) >= 10

    def test_stack_depth_graduated(self):
        small_stack = _make_devcard(
            stack=Stack(
                frameworks=[StackItem(name="FastAPI", category="framework")],
            ),
        )
        medium_stack = _make_devcard(
            stack=Stack(
                frameworks=[StackItem(name=f"fw{i}", category="framework") for i in range(5)],
            ),
        )
        large_stack = _make_devcard(
            stack=Stack(
                frameworks=[StackItem(name=f"fw{i}", category="framework") for i in range(10)],
            ),
        )
        profile = ProfileRepoData()
        small = compute_agent_readiness_score(small_stack, profile)
        medium = compute_agent_readiness_score(medium_stack, profile)
        large = compute_agent_readiness_score(large_stack, profile)
        assert small < medium < large

    def test_commit_quality_contributes(self):
        card = _make_devcard(
            commit_quality=CommitQuality(
                avg_message_length=60,
                conventional_commits_pct=80,
                commits_analyzed=50,
            ),
        )
        profile = ProfileRepoData()
        assert compute_agent_readiness_score(card, profile) >= 5

    def test_repo_descriptions_contribute(self):
        card = _make_devcard(
            projects=[
                Project(name="a", description="A tool"),
                Project(name="b", description="A lib"),
            ],
        )
        profile = ProfileRepoData()
        assert compute_agent_readiness_score(card, profile) >= 8

    def test_good_dev_scores_high_without_special_files(self):
        """A developer with good repos should score 60+ without devcard.json/llms.txt."""
        card = _make_devcard(
            projects=[
                Project(
                    name="p1",
                    description="A web API",
                    topics=["python", "api"],
                    classification="library",
                ),
                Project(
                    name="p2",
                    description="CLI tool",
                    topics=["rust", "cli"],
                    classification="tool",
                ),
            ],
            quality=Quality(
                docs_adoption=0.9,
                ci_adoption=0.8,
                test_adoption=0.7,
                license_adoption=0.8,
            ),
            stack=Stack(
                frameworks=[StackItem(name="FastAPI", category="framework")],
                libraries=[
                    StackItem(name="pydantic", category="library"),
                    StackItem(name="httpx", category="library"),
                    StackItem(name="pytest", category="library"),
                    StackItem(name="ruff", category="library"),
                ],
            ),
            commit_quality=CommitQuality(
                avg_message_length=55,
                conventional_commits_pct=60,
                commits_analyzed=100,
            ),
        )
        profile = ProfileRepoData()
        score = compute_agent_readiness_score(card, profile)
        assert score >= 60

    def test_full_agent_ready_scores_high(self):
        card = _make_devcard(
            projects=[
                Project(
                    name="p1",
                    description="A web API",
                    topics=["python", "api"],
                    classification="library",
                ),
                Project(
                    name="p2",
                    description="CLI tool",
                    topics=["rust"],
                    classification="tool",
                ),
            ],
            quality=Quality(
                docs_adoption=0.9,
                ci_adoption=0.8,
                test_adoption=0.7,
                license_adoption=0.8,
            ),
            stack=Stack(
                frameworks=[StackItem(name="FastAPI", category="framework")],
                libraries=[
                    StackItem(name="pydantic", category="library"),
                    StackItem(name="httpx", category="library"),
                    StackItem(name="pytest", category="library"),
                    StackItem(name="ruff", category="library"),
                ],
            ),
            commit_quality=CommitQuality(
                avg_message_length=55,
                conventional_commits_pct=60,
                commits_analyzed=100,
            ),
        )
        profile = ProfileRepoData(has_devcard_json=True, has_llms_txt=True)
        assert compute_agent_readiness_score(card, profile) >= 70

    def test_score_clamped_to_100(self):
        card = _make_devcard(
            projects=[
                Project(
                    name=f"p{i}",
                    description=f"Project {i}",
                    topics=["t1", "t2"],
                    classification="library",
                )
                for i in range(20)
            ],
            quality=Quality(
                docs_adoption=1.0,
                ci_adoption=1.0,
                test_adoption=1.0,
                license_adoption=1.0,
            ),
            stack=Stack(
                frameworks=[StackItem(name=f"fw{i}", category="framework") for i in range(10)],
            ),
            commit_quality=CommitQuality(
                avg_message_length=72,
                conventional_commits_pct=100,
                commits_analyzed=200,
            ),
        )
        profile = ProfileRepoData(has_devcard_json=True, has_llms_txt=True)
        score = compute_agent_readiness_score(card, profile)
        assert score <= 100

    def test_returns_int(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_devcard_json=True)
        result = compute_agent_readiness_score(card, profile)
        assert isinstance(result, int)
