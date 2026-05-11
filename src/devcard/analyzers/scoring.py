from __future__ import annotations

from devcard.models import DevCard, ProfileRepoData

# Git convention: 72 chars is the recommended max for commit subject lines
_IDEAL_COMMIT_MSG_LENGTH = 72


def compute_quality_score(devcard: DevCard) -> None:
    if devcard.quality is None:
        return

    q = devcard.quality
    q.score = round(
        q.test_adoption * 0.3
        + q.ci_adoption * 0.25
        + q.docs_adoption * 0.2
        + q.license_adoption * 0.15
        + q.linter_adoption * 0.1,
        3,
    )


def compute_human_visibility_score(devcard: DevCard, profile: ProfileRepoData) -> int:
    """Compute how visible/discoverable this developer is to humans (0-100).

    Rubric:
    - Bio present: 10 pts
    - Profile README: 15 pts (long) or 8 pts (short)
    - Repo descriptions: 15 pts (proportional)
    - Topics: 10 pts (proportional)
    - README quality (docs_adoption): 15 pts
    - License adoption: 5 pts
    - Pinned/signature repos: 5 pts
    - Activity: 10 pts
    - Social links: 5 pts
    - Consistency score: 10 pts
    """
    score = 0.0

    # Bio: 10 pts
    if devcard.identity.bio:
        score += 10

    # Profile README: 15 pts (long) or 8 pts (short)
    if profile.has_profile_readme:
        if profile.readme_length > 100:
            score += 15
        else:
            score += 8

    # Repo descriptions: 15 pts proportional
    projects = devcard.projects
    if projects:
        with_desc = sum(1 for p in projects if p.description)
        score += (with_desc / len(projects)) * 15

    # Topics: 10 pts proportional
    if projects:
        with_topics = sum(1 for p in projects if p.topics)
        score += (with_topics / len(projects)) * 10

    # README quality (docs_adoption): 15 pts
    if devcard.quality is not None:
        score += devcard.quality.docs_adoption * 15

    # License adoption: 5 pts
    if devcard.quality is not None:
        score += devcard.quality.license_adoption * 5

    # Pinned/signature repos: 5 pts
    if any(p.is_signature for p in projects):
        score += 5

    # Activity: 10 pts
    if devcard.activity is not None:
        activity_pts = {
            "active": 10,
            "moderate": 6,
            "sporadic": 3,
            "dormant": 0,
        }
        score += activity_pts.get(devcard.activity.status, 0)

    # Social links (blog, twitter_username): 5 pts, min(count*3, 5)
    link_count = 0
    if devcard.identity.blog:
        link_count += 1
    if devcard.identity.twitter_username:
        link_count += 1
    score += min(link_count * 3, 5)

    # Consistency score: 10 pts
    if devcard.activity is not None and devcard.activity.consistency_score is not None:
        score += (devcard.activity.consistency_score / 100) * 10

    return int(min(max(score, 0), 100))


def compute_agent_readiness_score(devcard: DevCard, profile: ProfileRepoData) -> int:
    """Compute how machine-readable/agent-friendly this developer profile is (0-100).

    Rewards things developers already do that make profiles parseable by agents.
    Bonus points for agent-specific files, but not required for a high score.

    Rubric:
    - Documentation adoption (docs signal in repos): 15 pts
    - Dependency files/stack depth: 15 pts (graduated)
    - Topics/metadata coverage: 12 pts (proportional)
    - Repo descriptions: 10 pts (proportional)
    - CI adoption: 8 pts
    - Test adoption: 8 pts
    - Commit quality: 8 pts (conventional commits = machine-parseable intent)
    - Classification coverage: 8 pts (proportional)
    - License adoption: 6 pts
    - devcard.json bonus: 5 pts
    - llms.txt bonus: 5 pts
    """
    score = 0.0

    # Documentation adoption (fraction of repos with docs signal): 15 pts
    if devcard.quality is not None:
        score += devcard.quality.docs_adoption * 15

    # Dependency files/stack depth: 15 pts graduated
    if devcard.stack is not None:
        total_items = (
            len(devcard.stack.frameworks)
            + len(devcard.stack.libraries)
            + len(devcard.stack.databases)
            + len(devcard.stack.tools)
            + len(devcard.stack.platforms)
            + len(devcard.stack.ci_cd)
            + len(devcard.stack.testing)
            + len(devcard.stack.other)
        )
        if total_items >= 10:
            score += 15
        elif total_items >= 5:
            score += 10
        elif total_items >= 1:
            score += 5

    # Topics/metadata coverage: 12 pts proportional
    projects = devcard.projects
    if projects:
        with_topics = sum(1 for p in projects if p.topics)
        score += (with_topics / len(projects)) * 12

    # Repo descriptions: 10 pts proportional
    if projects:
        with_desc = sum(1 for p in projects if p.description)
        score += (with_desc / len(projects)) * 10

    # CI adoption: 8 pts
    if devcard.quality is not None:
        score += devcard.quality.ci_adoption * 8

    # Test adoption: 8 pts
    if devcard.quality is not None:
        score += devcard.quality.test_adoption * 8

    # Commit quality: 8 pts (conventional commits are machine-parseable)
    if devcard.commit_quality is not None and devcard.commit_quality.commits_analyzed > 0:
        conv_score = min(devcard.commit_quality.conventional_commits_pct / 100, 1.0)
        msg_score = min(devcard.commit_quality.avg_message_length / _IDEAL_COMMIT_MSG_LENGTH, 1.0)
        score += (conv_score * 0.6 + msg_score * 0.4) * 8

    # Classification coverage: 8 pts proportional
    if projects:
        with_classification = sum(1 for p in projects if p.classification)
        score += (with_classification / len(projects)) * 8

    # License adoption: 6 pts
    if devcard.quality is not None:
        score += devcard.quality.license_adoption * 6

    # Bonus: devcard.json: 5 pts
    if profile.has_devcard_json:
        score += 5

    # Bonus: llms.txt: 5 pts
    if profile.has_llms_txt:
        score += 5

    return int(min(max(score, 0), 100))
