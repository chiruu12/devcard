from __future__ import annotations

from dataclasses import dataclass

from devcard.models import DevCard


@dataclass(frozen=True)
class AdvisorContext:
    # Profile
    bio_empty: bool
    followers: int
    public_repos: int
    has_blog: bool
    has_twitter: bool
    hireable: bool
    # Activity
    activity_status: str
    consistency_score: int
    commits_last_year: int
    # Quality
    quality_score: float
    ci_adoption: float
    test_adoption: float
    docs_adoption: float
    linter_adoption: float
    # Commit quality
    avg_message_length: float
    conventional_commits_pct: float
    multiline_pct: float
    # README depth
    readme_avg_word_count: float
    has_code_blocks_pct: float
    has_install_section_pct: float
    has_images_pct: float
    # Collaboration
    reviews_given: int
    notable_count: int
    orgs_count: int
    external_contributions: int
    # Lines
    total_lines_added: int
    total_lines_deleted: int
    # Coding habits
    indentation: str
    avg_line_length: float
    # Activity gaps
    longest_gap_days: int
    active_days: int
    # Scores
    human_score: int
    agent_score: int


def build_context(devcard: DevCard, human_score: int, agent_score: int) -> AdvisorContext:
    """Extract flat context from DevCard with safe defaults for missing data."""
    ident = devcard.identity
    act = devcard.activity
    qual = devcard.quality
    cq = devcard.commit_quality
    rd = devcard.readme_depth
    collab = devcard.collaboration
    lc = devcard.lines_changed
    habits = devcard.coding_habits

    return AdvisorContext(
        bio_empty=not ident.bio,
        followers=ident.followers,
        public_repos=ident.public_repos,
        has_blog=bool(ident.blog),
        has_twitter=bool(ident.twitter_username),
        hireable=bool(ident.hireable),
        activity_status=act.status if act else "dormant",
        consistency_score=act.consistency_score if act and act.consistency_score is not None else 0,
        commits_last_year=act.commits_last_year if act and act.commits_last_year else 0,
        quality_score=qual.score if qual else 0.0,
        ci_adoption=qual.ci_adoption if qual else 0.0,
        test_adoption=qual.test_adoption if qual else 0.0,
        docs_adoption=qual.docs_adoption if qual else 0.0,
        linter_adoption=qual.linter_adoption if qual else 0.0,
        avg_message_length=cq.avg_message_length if cq else 0.0,
        conventional_commits_pct=cq.conventional_commits_pct if cq else 0.0,
        multiline_pct=cq.multiline_pct if cq else 0.0,
        readme_avg_word_count=rd.avg_word_count if rd else 0.0,
        has_code_blocks_pct=rd.has_code_blocks_pct if rd else 0.0,
        has_install_section_pct=rd.has_install_section_pct if rd else 0.0,
        has_images_pct=rd.has_images_pct if rd else 0.0,
        reviews_given=(
            collab.review_activity.reviews_given
            if collab and collab.review_activity
            else 0
        ),
        notable_count=len(collab.notable_contributions) if collab else 0,
        orgs_count=len(collab.organizations) if collab else 0,
        external_contributions=collab.external_contributions if collab else 0,
        total_lines_added=lc.total_added if lc else 0,
        total_lines_deleted=lc.total_deleted if lc else 0,
        indentation=habits.indentation if habits and habits.indentation else "unknown",
        avg_line_length=habits.avg_line_length if habits and habits.avg_line_length else 0.0,
        longest_gap_days=act.longest_gap_days if act and act.longest_gap_days is not None else 0,
        active_days=act.active_days if act and act.active_days is not None else 0,
        human_score=human_score,
        agent_score=agent_score,
    )
