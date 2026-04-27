from __future__ import annotations

from devcard.models import DevCard, Issue, ProfileRepoData

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def detect_issues(devcard: DevCard, profile: ProfileRepoData) -> list[Issue]:
    """Detect profile and repository issues that the developer can fix.

    Returns issues sorted by severity (high first, then medium, then low).
    """
    issues: list[Issue] = []

    # --- high severity ---

    if not devcard.identity.bio:
        issues.append(
            Issue(
                severity="high",
                type="missing_bio",
                message="No bio on your GitHub profile. "
                "A short bio helps others understand who you are.",
            )
        )

    if not profile.has_profile_readme:
        issues.append(
            Issue(
                severity="high",
                type="missing_profile_readme",
                message="No profile README (username/username repo). "
                "This is the first thing visitors see.",
            )
        )

    # --- medium severity ---

    repos_without_desc = [
        p.name for p in devcard.projects if not p.description
    ]
    if repos_without_desc:
        issues.append(
            Issue(
                severity="medium",
                type="missing_descriptions",
                message=f"{len(repos_without_desc)} repo(s) have no description.",
                repos=repos_without_desc,
            )
        )

    repos_without_topics = [
        p.name for p in devcard.projects if not p.topics
    ]
    if repos_without_topics:
        issues.append(
            Issue(
                severity="medium",
                type="missing_topics",
                message=f"{len(repos_without_topics)} repo(s) have no topics/tags.",
                repos=repos_without_topics,
            )
        )

    if devcard.quality is not None and devcard.quality.license_adoption < 0.5:
        issues.append(
            Issue(
                severity="medium",
                type="missing_licenses",
                message=f"Only {devcard.quality.license_adoption:.0%} of repos have a license.",
            )
        )

    if devcard.quality is not None and devcard.quality.docs_adoption < 0.5:
        issues.append(
            Issue(
                severity="medium",
                type="stale_readmes",
                message=f"Only {devcard.quality.docs_adoption:.0%} of repos have documentation.",
            )
        )

    # --- low severity ---

    if not profile.has_devcard_json:
        issues.append(
            Issue(
                severity="low",
                type="no_devcard_json",
                message="No devcard.json in your profile repo. "
                "Add one for machine-readable identity.",
            )
        )

    if not profile.has_llms_txt:
        issues.append(
            Issue(
                severity="low",
                type="no_llms_txt",
                message="No llms.txt in your profile repo. Add one for LLM-friendly context.",
            )
        )

    issues.sort(key=lambda i: _SEVERITY_ORDER[i.severity])
    return issues
