"""Renderers for ProfileAdvice: terminal (Rich) and GitHub Flavored Markdown."""
from __future__ import annotations

from io import StringIO
from itertools import groupby

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from devcard.models import ProfileAdvice, Verdict


def _score_color(score: int) -> str:
    """Return a Rich color name based on score value."""
    if score >= 70:
        return "green"
    if score >= 40:
        return "yellow"
    return "red"


def _verdict_icon(verdict_type: str) -> tuple[str, str]:
    """Return (icon, color) for a verdict type."""
    if verdict_type == "praise":
        return "✔", "green"
    if verdict_type == "critique":
        return "✘", "red"
    # suggestion
    return "→", "yellow"


def render_advice_terminal(advice: ProfileAdvice) -> str:
    """Render ProfileAdvice as a Rich terminal string."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)

    # Scores panel
    h_color = _score_color(advice.human_score)
    a_color = _score_color(advice.agent_score)
    scores_text = Text()
    scores_text.append("Human Visibility: ")
    scores_text.append(f"{advice.human_score}/100", style=f"bold {h_color}")
    scores_text.append("  |  ")
    scores_text.append("Agent Readiness: ")
    scores_text.append(f"{advice.agent_score}/100", style=f"bold {a_color}")
    console.print(Panel(
        scores_text,
        title=f"Profile Advice: {advice.username}",
        border_style="blue",
    ))

    # Verdicts grouped by category
    sorted_verdicts = sorted(advice.verdicts, key=lambda v: v.category)
    for category, group in groupby(sorted_verdicts, key=lambda v: v.category):
        verdicts_list: list[Verdict] = list(group)
        lines: list[Text] = []
        for v in verdicts_list:
            icon, color = _verdict_icon(v.type)
            line = Text()
            line.append(f"{icon} ", style=color)
            line.append(v.message)
            lines.append(line)
            if v.action:
                action_line = Text()
                action_line.append(f"  {v.action}", style="dim")
                lines.append(action_line)

        panel_content = Text("\n")
        for i, line in enumerate(lines):
            panel_content.append_text(line)
            if i < len(lines) - 1:
                panel_content.append("\n")

        console.print(Panel(
            panel_content,
            title=category.replace("_", " ").title(),
            border_style="cyan",
        ))

    # Summary (if present)
    if advice.summary:
        console.print(Panel(
            advice.summary,
            title="Summary",
            border_style="bright_magenta",
        ))

    return buf.getvalue()


def _md_escape(text: str) -> str:
    """Escape characters that break GFM tables."""
    return text.replace("|", "\\|").replace("\n", " ")


def render_advice_markdown(advice: ProfileAdvice) -> str:
    """Render ProfileAdvice as GitHub Flavored Markdown."""
    sections: list[str] = []

    # Header
    sections.append(f"# Profile Advice: {advice.username}")

    # Scores
    scores_lines = [
        "## Scores",
        "",
        "| Metric | Score |",
        "| --- | ---: |",
        f"| Human Visibility | {advice.human_score}/100 |",
        f"| Agent Readiness | {advice.agent_score}/100 |",
    ]
    sections.append("\n".join(scores_lines))

    # Verdicts grouped by category
    sorted_verdicts = sorted(advice.verdicts, key=lambda v: v.category)
    for category, group in groupby(sorted_verdicts, key=lambda v: v.category):
        verdicts_list: list[Verdict] = list(group)
        cat_title = category.replace("_", " ").title()
        lines = [
            f"## {cat_title}",
            "",
            "| Type | Message | Action |",
            "| --- | --- | --- |",
        ]
        for v in verdicts_list:
            type_label = v.type.title()
            action = _md_escape(v.action) if v.action else "-"
            lines.append(
                f"| {type_label} | {_md_escape(v.message)} | {action} |"
            )
        sections.append("\n".join(lines))

    # Summary
    if advice.summary:
        sections.append(f"## Summary\n\n{advice.summary}")

    return "\n\n".join(sections)
