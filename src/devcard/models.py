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


class Enriched(BaseModel):
    summary: str | None = Field(
        default=None, description="LLM-generated natural language summary"
    )
    strengths: list[str] = Field(
        default_factory=list, description="Identified strengths"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Suggested areas for growth"
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
    enriched: Enriched | None = Field(
        default=None, description="Optional LLM-enriched content (requires enrich extra)"
    )
    summary: str | None = Field(
        default=None,
        description="Auto-generated one-line developer summary for agent consumption",
    )
