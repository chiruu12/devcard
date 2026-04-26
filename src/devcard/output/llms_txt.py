from __future__ import annotations

from typing import Any

from devcard.models import DevCard
from devcard.output.curated import curate_for_agent


def to_llms_txt(devcard: DevCard) -> str:
    """Generate llms.txt-spec-compliant markdown (https://llmstxt.org/).

    Uses the shared curation layer for structured data and accesses
    the full DevCard for URLs not present in the curated output.
    """
    curated = curate_for_agent(devcard)
    sections: list[str | None] = []
    sections.append(_title(curated))
    sections.append(_blockquote(curated))
    sections.append(_body(curated))
    sections.append(_projects(curated, devcard))
    sections.append(_skills(curated))
    sections.append(_expertise(curated))
    sections.append(_collaboration(curated))
    return "\n\n".join(s for s in sections if s)


def _title(curated: dict[str, Any]) -> str:
    username = curated["identity"]["username"]
    return f"# DevCard: {username}"


def _blockquote(curated: dict[str, Any]) -> str | None:
    summary = curated.get("summary")
    if not summary:
        return None
    return f"> {summary}"


def _body(curated: dict[str, Any]) -> str | None:
    lines: list[str] = []

    # Profile type line
    parts: list[str] = []
    expertise = curated.get("expertise", {})
    if expertise.get("profile_type"):
        parts.append(expertise["profile_type"].replace("_", " ").title() + " Developer")
    ident = curated["identity"]
    if ident.get("location"):
        parts.append(f"based in {ident['location']}")
    if parts:
        lines.append(" ".join(parts) + ".")

    # Primary languages
    lang_data = curated.get("languages")
    if lang_data:
        lang_parts = [f"{lang['name']} ({lang['percentage']}%)" for lang in lang_data["items"]]
        lines.append(f"Primary languages: {', '.join(lang_parts)}.")

    # Activity summary
    activity = curated.get("activity")
    if activity:
        act_parts: list[str] = []
        act_parts.append(f"{activity['status'].title()} contributor")
        if activity.get("consistency"):
            act_parts.append(f"with {activity['consistency']} consistency")
        if activity.get("commits_per_week") is not None:
            act_parts.append(f"~{activity['commits_per_week']} commits/week")
        lines.append(", ".join(act_parts) + ".")

    # Quality score
    quality = curated.get("quality")
    if quality:
        lines.append(f"Quality score: {quality['score']:.2f}.")

    return " ".join(lines) if lines else None


def _projects(curated: dict[str, Any], devcard: DevCard) -> str | None:
    curated_projects = curated.get("projects")
    if not curated_projects:
        return None

    # Build a lookup from the full DevCard for URLs
    url_lookup: dict[str, str] = {}
    for proj in devcard.projects:
        if proj.url:
            url_lookup[proj.name] = proj.url

    lines = ["## Projects"]
    for proj in curated_projects:
        name = proj["name"]
        desc = proj.get("description", "")
        stars = proj.get("stars", 0)
        url = url_lookup.get(name)

        suffix = f": {desc} ({stars} stars)" if desc else f" ({stars} stars)"
        if url:
            lines.append(f"- [{name}]({url}){suffix}")
        else:
            lines.append(f"- {name}{suffix}")
    return "\n".join(lines)


def _skills(curated: dict[str, Any]) -> str | None:
    languages = curated.get("languages")
    stack = curated.get("stack")
    if not languages and not stack:
        return None

    lines = ["## Skills"]
    if languages:
        lang_items = languages["items"] if isinstance(languages, dict) else languages
        for lang in lang_items:
            lines.append(f"- {lang['name']} ({lang['percentage']}%)")
    if stack:
        for _category, items in stack.items():
            lines.append(f"- {', '.join(items)}")
    return "\n".join(lines)


def _expertise(curated: dict[str, Any]) -> str | None:
    expertise = curated.get("expertise")
    if not expertise:
        return None
    domains = expertise.get("domains")
    focus_areas = expertise.get("focus_areas")
    if not domains and not focus_areas:
        return None

    lines = ["## Expertise"]
    if domains:
        for d in domains:
            lines.append(f"- {d['name']} ({d['confidence']:.2f} confidence)")
    if focus_areas:
        for fa in focus_areas:
            lines.append(f"- {fa}")
    return "\n".join(lines)


def _collaboration(curated: dict[str, Any]) -> str | None:
    collab = curated.get("collaboration")
    if not collab:
        return None
    orgs = collab.get("organizations")
    style = collab.get("contribution_style")
    if not orgs and not style:
        return None

    lines = ["## Collaboration"]
    if orgs:
        lines.append(f"- Organizations: {', '.join(orgs)}")
    if style:
        lines.append(f"- Contribution style: {style}")
    return "\n".join(lines)
