from __future__ import annotations

import base64
from unittest.mock import AsyncMock

import pytest

from devcard.extractors.readme_depth import extract_readme_depth
from devcard.github.models import GitHubContent, GitHubRepo, GitHubUser


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


def _content(name: str, type: str = "file", **kwargs) -> GitHubContent:
    return GitHubContent(name=name, path=name, type=type, sha="abc", url="https://x", **kwargs)


def _readme_listing() -> list[GitHubContent]:
    return [_content("README.md")]


def _repo(name: str, stars: int = 100) -> GitHubRepo:
    return GitHubRepo(
        name=name, full_name=f"testdev/{name}", html_url="https://x",
        stargazers_count=stars,
    )


def _mock_client_for_readme(readme_text: str) -> AsyncMock:
    """Create a mock client that returns the given README text (base64-encoded)."""
    encoded = base64.b64encode(readme_text.encode()).decode()
    content_item = _content(
        "README.md",
        size=len(readme_text),
        content=encoded,
        encoding="base64",
    )
    client = AsyncMock()
    client.get_repo_contents = AsyncMock(return_value=[content_item])
    return client


async def test_word_count_calculated(user):
    readme_text = "Hello world this is a test readme with ten words here"
    client = _mock_client_for_readme(readme_text)
    repos = [_repo("repo1")]
    root_listings = {"repo1": _readme_listing()}

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.avg_word_count == len(readme_text.split())
    assert result.repos_analyzed == 1


async def test_headings_counted(user):
    readme_text = "# Heading 1\n\nSome text\n\n## Heading 2\n\nMore text\n\n### Heading 3\n"
    client = _mock_client_for_readme(readme_text)
    repos = [_repo("repo1")]
    root_listings = {"repo1": _readme_listing()}

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.avg_heading_count == 3.0


async def test_code_blocks_detected(user):
    readme_text = "# My Project\n\n```python\nprint('hello')\n```\n\nSome text.\n"
    client = _mock_client_for_readme(readme_text)
    repos = [_repo("repo1")]
    root_listings = {"repo1": _readme_listing()}

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.has_code_blocks_pct == 100.0


async def test_images_detected(user):
    readme_text = "# Project\n\n![screenshot](https://example.com/img.png)\n\nDone.\n"
    client = _mock_client_for_readme(readme_text)
    repos = [_repo("repo1")]
    root_listings = {"repo1": _readme_listing()}

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.has_images_pct == 100.0


async def test_images_detected_shields_badge(user):
    readme_text = "# Project\n\nhttps://img.shields.io/badge/status-active-green\n"
    client = _mock_client_for_readme(readme_text)
    repos = [_repo("repo1")]
    root_listings = {"repo1": _readme_listing()}

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.has_images_pct == 100.0


async def test_install_section_detected(user):
    readme_text = "# My Tool\n\n## Installation\n\nRun `pip install mytool`.\n"
    client = _mock_client_for_readme(readme_text)
    repos = [_repo("repo1")]
    root_listings = {"repo1": _readme_listing()}

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.has_install_section_pct == 100.0


async def test_install_section_detected_getting_started(user):
    readme_text = "# My Tool\n\n## Getting Started\n\nClone and run.\n"
    client = _mock_client_for_readme(readme_text)
    repos = [_repo("repo1")]
    root_listings = {"repo1": _readme_listing()}

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.has_install_section_pct == 100.0


async def test_returns_none_no_readmes(user):
    """Repos without READMEs in root listings should produce None."""
    client = AsyncMock()
    repos = [_repo("repo1"), _repo("repo2")]
    root_listings = {
        "repo1": [_content("main.py")],
        "repo2": [_content("index.js")],
    }

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is None


async def test_returns_none_empty_root_listings(user):
    """No root_listings at all should produce None."""
    client = AsyncMock()
    repos = [_repo("repo1")]

    result = await extract_readme_depth(client, user, repos, root_listings={})

    assert result is None


async def test_multiple_repos_averaged(user):
    # repo1: short README, no code blocks, no images, no install section
    readme1 = "# Repo One\n\nA short description with five words.\n"
    # repo2: longer README with code blocks, images, and install section
    readme2 = (
        "# Repo Two\n\n"
        "## Installation\n\n"
        "```bash\npip install repo2\n```\n\n"
        "![logo](https://example.com/logo.png)\n\n"
        "This is a longer README with more words to increase the average count.\n"
    )

    encoded1 = base64.b64encode(readme1.encode()).decode()
    encoded2 = base64.b64encode(readme2.encode()).decode()

    content1 = _content("README.md", size=len(readme1), content=encoded1, encoding="base64")
    content2 = _content("README.md", size=len(readme2), content=encoded2, encoding="base64")

    async def _get_contents(owner, repo, path):
        if repo == "repo1":
            return [content1]
        return [content2]

    client = AsyncMock()
    client.get_repo_contents = AsyncMock(side_effect=_get_contents)

    repos = [_repo("repo1", stars=200), _repo("repo2", stars=150)]
    root_listings = {
        "repo1": _readme_listing(),
        "repo2": _readme_listing(),
    }

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.repos_analyzed == 2

    # Averages should be between the two values
    wc1 = len(readme1.split())
    wc2 = len(readme2.split())
    expected_avg_wc = round((wc1 + wc2) / 2, 1)
    assert result.avg_word_count == expected_avg_wc

    # readme1 has 1 heading, readme2 has 2 headings → avg 1.5
    assert result.avg_heading_count == 1.5

    # Only repo2 has code blocks → 50%
    assert result.has_code_blocks_pct == 50.0

    # Only repo2 has images → 50%
    assert result.has_images_pct == 50.0

    # Only repo2 has install section → 50%
    assert result.has_install_section_pct == 50.0


async def test_graceful_on_failure(user):
    """Client failure should return None, not raise."""
    client = AsyncMock()
    client.get_repo_contents = AsyncMock(side_effect=Exception("Network error"))

    repos = [_repo("repo1")]
    root_listings = {"repo1": _readme_listing()}

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is None


async def test_graceful_partial_failure(user):
    """If one repo fails but another succeeds, result should be based on the successful one."""
    readme_text = "# Good Repo\n\nThis readme works fine.\n"
    encoded = base64.b64encode(readme_text.encode()).decode()
    good_content = _content("README.md", size=len(readme_text), content=encoded, encoding="base64")

    async def _get_contents(owner, repo, path):
        if repo == "repo-bad":
            raise Exception("Network error")
        return [good_content]

    client = AsyncMock()
    client.get_repo_contents = AsyncMock(side_effect=_get_contents)

    repos = [_repo("repo-bad", stars=200), _repo("repo-good", stars=150)]
    root_listings = {
        "repo-bad": _readme_listing(),
        "repo-good": _readme_listing(),
    }

    result = await extract_readme_depth(client, user, repos, root_listings=root_listings)

    assert result is not None
    assert result.repos_analyzed == 1
    assert result.avg_word_count == len(readme_text.split())
