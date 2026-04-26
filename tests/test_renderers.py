from __future__ import annotations

import xml.etree.ElementTree as ET
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
from devcard.renderers.svg_card import render_svg
from devcard.renderers.terminal import render_terminal
from devcard.renderers.themes.dark import THEME as DARK_THEME


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser", name="Test User", bio="I build things"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


def _populated_devcard() -> DevCard:
    return _make_devcard(
        languages=[
            Language(name="Python", percentage=60.0, color="#3572A5"),
            Language(name="TypeScript", percentage=25.0, color="#3178c6"),
            Language(name="Go", percentage=15.0, color="#00ADD8"),
        ],
        projects=[
            Project(name="cool-project", stars=100, language="Python", status="active"),
            Project(name="another-one", stars=50, language="TypeScript", status="maintained"),
        ],
        quality=Quality(
            score=0.65,
            ci_adoption=0.8,
            test_adoption=0.6,
            docs_adoption=0.5,
            license_adoption=0.9,
            linter_adoption=0.3,
        ),
        expertise=Expertise(
            domains=[Domain(name="Web Development", confidence=0.85)],
            profile_type="backend",
            focus_areas=[FocusArea(name="Web Development", evidence=["Python", "FastAPI"])],
        ),
        activity=Activity(
            status="active",
            peak_hours=[10, 14, 16],
            timezone_estimate="UTC-8",
        ),
    )


class TestTerminalRenderer:
    def test_contains_username(self):
        output = render_terminal(_populated_devcard())
        assert "testuser" in output

    def test_contains_languages(self):
        output = render_terminal(_populated_devcard())
        assert "Python" in output
        assert "TypeScript" in output

    def test_contains_projects(self):
        output = render_terminal(_populated_devcard())
        assert "cool-project" in output

    def test_contains_quality(self):
        output = render_terminal(_populated_devcard())
        assert "Quality" in output

    def test_minimal_card_renders(self):
        output = render_terminal(_make_devcard())
        assert "testuser" in output


class TestSVGRenderer:
    def test_valid_xml(self):
        svg = render_svg(_populated_devcard())
        ET.fromstring(svg)

    def test_no_foreign_object(self):
        svg = render_svg(_populated_devcard())
        root = ET.fromstring(svg)
        ns = "{http://www.w3.org/2000/svg}"
        foreign = root.findall(f".//{ns}foreignObject")
        assert len(foreign) == 0

    def test_size_under_50kb(self):
        svg = render_svg(_populated_devcard())
        assert len(svg) < 50000

    def test_has_xmlns(self):
        svg = render_svg(_populated_devcard())
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_dark_theme_colors(self):
        svg = render_svg(_populated_devcard(), theme=DARK_THEME)
        assert "#0d1117" in svg

    def test_minimal_card_renders(self):
        svg = render_svg(_make_devcard())
        ET.fromstring(svg)

    def test_contains_username(self):
        svg = render_svg(_populated_devcard())
        assert "testuser" in svg
        assert "Test User" in svg
