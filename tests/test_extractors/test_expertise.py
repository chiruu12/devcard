from __future__ import annotations

import pytest

from devcard.extractors.expertise import (
    _compute_skill_level,
    extract_expertise,
)
from devcard.github.models import GitHubContent, GitHubRepo, GitHubUser
from devcard.models import Stack, StackItem


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


@pytest.fixture
def ml_repos():
    return [
        GitHubRepo(
            name="ml-project",
            full_name="testdev/ml-project",
            html_url="https://github.com/testdev/ml-project",
            topics=["machine-learning", "deep-learning"],
        ),
    ]


async def test_topics_generate_domains(user, ml_repos):
    result = await extract_expertise(None, user, ml_repos)
    assert result is not None
    domain_names = [d.name for d in result.domains]
    assert "Machine Learning" in domain_names


async def test_stack_boosts_confidence(user, ml_repos):
    stack = Stack(
        frameworks=[StackItem(name="TensorFlow", category="framework")],
    )
    result = await extract_expertise(None, user, ml_repos, stack=stack)
    ml_domain = next(d for d in result.domains if d.name == "Machine Learning")
    assert ml_domain.confidence > 0.7


async def test_starred_repos_add_signal(user):
    repos = [
        GitHubRepo(name="my-repo", full_name="testdev/my-repo",
                    html_url="", topics=[]),
    ]
    starred = [
        GitHubRepo(name="cool-ml", full_name="other/cool-ml",
                    html_url="", topics=["machine-learning"]),
        GitHubRepo(name="another-ml", full_name="other/another-ml",
                    html_url="", topics=["deep-learning"]),
    ]
    result = await extract_expertise(None, user, repos, starred_repos=starred)
    assert result is not None
    domain_names = [d.name for d in result.domains]
    assert "Machine Learning" in domain_names


async def test_file_patterns_add_signal(user):
    repos = [
        GitHubRepo(name="my-project", full_name="testdev/my-project",
                    html_url="", topics=[]),
    ]
    root_listings = {
        "my-project": [
            GitHubContent(name="train.py", path="train.py", type="file",
                          sha="abc", url=""),
            GitHubContent(name="model.py", path="model.py", type="file",
                          sha="def", url=""),
        ],
    }
    result = await extract_expertise(
        None, user, repos, root_listings=root_listings,
    )
    assert result is not None
    domain_names = [d.name for d in result.domains]
    assert "Machine Learning" in domain_names


async def test_skill_levels_assigned(user, ml_repos):
    stack = Stack(
        frameworks=[
            StackItem(name="TensorFlow", category="framework"),
            StackItem(name="PyTorch", category="framework"),
            StackItem(name="scikit-learn", category="library"),
        ],
    )
    result = await extract_expertise(None, user, ml_repos, stack=stack)
    ml_domain = next(d for d in result.domains if d.name == "Machine Learning")
    assert ml_domain.skill_level in ("intermediate", "advanced", "expert")


def test_compute_skill_level_beginner():
    signals = [(0.3, "language:Python")]
    assert _compute_skill_level("Machine Learning", None, signals) == "beginner"


def test_compute_skill_level_expert():
    stack = Stack(
        frameworks=[
            StackItem(name="TensorFlow", category="framework"),
            StackItem(name="PyTorch", category="framework"),
            StackItem(name="Keras", category="framework"),
            StackItem(name="scikit-learn", category="library"),
            StackItem(name="Transformers", category="library"),
            StackItem(name="XGBoost", category="library"),
        ],
    )
    signals = [
        (0.7, "topic:machine-learning in ml-proj"),
        (0.6, "stack:TensorFlow"),
        (0.6, "stack:PyTorch"),
        (0.5, "file:train.py in ml-proj"),
    ]
    assert _compute_skill_level("Machine Learning", stack, signals) == "expert"


async def test_empty_repos_returns_none(user):
    result = await extract_expertise(None, user, [])
    assert result is None
