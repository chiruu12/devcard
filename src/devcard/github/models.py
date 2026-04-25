from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GitHubUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = None
    hireable: Optional[bool] = None
    public_repos: int = 0
    public_gists: int = 0
    followers: int = 0
    following: int = 0
    created_at: Optional[str] = None
    type: Optional[str] = None


class GitHubRepo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    homepage: Optional[str] = None
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    fork: bool = False
    archived: bool = False
    disabled: bool = False
    pushed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    topics: list[str] = Field(default_factory=list)
    default_branch: str = "main"
    size: int = 0
    open_issues_count: int = 0
    license: Optional[dict] = None


class GitHubEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    created_at: str
    repo: dict
    payload: dict = Field(default_factory=dict)
    public: bool = True
    actor: Optional[dict] = None


class GitHubContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    path: str
    type: str
    size: int = 0
    content: Optional[str] = None
    encoding: Optional[str] = None
    sha: str
    url: str
