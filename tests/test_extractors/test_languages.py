from __future__ import annotations

import httpx
import pytest

from devcard.config import DevCardConfig
from devcard.extractors.languages import extract_languages
from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser

LANG_RESPONSES = {
    "/repos/testdev/repo-a/languages": {"Python": 500000, "HTML": 50000},
    "/repos/testdev/repo-b/languages": {"Python": 100000, "TypeScript": 300000},
}


def _mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in LANG_RESPONSES:
            return httpx.Response(200, json=LANG_RESPONSES[path])
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


@pytest.fixture
def client():
    config = DevCardConfig(github_token="fake", no_cache=True)
    c = GitHubClient(config)
    c._http = httpx.AsyncClient(transport=_mock_transport())
    return c


@pytest.fixture
def repos():
    return [
        GitHubRepo(
            name="repo-a", full_name="testdev/repo-a",
            html_url="https://github.com/testdev/repo-a", fork=False,
        ),
        GitHubRepo(
            name="repo-b", full_name="testdev/repo-b",
            html_url="https://github.com/testdev/repo-b", fork=False,
        ),
    ]


@pytest.fixture
def user():
    return GitHubUser(login="testdev")


async def test_languages_aggregates_bytes(client, user, repos):
    result = await extract_languages(client, user, repos)
    assert result is not None
    assert len(result) == 3
    assert result[0].name == "Python"
    assert result[0].percentage > 50


async def test_languages_sorted_descending(client, user, repos):
    result = await extract_languages(client, user, repos)
    percentages = [lang.percentage for lang in result]
    assert percentages == sorted(percentages, reverse=True)


async def test_languages_colors_present(client, user, repos):
    result = await extract_languages(client, user, repos)
    python = next(lang for lang in result if lang.name == "Python")
    assert python.color == "#3572A5"


async def test_languages_empty_repos(client, user):
    result = await extract_languages(client, user, repos=[])
    assert result is None


def test_jupyter_notebook_weight_exists():
    from devcard.extractors.languages import LANGUAGE_BYTE_WEIGHTS

    assert "Jupyter Notebook" in LANGUAGE_BYTE_WEIGHTS
    assert LANGUAGE_BYTE_WEIGHTS["Jupyter Notebook"] == 0.05


def _notebook_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "languages" in path:
            return httpx.Response(
                200, json={"Jupyter Notebook": 1000000, "Python": 50000}
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.fixture
def notebook_client():
    from devcard.config import DevCardConfig
    from devcard.github.client import GitHubClient

    config = DevCardConfig(github_token="fake", no_cache=True)
    c = GitHubClient(config)
    c._http = httpx.AsyncClient(transport=_notebook_mock_transport())
    return c


@pytest.fixture
def notebook_repos():
    return [
        GitHubRepo(
            name="nb-repo", full_name="testdev/nb-repo",
            html_url="https://github.com/testdev/nb-repo",
        ),
    ]


async def test_jupyter_penalized_in_percentages(notebook_client, user, notebook_repos):
    result = await extract_languages(notebook_client, user, notebook_repos)
    assert result is not None
    python = next(lang for lang in result if lang.name == "Python")
    jupyter = next(lang for lang in result if lang.name == "Jupyter Notebook")
    assert python.percentage >= jupyter.percentage
