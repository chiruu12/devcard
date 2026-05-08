from __future__ import annotations

from dataclasses import dataclass

from devcard.models import DevCard


@dataclass(frozen=True)
class AdvisorContext:
    # Profile (always present from Identity)
    bio_empty: bool
    followers: int
    public_repos: int
    has_blog: bool
    has_twitter: bool
    hireable: bool
    # Activity (None when extractor fails)
    activity_status: str | None
    consistency_score: int | None
    commits_last_year: int | None
    # Quality (None when extractor fails)
    quality_score: float | None
    ci_adoption: float | None
    test_adoption: float | None
    docs_adoption: float | None
    linter_adoption: float | None
    # Commit quality (None when extractor fails)
    avg_message_length: float | None
    conventional_commits_pct: float | None
    multiline_pct: float | None
    # README depth (None when extractor fails)
    readme_avg_word_count: float | None
    has_code_blocks_pct: float | None
    has_install_section_pct: float | None
    has_images_pct: float | None
    # Collaboration (None when extractor fails)
    reviews_given: int | None
    notable_count: int | None
    orgs_count: int | None
    external_contributions: int | None
    # Lines (None when extractor fails)
    total_lines_added: int | None
    total_lines_deleted: int | None
    # Coding habits (None when extractor fails)
    indentation: str | None
    avg_line_length: float | None
    # Activity gaps (None when extractor fails)
    longest_gap_days: int | None
    active_days: int | None
    # Scores (always present, computed by scoring)
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
        activity_status=act.status if act else None,
        consistency_score=act.consistency_score if act else None,
        commits_last_year=act.commits_last_year if act else None,
        quality_score=qual.score if qual else None,
        ci_adoption=qual.ci_adoption if qual else None,
        test_adoption=qual.test_adoption if qual else None,
        docs_adoption=qual.docs_adoption if qual else None,
        linter_adoption=qual.linter_adoption if qual else None,
        avg_message_length=cq.avg_message_length if cq else None,
        conventional_commits_pct=cq.conventional_commits_pct if cq else None,
        multiline_pct=cq.multiline_pct if cq else None,
        readme_avg_word_count=rd.avg_word_count if rd else None,
        has_code_blocks_pct=rd.has_code_blocks_pct if rd else None,
        has_install_section_pct=rd.has_install_section_pct if rd else None,
        has_images_pct=rd.has_images_pct if rd else None,
        reviews_given=(
            collab.review_activity.reviews_given
            if collab and collab.review_activity
            else None
        ),
        notable_count=len(collab.notable_contributions) if collab else None,
        orgs_count=len(collab.organizations) if collab else None,
        external_contributions=collab.external_contributions if collab else None,
        total_lines_added=lc.total_added if lc else None,
        total_lines_deleted=lc.total_deleted if lc else None,
        indentation=habits.indentation if habits else None,
        avg_line_length=habits.avg_line_length if habits else None,
        longest_gap_days=act.longest_gap_days if act else None,
        active_days=act.active_days if act else None,
        human_score=human_score,
        agent_score=agent_score,
    )
