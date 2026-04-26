from __future__ import annotations

from devcard.extractors.languages import compute_coding_ratio
from devcard.models import DevCard


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(devcard: DevCard) -> str:
    """Render a full-content DevCard as GitHub Flavored Markdown."""
    sections: list[str] = []
    sections.append(_render_header(devcard))
    if devcard.summary:
        sections.append(f"> {devcard.summary}")
    if devcard.languages:
        sections.append(_render_languages(devcard))
    if devcard.stack:
        sections.append(_render_stack(devcard))
    if devcard.projects:
        sections.append(_render_projects(devcard))
    if devcard.activity:
        sections.append(_render_activity(devcard))
    if devcard.quality:
        sections.append(_render_quality(devcard))
    if devcard.expertise:
        sections.append(_render_expertise(devcard))
    if devcard.collaboration:
        sections.append(_render_collaboration(devcard))
    sections.append(_render_footer(devcard))
    return "\n\n".join(s for s in sections if s)


def _render_header(devcard: DevCard) -> str:
    ident = devcard.identity
    lines = [f"# DevCard: {ident.username}"]
    if ident.name:
        lines.append(f"**{ident.name}**")
    if ident.bio:
        lines.append(ident.bio)
    meta: list[str] = []
    if ident.location:
        meta.append(ident.location)
    if ident.company:
        meta.append(ident.company)
    if ident.blog:
        meta.append(ident.blog)
    if ident.twitter_username:
        meta.append(f"@{ident.twitter_username}")
    if meta:
        lines.append(" | ".join(meta))
    stats: list[str] = []
    if ident.public_repos:
        stats.append(f"{ident.public_repos} repos")
    if ident.followers:
        stats.append(f"{ident.followers:,} followers")
    if ident.following:
        stats.append(f"{ident.following:,} following")
    if stats:
        lines.append(" | ".join(stats))
    if ident.hireable:
        lines.append("*Open to hire*")
    return "\n\n".join(lines)


def _render_languages(devcard: DevCard) -> str:
    coding_ratio = compute_coding_ratio(devcard.languages)
    lines = ["## Languages", "", f"**Logic code:** {coding_ratio:.0f}%", "",
             "| Language | Usage | Category |", "| --- | ---: | --- |"]
    for lang in devcard.languages:
        cat = lang.category or "other"
        lines.append(f"| {lang.name} | {lang.percentage:.1f}% | {cat} |")
    return "\n".join(lines)


def _render_stack(devcard: DevCard) -> str:
    stack = devcard.stack
    if stack is None:
        return ""
    categories = [
        ("Frameworks", stack.frameworks),
        ("Libraries", stack.libraries),
        ("Databases", stack.databases),
        ("Tools", stack.tools),
        ("Platforms", stack.platforms),
        ("CI/CD", stack.ci_cd),
        ("Testing", stack.testing),
        ("Other", stack.other),
    ]
    lines = ["## Stack", ""]
    any_items = False
    for label, items in categories:
        if items:
            any_items = True
            names = ", ".join(item.name for item in items)
            lines.append(f"**{label}:** {names}")
    if not any_items:
        return ""
    return "\n\n".join(lines)


def _render_projects(devcard: DevCard) -> str:
    lines = [
        "## Projects",
        "",
        "| Project | Description | Stars | Language | Status |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for proj in devcard.projects:
        name = f"**{proj.name}**" if proj.is_signature else proj.name
        desc = _md_escape(proj.description or "")
        lang = proj.language or "-"
        status = proj.status or "-"
        lines.append(f"| {name} | {desc} | {proj.stars} | {lang} | {status} |")
    sig = next((p for p in devcard.projects if p.is_signature and p.narrative), None)
    if sig:
        lines.append("")
        lines.append(f"*{sig.narrative}*")
    return "\n".join(lines)


def _render_activity(devcard: DevCard) -> str:
    act = devcard.activity
    if act is None:
        return ""
    lines = ["## Activity", ""]
    lines.append(f"**Status:** {act.status}")
    if act.commits_last_year is not None:
        lines.append(f"**Commits (last year):** ~{act.commits_last_year:,}")
    if act.current_streak is not None:
        lines.append(f"**Current streak:** {act.current_streak} days")
    if act.longest_streak is not None:
        lines.append(f"**Longest streak:** {act.longest_streak} days")
    if act.peak_hours:
        hours_str = ", ".join(f"{h}:00" for h in act.peak_hours)
        lines.append(f"**Peak hours (UTC):** {hours_str}")
    if act.timezone_estimate:
        lines.append(f"**Timezone estimate:** {act.timezone_estimate}")
    return "\n\n".join(lines)


def _render_quality(devcard: DevCard) -> str:
    q = devcard.quality
    if q is None:
        return ""
    lines = [
        "## Quality",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Score | {q.score:.0%} |",
        f"| Tests | {q.test_adoption:.0%} |",
        f"| CI/CD | {q.ci_adoption:.0%} |",
        f"| Docs | {q.docs_adoption:.0%} |",
        f"| License | {q.license_adoption:.0%} |",
        f"| Linter | {q.linter_adoption:.0%} |",
    ]
    if q.recommendations:
        lines.append("")
        lines.append("**Recommendations:**")
        lines.append("")
        for tip in q.recommendations[:5]:
            lines.append(f"- {tip}")
    return "\n".join(lines)


def _render_expertise(devcard: DevCard) -> str:
    exp = devcard.expertise
    if exp is None:
        return ""
    lines = ["## Expertise", ""]
    if exp.profile_type:
        lines.append(f"**Profile type:** {exp.profile_type.replace('_', ' ').title()}")
    if exp.domains:
        lines.append("")
        lines.append("**Domains:**")
        lines.append("")
        for domain in exp.domains:
            level = f" — {domain.skill_level}" if domain.skill_level else ""
            lines.append(f"- {domain.name} ({domain.confidence:.0%}{level})")
    if exp.focus_areas:
        lines.append("")
        lines.append("**Focus areas:**")
        lines.append("")
        for area in exp.focus_areas:
            lines.append(f"- {area.name}")
    return "\n".join(lines)


def _render_collaboration(devcard: DevCard) -> str:
    collab = devcard.collaboration
    if collab is None:
        return ""
    lines = ["## Collaboration", ""]
    if collab.organizations:
        lines.append(f"**Organizations:** {', '.join(collab.organizations)}")
    if collab.contribution_style:
        lines.append(
            f"**Style:** {collab.contribution_style.replace('_', ' ').title()}"
        )
    if collab.pull_requests_opened:
        lines.append(f"**PRs opened:** {collab.pull_requests_opened}")
    if collab.issues_opened:
        lines.append(f"**Issues opened:** {collab.issues_opened}")
    if collab.external_contributions:
        lines.append(f"**External contributions:** {collab.external_contributions}")
    if collab.org_contributions:
        lines.append("")
        lines.append("**Org contributions:**")
        lines.append("")
        for oc in collab.org_contributions:
            parts = [f"{oc.org}:"]
            if oc.prs_opened:
                parts.append(f"{oc.prs_opened} PRs opened")
            if oc.prs_merged:
                parts.append(f"{oc.prs_merged} PRs merged")
            if oc.issues_opened:
                parts.append(f"{oc.issues_opened} issues")
            if oc.commits:
                parts.append(f"{oc.commits} commits")
            lines.append(f"- {parts[0]} {', '.join(parts[1:])}")
    return "\n\n".join(lines)


def _render_footer(devcard: DevCard) -> str:
    date_str = devcard.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    return f"---\n\nGenerated by devcard v{devcard.generator.version} on {date_str}"
