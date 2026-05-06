from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ProfileType(StrEnum):
    full_stack = "full_stack"
    backend = "backend"
    frontend = "frontend"
    devops = "devops"
    data = "data"
    ml = "ml"
    mobile = "mobile"
    systems = "systems"
    security = "security"
    embedded = "embedded"
    researcher = "researcher"
    other = "other"


class Generator(BaseModel):
    name: str = Field(description="Name of the tool that generated this DevCard")
    version: str = Field(description="Version of the generator tool")
    url: str | None = Field(default=None, description="URL of the generator project")


class Identity(BaseModel):
    username: str = Field(description="GitHub username")
    name: str | None = Field(default=None, description="Display name")
    bio: str | None = Field(default=None, description="GitHub profile bio")
    avatar_url: str | None = Field(default=None, description="URL to avatar image")
    location: str | None = Field(default=None, description="Self-reported location")
    company: str | None = Field(default=None, description="Company or organization")
    blog: str | None = Field(default=None, description="Personal website or blog URL")
    twitter_username: str | None = Field(
        default=None, description="Twitter/X username without @"
    )
    hireable: bool | None = Field(default=None, description="Whether the user is open to hire")
    public_repos: int = Field(default=0, description="Number of public repositories")
    public_gists: int = Field(default=0, description="Number of public gists")
    followers: int = Field(default=0, description="Number of followers")
    following: int = Field(default=0, description="Number of users being followed")
    created_at: str | None = Field(
        default=None, description="Account creation date in ISO 8601 format"
    )


class Language(BaseModel):
    name: str = Field(description="Programming language name")
    percentage: float = Field(description="Percentage of total code in this language")
    color: str | None = Field(
        default=None, description="Hex color code from GitHub Linguist"
    )
    bytes: int | None = Field(default=None, description="Total bytes of code in this language")
    category: Literal["logic", "presentation", "markup", "data", "build", "other"] | None = Field(
        default=None,
        description="Language category: logic, presentation, markup, data, build, other",
    )


class StackItem(BaseModel):
    name: str = Field(description="Technology or package display name")
    category: str = Field(
        description="Category: framework, library, database, tool, platform, ci_cd, testing, other"
    )
    source: str | None = Field(
        default=None, description="Repository where this dependency was detected"
    )


class Stack(BaseModel):
    frameworks: list[StackItem] = Field(
        default_factory=list, description="Web and application frameworks"
    )
    libraries: list[StackItem] = Field(
        default_factory=list, description="General-purpose libraries"
    )
    databases: list[StackItem] = Field(
        default_factory=list, description="Database systems and ORMs"
    )
    tools: list[StackItem] = Field(default_factory=list, description="Developer tools and CLIs")
    platforms: list[StackItem] = Field(
        default_factory=list, description="Cloud platforms and services"
    )
    ci_cd: list[StackItem] = Field(
        default_factory=list, description="CI/CD and build tools"
    )
    testing: list[StackItem] = Field(
        default_factory=list, description="Testing frameworks and tools"
    )
    other: list[StackItem] = Field(
        default_factory=list, description="Other technologies that don't fit above categories"
    )


class Activity(BaseModel):
    status: Literal["active", "moderate", "sporadic", "dormant"] = Field(
        description="Recent activity level based on events and push timestamps"
    )
    commits_last_year: int | None = Field(
        default=None, description="Estimated commits in the last 365 days"
    )
    current_streak: int | None = Field(
        default=None, description="Current consecutive days with activity"
    )
    longest_streak: int | None = Field(
        default=None, description="Longest consecutive days with activity"
    )
    peak_hours: list[int] = Field(
        default_factory=list,
        description="Most active hours of the day (0-23 UTC) by commit frequency",
    )
    timezone_estimate: str | None = Field(
        default=None, description="Estimated timezone based on activity patterns (e.g. UTC-8)"
    )
    heatmap: list[list[int]] | None = Field(
        default=None,
        description="7x24 matrix of activity counts (rows=days Mon-Sun, cols=hours 0-23)",
    )
    consistency_score: int | None = Field(
        default=None,
        description="Activity consistency from 0 (sporadic) to 100 (perfectly even)",
    )
    consistency_description: str | None = Field(
        default=None,
        description="Human-readable consistency label (e.g. 'bursty, heavy Tuesdays & Fridays')",
    )


