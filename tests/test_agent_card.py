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
    Stack,
    StackItem,
)
from devcard.output.agent_card import to_agent_card


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser", name="Test User", bio="I build things"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


class TestAgentCardHeaderFooter:
    def test_header_and_footer(self):
        result = to_agent_card(_make_devcard())
        assert result.startswith("=== DEVCARD: testuser ===")
        assert result.rstrip().endswith("=== END ===")


class TestAgentCardIdentity:
    def test_identity_line(self):
        dc = _make_devcard(
            identity=Identity(
                username="chiruu12",
                name="Chirag",
                location="India",
                hireable=False,
            ),
            expertise=Expertise(profile_type="ml"),
        )
        result = to_agent_card(dc)
        assert "Chirag" in result
        assert "Ml Developer" in result
        assert "India" in result
        assert "Hireable: No" in result

    def test_identity_hireable_yes(self):
        dc = _make_devcard(
            identity=Identity(username="dev1", name="Dev", hireable=True),
        )
        result = to_agent_card(dc)
        assert "Hireable: Yes" in result


class TestAgentCardLanguages:
    def test_languages_section(self):
        dc = _make_devcard(
            languages=[
                Language(name="Python", percentage=45.2),
                Language(name="Jupyter Notebook", percentage=3.1),
                Language(name="Shell", percentage=2.0),
            ],
        )
        result = to_agent_card(dc)
        assert "--- LANGUAGES ---" in result
        assert "Python 45.2%" in result
        assert "Jupyter Notebook 3.1%" in result
        assert "Shell 2.0%" in result


class TestAgentCardStack:
    def test_stack_section(self):
        dc = _make_devcard(
            stack=Stack(
                frameworks=[StackItem(name="FastAPI", category="framework")],
                libraries=[StackItem(name="httpx", category="library")],
                tools=[StackItem(name="docker", category="tool")],
            ),
        )
        result = to_agent_card(dc)
        assert "--- STACK ---" in result
        assert "Frameworks: FastAPI" in result
        assert "Libraries: httpx" in result
        assert "Tools: docker" in result


class TestAgentCardProjects:
    def test_projects_section(self):
        dc = _make_devcard(
            projects=[
                Project(
                    name="NexNet",
                    description="Neural network library",
                    stars=5,
                    language="Python",
                    status="active",
                ),
                Project(
                    name="DIP_OCR",
                    description="Custom OCR tool",
                    stars=2,
                    language="Python",
                    status="maintained",
                ),
            ],
        )
        result = to_agent_card(dc)
        assert "--- TOP PROJECTS ---" in result
        assert "NexNet" in result
        assert "Neural network library" in result
        assert "5 stars" in result
        assert "DIP_OCR" in result


class TestAgentCardQuality:
    def test_quality_section(self):
        dc = _make_devcard(
            quality=Quality(
                score=0.65,
                test_adoption=0.4,
                ci_adoption=0.6,
                docs_adoption=0.5,
                license_adoption=0.8,
                linter_adoption=0.3,
            ),
        )
        result = to_agent_card(dc)
        assert "--- QUALITY ---" in result
        assert "Score: 0.65" in result
        assert "Tests: 40%" in result
        assert "CI: 60%" in result
        assert "Docs: 50%" in result
        assert "License: 80%" in result
        assert "Linter: 30%" in result


class TestAgentCardExpertise:
    def test_expertise_section(self):
        dc = _make_devcard(
            expertise=Expertise(
                profile_type="ml",
                domains=[
                    Domain(name="Machine Learning", confidence=0.90),
                    Domain(name="Computer Vision", confidence=0.75),
                ],
                focus_areas=[
                    FocusArea(name="Neural Networks"),
                    FocusArea(name="OCR"),
                ],
            ),
        )
        result = to_agent_card(dc)
        assert "--- EXPERTISE ---" in result
        assert "Type: ml" in result
        assert "Machine Learning (0.90)" in result
        assert "Computer Vision (0.75)" in result
        assert "Focus: Neural Networks, OCR" in result


class TestAgentCardCollaboration:
    def test_collaboration_section(self):
        dc = _make_devcard(
            collaboration=Collaboration(
                organizations=["jenkinsci"],
                contribution_style="contributor",
                org_contributions=[
                    OrgContribution(
                        org="jenkinsci",
                        prs_merged=3,
                        issues_opened=2,
                    ),
                ],
            ),
        )
        result = to_agent_card(dc)
        assert "--- COLLABORATION ---" in result
        assert "Orgs: jenkinsci" in result
        assert "Style: contributor" in result
        assert "jenkinsci" in result
        assert "3 PRs merged" in result
        assert "2 issues" in result


class TestAgentCardActivity:
    def test_activity_section(self):
        dc = _make_devcard(
            activity=Activity(
                status="active",
                commits_last_year=973,
                peak_hours=[10, 14, 16],
                timezone_estimate="UTC+5:30",
            ),
        )
        result = to_agent_card(dc)
        assert "--- ACTIVITY ---" in result
        assert "Status: active" in result
        assert "commits/week" in result
        assert "Consistency: high" in result
        assert "10:00" in result
        assert "14:00" in result
        assert "16:00" in result
        assert "UTC+5:30" in result


class TestAgentCardMinimal:
    def test_minimal_devcard(self):
        dc = DevCard(
            generated_at=datetime.now(UTC),
            generator=Generator(name="devcard", version="0.1.0"),
            identity=Identity(username="minuser"),
        )
        result = to_agent_card(dc)
        assert result.startswith("=== DEVCARD: minuser ===")
        assert result.rstrip().endswith("=== END ===")
        assert isinstance(result, str)

    def test_sections_skip_when_empty(self):
        dc = DevCard(
            generated_at=datetime.now(UTC),
            generator=Generator(name="devcard", version="0.1.0"),
            identity=Identity(username="minuser"),
        )
        result = to_agent_card(dc)
        assert "--- LANGUAGES ---" not in result
        assert "--- STACK ---" not in result
        assert "--- TOP PROJECTS ---" not in result
        assert "--- EXPERTISE ---" not in result
        assert "--- COLLABORATION ---" not in result
        assert "--- ACTIVITY ---" not in result
        assert "--- QUALITY ---" not in result
