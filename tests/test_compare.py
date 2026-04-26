from __future__ import annotations

from datetime import UTC, datetime

from devcard.models import (
    Activity,
    DevCard,
    Domain,
    Expertise,
    FocusArea,
    Generator,
    Identity,
    Language,
    Project,
    Quality,
)
from devcard.renderers.compare import render_compare


def _make_devcard(username: str, **overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username=username, name=username.title()),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


def _card_a():
    return _make_devcard(
        "alice",
        languages=[
            Language(name="Python", percentage=70.0, category="logic"),
            Language(name="TypeScript", percentage=30.0, category="logic"),
        ],
        projects=[
            Project(name="ml-lib", stars=500, language="Python",
                    status="active", is_signature=True),
        ],
        quality=Quality(score=0.8, ci_adoption=0.9, test_adoption=0.7,
                         docs_adoption=0.6, license_adoption=1.0, linter_adoption=0.5),
        expertise=Expertise(
            domains=[Domain(name="Machine Learning", confidence=0.9)],
            profile_type="ml",
            focus_areas=[FocusArea(name="ML")],
        ),
        activity=Activity(status="active", commits_last_year=1200,
                          consistency_score=75, peak_hours=[10, 14]),
    )


def _card_b():
    return _make_devcard(
        "bob",
        languages=[
            Language(name="TypeScript", percentage=60.0, category="logic"),
            Language(name="CSS", percentage=20.0, category="presentation"),
            Language(name="Python", percentage=20.0, category="logic"),
        ],
        projects=[
            Project(name="web-app", stars=200, language="TypeScript",
                    status="active", is_signature=True),
        ],
        quality=Quality(score=0.5, ci_adoption=0.4, test_adoption=0.5,
                         docs_adoption=0.3, license_adoption=0.8, linter_adoption=0.7),
        expertise=Expertise(
            domains=[Domain(name="Frontend Development", confidence=0.85)],
            profile_type="frontend",
            focus_areas=[FocusArea(name="Frontend")],
        ),
        activity=Activity(status="moderate", commits_last_year=400,
                          consistency_score=40, peak_hours=[15, 20]),
    )


class TestCompareRenderer:
    def test_contains_both_usernames(self):
        output = render_compare(_card_a(), _card_b())
        assert "alice" in output
        assert "bob" in output

    def test_contains_languages(self):
        output = render_compare(_card_a(), _card_b())
        assert "Python" in output
        assert "TypeScript" in output

    def test_contains_quality_scores(self):
        output = render_compare(_card_a(), _card_b())
        assert "Quality" in output

    def test_contains_expertise(self):
        output = render_compare(_card_a(), _card_b())
        assert "Machine Learning" in output
        assert "Frontend" in output

    def test_contains_activity(self):
        output = render_compare(_card_a(), _card_b())
        assert "ACTIVE" in output
        assert "MODERATE" in output

    def test_contains_projects(self):
        output = render_compare(_card_a(), _card_b())
        assert "ml-lib" in output
        assert "web-app" in output

    def test_minimal_cards_render(self):
        c1 = _make_devcard("empty1")
        c2 = _make_devcard("empty2")
        output = render_compare(c1, c2)
        assert "empty1" in output
        assert "empty2" in output