class Project(BaseModel):
    name: str = Field(description="Repository name")
    description: str | None = Field(default=None, description="Repository description")
    url: str | None = Field(default=None, description="Repository URL")
    stars: int = Field(default=0, description="Star count")
    forks: int = Field(default=0, description="Fork count")
    language: str | None = Field(default=None, description="Primary language")
    topics: list[str] = Field(default_factory=list, description="Repository topics/tags")
    status: Literal["active", "maintained", "inactive", "archived"] | None = Field(
        default=None, description="Activity status based on last push date"
    )
    maturity: Literal["mature", "growing", "new", "stale"] | None = Field(
        default=None, description="Project maturity based on age and adoption"
    )
    classification: str | None = Field(
        default=None,
        description="Project type: library, application, tool, framework, config, docs, learning",
    )
    is_signature: bool = Field(
        default=False,
        description="Whether this is the developer's signature (standout) project",
    )
    narrative: str | None = Field(
        default=None,
        description="One-line heuristic description of the project's significance",
    )


class ReviewActivity(BaseModel):
    reviews_given: int = Field(default=0, description="Total PR reviews given (from recent events)")
    approved: int = Field(default=0, description="Reviews with APPROVED state")
    changes_requested: int = Field(default=0, description="Reviews requesting changes")
    commented: int = Field(default=0, description="Reviews with only comments")
    repos_reviewed: list[str] = Field(
        default_factory=list, description="Unique repos where reviews were given"
    )


class NotableContribution(BaseModel):
    repo: str = Field(description="Full repo name e.g. 'facebook/react'")
    repo_stars: int = Field(description="Star count of the target repo")
    contribution_type: Literal["pull_request", "commit", "issue"] = Field(
        description="Type of contribution"
    )
    count: int = Field(description="Number of contributions to this repo")
    merged: int | None = Field(default=None, description="Number of merged PRs")
    description: str | None = Field(default=None, description="Repo description")
    url: str = Field(description="Repo URL")


class Collaboration(BaseModel):
    organizations: list[str] = Field(
        default_factory=list, description="GitHub organizations the user belongs to"
    )
    pull_requests_opened: int = Field(
        default=0, description="Number of pull requests opened (from recent events)"
    )
    issues_opened: int = Field(
        default=0, description="Number of issues opened (from recent events)"
    )
    contribution_style: str | None = Field(
        default=None,
        description="Collaboration style: maintainer, contributor, solo_builder, explorer",
    )
    external_contributions: int = Field(
        default=0, description="Contributions to repositories not owned by this user"
    )
    org_contributions: list[OrgContribution] = Field(
        default_factory=list,
        description="Detailed contribution breakdown per organization",
    )
    maintained_repos_with_contributors: int = Field(
        default=0,
        description="Repos owned by user with forks (indicating external contributors)",
    )
    notable_contributions: list[NotableContribution] = Field(
        default_factory=list,
        description="Contributions to popular repos (1000+ stars) the user doesn't own",
    )
    review_activity: ReviewActivity | None = Field(
        default=None, description="PR review activity from recent events"
    )


class OrgContribution(BaseModel):
    org: str = Field(description="GitHub organization login name")
    prs_opened: int = Field(default=0, description="Pull requests opened in this org's repos")
    prs_merged: int = Field(default=0, description="Pull requests merged in this org's repos")
    issues_opened: int = Field(
        default=0, description="Issues opened in this org's repos"
    )
    commits: int = Field(default=0, description="Commits to this org's repos (estimated)")


class QualityDetail(BaseModel):
    repo: str = Field(description="Repository name")
    signals: list[str] = Field(
        default_factory=list,
        description="Quality signals found in this repo (ci, testing, docs, license, linting)",
    )


class Quality(BaseModel):
    score: float = Field(default=0.0, description="Composite quality score from 0 to 1")
    ci_adoption: float = Field(
        default=0.0, description="Fraction of repos with CI/CD configuration (0-1)"
    )
    test_adoption: float = Field(
        default=0.0, description="Fraction of repos with test infrastructure (0-1)"
    )
    docs_adoption: float = Field(
        default=0.0, description="Fraction of repos with documentation (0-1)"
    )
    license_adoption: float = Field(
        default=0.0, description="Fraction of repos with a license file (0-1)"
    )
    linter_adoption: float = Field(
        default=0.0, description="Fraction of repos with linter configuration (0-1)"
    )
    details: list[QualityDetail] = Field(
        default_factory=list, description="Per-repo quality signal breakdown"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable improvement tips based on quality gaps",
    )


