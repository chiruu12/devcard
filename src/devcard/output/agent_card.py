from __future__ import annotations

from devcard.models import DevCard
from devcard.output.curated import curate_for_agent


def to_agent_card(devcard: DevCard) -> str:
    curated = curate_for_agent(devcard)
    sections: list[str | None] = []
    sections.append(_render_header(curated))
    sections.append(_render_identity(curated))
    sections.append(_render_languages(curated))
    sections.append(_render_stack(curated))
    sections.append(_render_projects(curated))
    sections.append(_render_expertise(curated))
    sections.append(_render_collaboration(curated))
    sections.append(_render_activity(curated))
    sections.append(_render_quality(curated))
    sections.append("=== END ===")
    return "\n\n".join(s for s in sections if s)


def _render_header(curated: dict) -> str:
    username = curated["identity"]["username"]
    return f"=== DEVCARD: {username} ==="


def _render_identity(curated: dict) -> str:
    ident = curated["identity"]
    lines: list[str] = []

    # Identity line: Name | Profile Type | Location | Hireable: Yes/No
    parts: list[str] = []
    if ident.get("name"):
        parts.append(ident["name"])
    expertise = curated.get("expertise", {})
    if expertise.get("profile_type"):
        parts.append(expertise["profile_type"].replace("_", " ").title() + " Developer")
    if ident.get("location"):
        parts.append(ident["location"])
    if ident.get("hireable") is not None:
        parts.append(f"Hireable: {'Yes' if ident['hireable'] else 'No'}")
    if parts:
        lines.append(" | ".join(parts))

    # Summary on its own line
    summary = curated.get("summary")
    if summary:
        lines.append(summary)

    return "\n".join(lines) if lines else ""


def _render_languages(curated: dict) -> str | None:
    lang_data = curated.get("languages")
    if not lang_data:
        return None
    items = [f"{lang['name']} {lang['percentage']}%" for lang in lang_data["items"]]
    coding_ratio = lang_data.get("coding_ratio", 0)
    return f"--- LANGUAGES ---\n{' | '.join(items)}\nLogic code: {coding_ratio:.0f}%"


def _render_stack(curated: dict) -> str | None:
    stack = curated.get("stack")
    if not stack:
        return None
    lines = ["--- STACK ---"]
    for category, items in stack.items():
        label = category.replace("_", " ").title()
        lines.append(f"{label}: {', '.join(items)}")
    return "\n".join(lines)


def _render_projects(curated: dict) -> str | None:
    projects = curated.get("projects")
    if not projects:
        return None
    lines = ["--- TOP PROJECTS ---"]
    for proj in projects:
        parts = [proj["name"]]
        if proj.get("description"):
            parts.append(proj["description"])
        parts.append(f"{proj.get('stars', 0)} stars")
        if proj.get("language"):
            parts.append(proj["language"])
        if proj.get("status"):
            parts.append(proj["status"])
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _render_expertise(curated: dict) -> str | None:
    expertise = curated.get("expertise")
    if not expertise:
        return None
    lines = ["--- EXPERTISE ---"]
    if expertise.get("profile_type"):
        lines.append(f"Type: {expertise['profile_type']}")
    if expertise.get("domains"):
        domain_parts = [
            f"{d['name']} ({d['confidence']:.2f})" for d in expertise["domains"]
        ]
        lines.append(f"Domains: {', '.join(domain_parts)}")
    if expertise.get("focus_areas"):
        lines.append(f"Focus: {', '.join(expertise['focus_areas'])}")
    return "\n".join(lines)


def _render_collaboration(curated: dict) -> str | None:
    collab = curated.get("collaboration")
    if not collab:
        return None
    lines = ["--- COLLABORATION ---"]
    if collab.get("organizations"):
        lines.append(f"Orgs: {', '.join(collab['organizations'])}")
    if collab.get("contribution_style"):
        lines.append(f"Style: {collab['contribution_style']}")
    if collab.get("org_contributions"):
        contrib_parts = []
        for oc in collab["org_contributions"]:
            details = []
            if oc.get("prs_merged"):
                details.append(f"{oc['prs_merged']} PRs merged")
            if oc.get("issues_opened"):
                details.append(f"{oc['issues_opened']} issues")
            if oc.get("commits"):
                details.append(f"{oc['commits']} commits")
            contrib_parts.append(f"{oc['org']} ({', '.join(details)})")
        lines.append(f"Contributions: {', '.join(contrib_parts)}")
    return "\n".join(lines)


def _render_activity(curated: dict) -> str | None:
    act = curated.get("activity")
    if not act:
        return None
    lines = ["--- ACTIVITY ---"]

    # Status line
    status_parts = [f"Status: {act['status']}"]
    if act.get("commits_per_week") is not None:
        status_parts.append(f"{act['commits_per_week']} commits/week")
    if act.get("consistency"):
        status_parts.append(f"Consistency: {act['consistency']}")
    lines.append(" | ".join(status_parts))
    if act.get("consistency_detail"):
        lines.append(act["consistency_detail"])

    # Peak hours and timezone line
    detail_parts: list[str] = []
    if act.get("peak_hours"):
        hours_str = ", ".join(f"{h}:00" for h in act["peak_hours"])
        detail_parts.append(f"Peak hours: {hours_str} UTC")
    if act.get("timezone"):
        detail_parts.append(f"Timezone: {act['timezone']}")
    if detail_parts:
        lines.append(" | ".join(detail_parts))

    if act.get("active_days_per_week") is not None:
        lines.append(f"Active {act['active_days_per_week']} days/week")

    return "\n".join(lines)


def _render_quality(curated: dict) -> str | None:
    qual = curated.get("quality")
    if not qual:
        return None
    parts = [
        f"Score: {qual['score']:.2f}",
        f"Tests: {int(qual['test_adoption'] * 100)}%",
        f"CI: {int(qual['ci_adoption'] * 100)}%",
        f"Docs: {int(qual['docs_adoption'] * 100)}%",
        f"License: {int(qual['license_adoption'] * 100)}%",
        f"Linter: {int(qual['linter_adoption'] * 100)}%",
    ]
    return f"--- QUALITY ---\n{' | '.join(parts)}"
