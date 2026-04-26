from __future__ import annotations

from typing import Any

from devcard.extractors.languages import compute_coding_ratio
from devcard.models import DevCard


def curate_for_agent(devcard: DevCard) -> dict[str, Any]:
    curated: dict[str, Any] = {}

    curated["summary"] = devcard.summary

    curated["identity"] = _curate_identity(devcard)

    if devcard.languages:
        curated["languages"] = _curate_languages(devcard)

    if devcard.stack:
        curated["stack"] = _curate_stack(devcard)

    if devcard.projects:
        curated["projects"] = _curate_projects(devcard)

    if devcard.expertise:
        curated["expertise"] = _curate_expertise(devcard)

    if devcard.collaboration:
        curated["collaboration"] = _curate_collaboration(devcard)

    if devcard.activity:
        curated["activity"] = _curate_activity(devcard)

    if devcard.quality:
        curated["quality"] = _curate_quality(devcard)

    return curated


def _curate_identity(devcard: DevCard) -> dict[str, Any]:
    ident = devcard.identity
    result: dict[str, Any] = {"username": ident.username}
    if ident.name:
        result["name"] = ident.name
    if ident.bio:
        result["bio"] = ident.bio
    if ident.location:
        result["location"] = ident.location
    if ident.hireable is not None:
        result["hireable"] = ident.hireable
    if ident.public_repos:
        result["public_repos"] = ident.public_repos
    if ident.followers:
        result["followers"] = ident.followers
    return result


def _curate_languages(devcard: DevCard) -> dict[str, Any]:
    langs = [
        {
            "name": lang.name,
            "percentage": round(lang.percentage, 1),
            "category": lang.category or "other",
        }
        for lang in devcard.languages[:8]
    ]
    return {
        "items": langs,
        "coding_ratio": compute_coding_ratio(devcard.languages),
    }


def _curate_stack(devcard: DevCard) -> dict[str, list[str]]:
    stack = devcard.stack
    if not stack:
        return {}
    result: dict[str, list[str]] = {}
    for category in [
        "frameworks", "libraries", "databases", "tools", "platforms", "ci_cd", "testing",
    ]:
        items = getattr(stack, category, [])
        if items:
            result[category] = [item.name for item in items]
    return result


def _curate_projects(devcard: DevCard) -> list[dict[str, Any]]:
    projects = []
    for proj in devcard.projects[:8]:
        entry: dict[str, Any] = {"name": proj.name}
        if proj.description:
            entry["description"] = proj.description
        entry["stars"] = proj.stars
        if proj.language:
            entry["language"] = proj.language
        if proj.status:
            entry["status"] = proj.status
        projects.append(entry)
    return projects


def _curate_expertise(devcard: DevCard) -> dict[str, Any]:
    expertise = devcard.expertise
    if not expertise:
        return {}
    result: dict[str, Any] = {}
    if expertise.profile_type:
        result["profile_type"] = expertise.profile_type
    if expertise.domains:
        result["domains"] = [
            {
                "name": d.name,
                "confidence": round(d.confidence, 2),
                **({"skill_level": d.skill_level} if d.skill_level else {}),
            }
            for d in expertise.domains
        ]
    if expertise.focus_areas:
        result["focus_areas"] = [fa.name for fa in expertise.focus_areas]
    return result


def _curate_collaboration(devcard: DevCard) -> dict[str, Any]:
    collab = devcard.collaboration
    if not collab:
        return {}
    result: dict[str, Any] = {}
    if collab.organizations:
        result["organizations"] = collab.organizations
    if collab.contribution_style:
        result["contribution_style"] = collab.contribution_style
    if collab.org_contributions:
        result["org_contributions"] = [
            {
                "org": oc.org,
                "prs_merged": oc.prs_merged,
                "issues_opened": oc.issues_opened,
                "commits": oc.commits,
            }
            for oc in collab.org_contributions
        ]
    return result


def _curate_activity(devcard: DevCard) -> dict[str, Any]:
    activity = devcard.activity
    if not activity:
        return {}

    result: dict[str, Any] = {"status": activity.status}

    if activity.commits_last_year is not None:
        result["commits_per_week"] = round(activity.commits_last_year / 52, 1)

    if activity.consistency_score is not None:
        result["consistency_score"] = activity.consistency_score
        result["consistency"] = _label_from_score(activity.consistency_score)
    else:
        result["consistency"] = _label_from_status(activity.status)
    if activity.consistency_description:
        result["consistency_detail"] = activity.consistency_description

    if activity.heatmap:
        active_days = sum(1 for row in activity.heatmap if any(v > 0 for v in row))
        result["active_days_per_week"] = active_days

    if activity.peak_hours:
        result["peak_hours"] = activity.peak_hours

    if activity.timezone_estimate:
        result["timezone"] = activity.timezone_estimate

    return result


def _label_from_score(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "moderate"
    return "low"


def _label_from_status(status: str) -> str:
    return {"active": "high", "moderate": "moderate"}.get(status, "low")


def _curate_quality(devcard: DevCard) -> dict[str, Any]:
    quality = devcard.quality
    if not quality:
        return {}
    return {
        "score": round(quality.score, 2),
        "ci_adoption": round(quality.ci_adoption, 2),
        "test_adoption": round(quality.test_adoption, 2),
        "docs_adoption": round(quality.docs_adoption, 2),
        "license_adoption": round(quality.license_adoption, 2),
        "linter_adoption": round(quality.linter_adoption, 2),
    }