class Domain(BaseModel):
    name: str = Field(description="Expertise domain name (e.g. Machine Learning, Web Development)")
    confidence: float = Field(description="Confidence score from 0 to 1")
    skill_level: Literal["beginner", "intermediate", "advanced", "expert"] | None = Field(
        default=None,
        description="Inferred skill depth based on breadth of packages and projects",
    )


class FocusArea(BaseModel):
    name: str = Field(description="Focus area name")
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence supporting this focus area (topics, languages, stack items)",
    )


class Expertise(BaseModel):
    domains: list[Domain] = Field(
        default_factory=list, description="Inferred expertise domains with confidence scores"
    )
    profile_type: str | None = Field(
        default=None, description="Developer profile classification (from ProfileType enum)"
    )
    focus_areas: list[FocusArea] = Field(
        default_factory=list, description="Top focus areas with supporting evidence"
    )


class ProjectHighlight(BaseModel):
    name: str = Field(description="Repository name")
    reason: str = Field(description="Why this project matters")
    significance: Literal["flagship", "growing", "hidden gem"] = Field(
        description="Project significance tier"
    )


class Enriched(BaseModel):
    summary: str | None = Field(
        default=None, description="LLM-generated natural language summary"
    )
    archetype: str | None = Field(
        default=None, description="Creative developer label (e.g. ML Craftsman)"
    )
    strengths: list[str] = Field(
        default_factory=list, description="Identified strengths"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Suggested areas for growth"
    )
    project_highlights: list[ProjectHighlight] = Field(
        default_factory=list, description="LLM-ranked top projects by significance"
    )


class CodingHabits(BaseModel):
    indentation: Literal["spaces", "tabs", "mixed"] | None = Field(
        default=None, description="Detected indentation style from recent commits"
    )
    spaces_count: int = Field(default=0, description="Number of space-indented lines found")
    tabs_count: int = Field(default=0, description="Number of tab-indented lines found")
    avg_line_length: float | None = Field(
        default=None, description="Average characters per line in recent code additions"
    )
    lines_analyzed: int = Field(default=0, description="Total lines of code analyzed")


class RepoLines(BaseModel):
    repo: str = Field(description="Repository name")
    added: int = Field(default=0, description="Total lines added")
    deleted: int = Field(default=0, description="Total lines deleted")


class LinesChanged(BaseModel):
    total_added: int = Field(default=0, description="Total lines added across all repos")
    total_deleted: int = Field(default=0, description="Total lines deleted across all repos")
    by_repo: list[RepoLines] = Field(
        default_factory=list, description="Per-repo breakdown sorted by total activity"
    )


class CommitQuality(BaseModel):
    avg_message_length: float = Field(
        default=0.0, description="Average commit message length in characters"
    )
    conventional_commits_pct: float = Field(
        default=0.0, description="Percentage of commits using conventional format (feat:/fix:/etc.)"
    )
    multiline_pct: float = Field(
        default=0.0, description="Percentage of commits with multi-line messages"
    )
    commits_analyzed: int = Field(default=0, description="Total commits analyzed")


class ReadmeDepth(BaseModel):
    avg_word_count: float = Field(default=0.0, description="Average word count across repo READMEs")
    avg_heading_count: float = Field(
        default=0.0, description="Average number of headings per README"
    )
    has_code_blocks_pct: float = Field(
        default=0.0, description="Percentage of READMEs with code blocks"
    )
    has_images_pct: float = Field(
        default=0.0, description="Percentage of READMEs with images or badges"
    )
    has_install_section_pct: float = Field(
        default=0.0,
        description="Percentage of READMEs with Installation/Getting Started/Usage section",
    )
    repos_analyzed: int = Field(default=0, description="Number of repos with READMEs analyzed")


class Responsiveness(BaseModel):
    issue_comments: int = Field(
        default=0, description="Number of issue comments made (from recent events)"
    )
    avg_response_hours: float | None = Field(
        default=None, description="Average hours to first response on owned repo issues"
    )
    pr_comment_count: int = Field(
        default=0, description="Number of PR review comments made (from recent events)"
    )


