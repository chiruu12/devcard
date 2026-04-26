from __future__ import annotations

from datetime import UTC, datetime

from devcard.analyzers.contribution_style import analyze_contribution_style
from devcard.analyzers.developer_type import analyze_developer_type
from devcard.analyzers.project_classifier import classify_projects
from devcard.analyzers.scoring import compute_quality_score
from devcard.models import (
    Collaboration,
    DevCard,
    Domain,
    Expertise,
    FocusArea,
    Generator,
    Identity,
    Language,
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


class TestDeveloperType:
    def test_ml_user(self):
        card = _make_devcard(
            languages=[Language(name="Python", percentage=70.0)],
            projects=[
                Project(name="ml-project", topics=["machine-learning", "deep-learning"]),
            ],
            stack=Stack(frameworks=[StackItem(name="TensorFlow", category="framework")]),
            expertise=Expertise(
                domains=[Domain(name="ML", confidence=0.9)],
                focus_areas=[FocusArea(name="ML")],
            ),
        )
        assert analyze_developer_type(card) == "ml"

    def test_frontend_user(self):
        card = _make_devcard(
            languages=[
                Language(name="TypeScript", percentage=65.0),
                Language(name="CSS", percentage=35.0),
            ],
            projects=[Project(name="app", topics=["react", "frontend"])],
            stack=Stack(frameworks=[StackItem(name="React", category="framework")]),
            expertise=Expertise(),
        )
        assert analyze_developer_type(card) == "frontend"

    def test_generic_user_defaults_fullstack(self):
        card = _make_devcard()
        assert analyze_developer_type(card) == "full_stack"


class TestProjectClassifier:
    def test_library_in_name(self):
        card = _make_devcard(
            projects=[Project(name="my-lib", description="A useful library")],
        )
        classify_projects(card)
        assert card.projects[0].classification == "library"

    def test_learning_topic(self):
        card = _make_devcard(
            projects=[Project(name="learn-rust", topics=["learning", "course"])],
        )
        classify_projects(card)
        assert card.projects[0].classification == "learning"

    def test_tool_in_description(self):
        card = _make_devcard(
            projects=[Project(name="formatter", description="A CLI tool for formatting")],
        )
        classify_projects(card)
        assert card.projects[0].classification == "tool"

    def test_generic_defaults_application(self):
        card = _make_devcard(
            projects=[Project(name="my-project", description="Does stuff")],
        )
        classify_projects(card)
        assert card.projects[0].classification == "application"

    def test_does_not_overwrite_existing(self):
        card = _make_devcard(
            projects=[Project(name="my-lib", classification="framework")],
        )
        classify_projects(card)
        assert card.projects[0].classification == "framework"

    def test_config_classification(self):
        card = _make_devcard(
            projects=[Project(name="dotfiles", description="My configuration")],
        )
        classify_projects(card)
        assert card.projects[0].classification == "config"

    def test_signature_project_marked(self):
        card = _make_devcard(
            projects=[
                Project(name="big", stars=500, forks=100),
                Project(name="small", stars=5, forks=0),
            ],
        )
        classify_projects(card)
        assert card.projects[0].is_signature is True
        assert card.projects[1].is_signature is False

    def test_no_signature_if_no_stars(self):
        card = _make_devcard(
            projects=[Project(name="empty", stars=0, forks=0)],
        )
        classify_projects(card)
        assert card.projects[0].is_signature is False

    def test_narrative_generated(self):
        card = _make_devcard(
            projects=[
                Project(
                    name="cool-lib", stars=200, language="Python",
                    description="A really cool library",
                ),
            ],
        )
        classify_projects(card)
        assert card.projects[0].narrative is not None
        assert "python" in card.projects[0].narrative.lower()

    def test_signature_narrative_prefix(self):
        card = _make_devcard(
            projects=[Project(name="top", stars=100, language="Rust")],
        )
        classify_projects(card)
        assert card.projects[0].narrative.startswith("Flagship:")


class TestContributionStyle:
    def test_maintainer(self):
        card = _make_devcard(
            projects=[Project(name=f"p{i}", stars=50) for i in range(5)],
            collaboration=Collaboration(external_contributions=2),
        )
        assert analyze_contribution_style(card) == "maintainer"

    def test_contributor(self):
        card = _make_devcard(
            collaboration=Collaboration(
                external_contributions=15,
                pull_requests_opened=10,
                organizations=["org1", "org2", "org3"],
            ),
        )
        assert analyze_contribution_style(card) == "contributor"

    def test_solo_builder(self):
        card = _make_devcard(
            projects=[Project(name="solo")],
            collaboration=Collaboration(external_contributions=0),
        )
        assert analyze_contribution_style(card) == "solo_builder"

    def test_no_collaboration(self):
        card = _make_devcard()
        assert analyze_contribution_style(card) == "solo_builder"


class TestScoring:
    def test_weighted_composite(self):
        card = _make_devcard(
            quality=Quality(
                test_adoption=0.8,
                ci_adoption=0.6,
                docs_adoption=0.5,
                license_adoption=1.0,
                linter_adoption=0.3,
            ),
        )
        compute_quality_score(card)
        expected = round(0.8 * 0.3 + 0.6 * 0.25 + 0.5 * 0.2 + 1.0 * 0.15 + 0.3 * 0.1, 3)
        assert card.quality.score == expected

    def test_all_zeros(self):
        card = _make_devcard(quality=Quality())
        compute_quality_score(card)
        assert card.quality.score == 0.0

    def test_all_ones(self):
        card = _make_devcard(
            quality=Quality(
                test_adoption=1.0,
                ci_adoption=1.0,
                docs_adoption=1.0,
                license_adoption=1.0,
                linter_adoption=1.0,
            ),
        )
        compute_quality_score(card)
        assert card.quality.score == 1.0

    def test_no_quality(self):
        card = _make_devcard()
        compute_quality_score(card)
        assert card.quality is None
