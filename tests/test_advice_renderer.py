from __future__ import annotations

from typer.testing import CliRunner

from devcard.cli import app
from devcard.models import ProfileAdvice, Verdict
from devcard.renderers.advice import render_advice_markdown, render_advice_terminal


def _make_advice(**overrides) -> ProfileAdvice:
    defaults = dict(
        username="testuser",
        human_score=72,
        agent_score=45,
        verdicts=[
            Verdict(
                category="profile",
                type="praise",
                message="Has a detailed bio",
                severity="info",
            ),
            Verdict(
                category="profile",
                type="critique",
                message="Missing profile README",
                action="Create a README.md in your profile repo",
                severity="high",
            ),
            Verdict(
                category="repos",
                type="suggestion",
                message="Add topics to your popular repos",
                action="Use gh repo edit --add-topic to tag repos",
                severity="medium",
            ),
            Verdict(
                category="repos",
                type="praise",
                message="Good repo descriptions overall",
                severity="info",
            ),
            Verdict(
                category="documentation",
                type="critique",
                message="Most repos lack a README",
                action="Add READMEs to your top 5 repos",
                severity="high",
            ),
        ],
        summary=None,
    )
    defaults.update(overrides)
    return ProfileAdvice(**defaults)


class TestTerminalRenderer:
    def test_terminal_contains_username(self):
        output = render_advice_terminal(_make_advice())
        assert "testuser" in output

    def test_terminal_contains_scores(self):
        output = render_advice_terminal(_make_advice())
        assert "72" in output
        assert "45" in output

    def test_terminal_color_codes_verdicts(self):
        output = render_advice_terminal(_make_advice())
        # Check that verdict icons are present in the output
        assert "✔" in output  # checkmark (praise)
        assert "✘" in output  # X (critique)
        assert "→" in output  # arrow (suggestion)

    def test_terminal_shows_actions(self):
        output = render_advice_terminal(_make_advice())
        assert "Create a README.md in your profile repo" in output

    def test_terminal_shows_summary_when_present(self):
        advice = _make_advice(summary="This developer has a solid profile but could improve docs.")
        output = render_advice_terminal(advice)
        assert "solid profile" in output

    def test_terminal_no_summary_panel_when_absent(self):
        advice = _make_advice(summary=None)
        output = render_advice_terminal(advice)
        assert "Summary" not in output


class TestMarkdownRenderer:
    def test_markdown_starts_with_header(self):
        output = render_advice_markdown(_make_advice())
        assert output.startswith("# Profile Advice:")

    def test_markdown_contains_scores(self):
        output = render_advice_markdown(_make_advice())
        assert "72/100" in output
        assert "45/100" in output

    def test_markdown_contains_verdicts(self):
        output = render_advice_markdown(_make_advice())
        assert "Has a detailed bio" in output
        assert "Missing profile README" in output
        assert "Add topics to your popular repos" in output

    def test_markdown_shows_summary(self):
        advice = _make_advice(summary="Great developer, needs more documentation.")
        output = render_advice_markdown(advice)
        assert "Great developer, needs more documentation." in output

    def test_markdown_no_summary_when_absent(self):
        advice = _make_advice(summary=None)
        output = render_advice_markdown(advice)
        assert "## Summary" not in output

    def test_markdown_contains_category_headings(self):
        output = render_advice_markdown(_make_advice())
        assert "## Profile" in output
        assert "## Repos" in output
        assert "## Documentation" in output

    def test_markdown_contains_actions(self):
        output = render_advice_markdown(_make_advice())
        assert "Create a README.md in your profile repo" in output
        assert "Use gh repo edit" in output


class TestAdviseCLI:
    def test_advise_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["advise", "--help"])
        assert result.exit_code == 0
        assert "advise" in result.stdout.lower() or "advice" in result.stdout.lower()