class DevCard(BaseModel):
    version: str = Field(default="1.0", description="DevCard schema version")
    generated_at: datetime = Field(description="When this DevCard was generated (ISO 8601)")
    generator: Generator = Field(description="Tool that generated this DevCard")
    identity: Identity = Field(description="Core GitHub identity information")
    languages: list[Language] = Field(
        default_factory=list, description="Programming languages by usage percentage"
    )
    stack: Stack | None = Field(
        default=None, description="Detected technology stack from dependency files"
    )
    activity: Activity | None = Field(
        default=None, description="Recent activity patterns and commit behavior"
    )
    projects: list[Project] = Field(
        default_factory=list, description="Top repositories ranked by stars, forks, and recency"
    )
    collaboration: Collaboration | None = Field(
        default=None, description="Collaboration signals: orgs, PRs, issues, style"
    )
    quality: Quality | None = Field(
        default=None, description="Code quality practice signals across repositories"
    )
    expertise: Expertise | None = Field(
        default=None, description="Inferred expertise domains and developer profile type"
    )
    coding_habits: CodingHabits | None = Field(
        default=None, description="Coding style signals from recent commit patches"
    )
    lines_changed: LinesChanged | None = Field(
        default=None, description="Lines of code added/deleted across repositories"
    )
    commit_quality: CommitQuality | None = Field(
        default=None, description="Commit message quality signals"
    )
    readme_depth: ReadmeDepth | None = Field(
        default=None, description="README documentation depth across repositories"
    )
    responsiveness: Responsiveness | None = Field(
        default=None, description="Community responsiveness signals"
    )
    enriched: Enriched | None = Field(
        default=None, description="Optional LLM-enriched content (requires enrich extra)"
    )
    summary: str | None = Field(
        default=None,
        description="Auto-generated one-line developer summary for agent consumption",
    )


class ProfileRepoData(BaseModel):
    """Data from the user's profile repo (username/username)."""

    has_profile_readme: bool = Field(
        default=False, description="Whether a profile README exists"
    )
    readme_length: int = Field(
        default=0, description="Size of profile README in bytes"
    )
    has_devcard_json: bool = Field(
        default=False, description="Whether devcard.json exists in profile repo"
    )
    has_llms_txt: bool = Field(
        default=False, description="Whether llms.txt exists in profile repo"
    )
    files: list[str] = Field(
        default_factory=list, description="File names in root of profile repo"
    )


class Issue(BaseModel):
    """A detected profile/repo issue that can be fixed."""

    severity: Literal["high", "medium", "low"] = Field(
        description="Issue severity level"
    )
    type: str = Field(description="Issue type identifier (e.g. missing_bio, missing_topics)")
    message: str = Field(description="Human-readable description of the issue")
    repos: list[str] = Field(
        default_factory=list,
        description="Affected repositories, if repo-specific",
    )


class AuditResult(BaseModel):
    """Result of auditing a developer's GitHub profile."""

    username: str = Field(description="GitHub username that was audited")
    human_visibility_score: int = Field(description="Human visibility score 0-100")
    agent_readiness_score: int = Field(description="Agent readiness score 0-100")
    issues: list[Issue] = Field(default_factory=list, description="Detected issues")
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )
    summary: dict = Field(default_factory=dict, description="Summary statistics")


class RepoAnalysis(BaseModel):
    """Result of analyzing a single repository."""

    owner: str = Field(description="Repository owner")
    repo: str = Field(description="Repository name")
    language: str | None = Field(default=None, description="Primary language")
    classification: str | None = Field(
        default=None, description="Project classification"
    )
    issues: list[Issue] = Field(
        default_factory=list, description="Detected issues for this repo"
    )
    suggested_description: str | None = Field(
        default=None, description="Suggested repo description"
    )
    suggested_topics: list[str] = Field(
        default_factory=list, description="Suggested topics"
    )


class FixChange(BaseModel):
    """A single change to be applied or previewed."""

    type: str = Field(description="Change type: create_file, update_description, update_topics")
    repo: str = Field(description="Target repository (owner/repo)")
    path: str | None = Field(default=None, description="File path for create_file changes")
    content: str | None = Field(default=None, description="Content for create_file changes")
    description: str = Field(default="", description="Human-readable description of the change")


class FixResult(BaseModel):
    """Result of a fix operation."""

    username: str = Field(description="GitHub username")
    dry_run: bool = Field(description="Whether this was a preview only")
    changes: list[FixChange] = Field(
        default_factory=list, description="Changes applied or previewed"
    )
    message: str = Field(default="", description="Summary message")
