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
    Project,
    Quality,
    Stack,
    StackItem,
)
from devcard.output.llms_txt import to_llms_txt


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser", name="Test User", bio="I build things"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


class TestLlmsTxt:
    def test_starts_with_title(self):
        result = to_llms_txt(_make_devcard())
        assert result.startswith("# DevCard: testuser")

    def test_has_blockquote_summary(self):
        dc = _make_devcard(summary="ML dev who loves Python.")
        result = to_llms_txt(dc)
        assert "> ML dev who loves Python." in result

    def test_no_blockquote_without_summary(self):
        dc = _make_devcard(summary=None)
        result = to_llms_txt(dc)
        assert "\n> " not in result

    def test_projects_with_urls(self):
        dc = _make_devcard(
            projects=[
                Project(
                    name="NexNet",
                    description="Neural net library",
                    url="https://github.com/testuser/NexNet",
                    stars=5,
                    language="Python",
                ),
            ],
        )
        result = to_llms_txt(dc)
        assert "## Projects" in result
        assert "[NexNet](https://github.com/testuser/NexNet)" in result
        assert "Neural net library" in result
        assert "5 stars" in result

    def test_projects_without_urls(self):
        dc = _make_devcard(
            projects=[
                Project(
                    name="MyTool",
                    description="A handy tool",
                    stars=2,
                ),
            ],
        )
        result = to_llms_txt(dc)
        assert "## Projects" in result
        assert "- MyTool: A handy tool (2 stars)" in result
        # Should not have markdown link syntax
        assert "[MyTool](" not in result

    def test_minimal_devcard(self):
        dc = DevCard(
            generated_at=datetime.now(UTC),
            generator=Generator(name="devcard", version="0.1.0"),
            identity=Identity(username="minuser"),
        )
        result = to_llms_txt(dc)
        assert isinstance(result, str)
        assert "# DevCard: minuser" in result

    def test_skills_section(self):
        dc = _make_devcard(
            languages=[
                Language(name="Python", percentage=45.2),
                Language(name="Shell", percentage=2.0),
            ],
            stack=Stack(
                frameworks=[StackItem(name="FastAPI", category="framework")],
                libraries=[StackItem(name="httpx", category="library")],
            ),
        )
        result = to_llms_txt(dc)
        assert "## Skills" in result
        assert "- Python (45.2%)" in result
        assert "- Shell (2.0%)" in result
        assert "FastAPI" in result
        assert "httpx" in result

    def test_expertise_section(self):
        dc = _make_devcard(
            expertise=Expertise(
                profile_type="ml",
                domains=[
                    Domain(name="Machine Learning", confidence=0.85),
                    Domain(name="Computer Vision", confidence=0.72),
                ],
                focus_areas=[FocusArea(name="Deep Learning", evidence=["pytorch"])],
            ),
        )
        result = to_llms_txt(dc)
        assert "## Expertise" in result
        assert "Machine Learning (0.85 confidence)" in result
        assert "Computer Vision (0.72 confidence)" in result
        assert "Deep Learning" in result

    def test_collaboration_section(self):
        dc = _make_devcard(
            collaboration=Collaboration(
                organizations=["jenkinsci", "apache"],
                contribution_style="contributor",
            ),
        )
        result = to_llms_txt(dc)
        assert "## Collaboration" in result
        assert "Organizations: jenkinsci, apache" in result
        assert "Contribution style: contributor" in result

    def test_body_includes_profile_type_and_location(self):
        dc = _make_devcard(
            identity=Identity(username="testuser", name="Test User", location="India"),
            expertise=Expertise(profile_type="ml"),
        )
        result = to_llms_txt(dc)
        assert "Ml Developer" in result
        assert "based in India" in result

    def test_body_includes_activity(self):
        dc = _make_devcard(
            activity=Activity(
                status="active",
                commits_last_year=973,
                peak_hours=[10, 14],
            ),
        )
        result = to_llms_txt(dc)
        assert "Active contributor" in result
        assert "commits/week" in result

    def test_body_includes_quality_score(self):
        dc = _make_devcard(
            quality=Quality(score=0.65),
        )
        result = to_llms_txt(dc)
        assert "Quality score: 0.65" in result
