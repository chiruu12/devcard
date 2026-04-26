from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GitHubUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    location: str | None = None
    company: str | None = None
    blog: str | None = None
    twitter_username: str | None = None
    hireable: bool | None = None
    public_repos: int = 0
    public_gists: int = 0
    followers: int = 0
    following: int = 0
    created_at: str | None = None
    type: str | None = None


class GitHubRepo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    full_name: str
    description: str | None = None
    html_url: str
    homepage: str | None = None
    language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    fork: bool = False
    archived: bool = False
    disabled: bool = False
    pushed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    topics: list[str] = Field(default_factory=list)
    default_branch: str = "main"
    size: int = 0
    open_issues_count: int = 0
    license: dict | None = None


class GitHubEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    created_at: str
    repo: dict
    payload: dict = Field(default_factory=dict)
    public: bool = True
    actor: dict | None = None


class GitHubContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    path: str
    type: str
    size: int = 0
    content: str | None = None
    encoding: str | None = None
    sha: str
    url: str
