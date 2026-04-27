from __future__ import annotations

import base64
import json

import httpx
import pytest

from devcard.config import DevCardConfig
from devcard.github.client import GitHubAPIError, GitHubClient


def _make_client(transport: httpx.MockTransport) -> GitHubClient:
    config = DevCardConfig(
        github_token="test-token",
        base_url="https://api.github.com",
        no_cache=True,
    )
    client = GitHubClient(config)
    client._http = httpx.AsyncClient(
        transport=transport,
        base_url=config.base_url,
        headers=client._http.headers,
        timeout=30.0,
    )
    return client


class TestCreateOrUpdateFile:
    async def test_creates_new_file(self):
        """When GET returns 404 (file doesn't exist), PUT without SHA, verify 201."""
        requests_log: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests_log.append(request)
            if request.method == "GET":
                return httpx.Response(404, json={"message": "Not Found"})
            if request.method == "PUT":
                return httpx.Response(
                    201,
                    json={"content": {"sha": "abc123"}},
                    headers={"X-RateLimit-Remaining": "4999"},
                )
            return httpx.Response(405)

        client = _make_client(httpx.MockTransport(handler))
        try:
            result = await client.create_or_update_file(
                owner="octocat",
                repo="hello-world",
                path="devcard.json",
                content='{"test": true}',
                commit_message="Add devcard.json",
            )

            assert result == {"content": {"sha": "abc123"}}

            # Verify PUT request body
            put_request = requests_log[-1]
            assert put_request.method == "PUT"
            body = json.loads(put_request.content)
            assert body["message"] == "Add devcard.json"
            assert "sha" not in body
            # Content should be base64-encoded
            decoded = base64.b64decode(body["content"]).decode()
            assert decoded == '{"test": true}'
        finally:
            await client.close()

    async def test_updates_existing_file(self):
        """When GET returns 200 with SHA, PUT includes SHA."""
        requests_log: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests_log.append(request)
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={"sha": "existing-sha-456"},
                    headers={"X-RateLimit-Remaining": "4998"},
                )
            if request.method == "PUT":
                return httpx.Response(
                    200,
                    json={"content": {"sha": "updated-sha-789"}},
                    headers={"X-RateLimit-Remaining": "4997"},
                )
            return httpx.Response(405)

        client = _make_client(httpx.MockTransport(handler))
        try:
            result = await client.create_or_update_file(
                owner="octocat",
                repo="hello-world",
                path="devcard.json",
                content='{"updated": true}',
                commit_message="Update devcard.json",
            )

            assert result == {"content": {"sha": "updated-sha-789"}}

            # Verify PUT request includes SHA
            put_request = requests_log[-1]
            assert put_request.method == "PUT"
            body = json.loads(put_request.content)
            assert body["sha"] == "existing-sha-456"
            assert body["message"] == "Update devcard.json"
        finally:
            await client.close()

    async def test_raises_on_put_failure(self):
        """When PUT returns 422, raises GitHubAPIError."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(404, json={"message": "Not Found"})
            if request.method == "PUT":
                return httpx.Response(
                    422,
                    json={"message": "Validation Failed"},
                    headers={"X-RateLimit-Remaining": "4999"},
                )
            return httpx.Response(405)

        client = _make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.create_or_update_file(
                    owner="octocat",
                    repo="hello-world",
                    path="bad/path",
                    content="content",
                    commit_message="This will fail",
                )
            assert exc_info.value.status_code == 422
        finally:
            await client.close()


class TestUpdateRepoDescription:
    async def test_updates_description(self):
        """PATCH with description, verify response."""
        requests_log: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests_log.append(request)
            return httpx.Response(
                200,
                json={"description": "New description", "full_name": "octocat/hello-world"},
                headers={"X-RateLimit-Remaining": "4999"},
            )

        client = _make_client(httpx.MockTransport(handler))
        try:
            result = await client.update_repo_description(
                owner="octocat",
                repo="hello-world",
                description="New description",
            )

            assert result["description"] == "New description"

            patch_request = requests_log[0]
            assert patch_request.method == "PATCH"
            body = json.loads(patch_request.content)
            assert body == {"description": "New description"}
        finally:
            await client.close()

    async def test_raises_on_failure(self):
        """When PATCH returns 403, raises GitHubAPIError."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403,
                json={"message": "Forbidden"},
                headers={"X-RateLimit-Remaining": "4999"},
            )

        client = _make_client(httpx.MockTransport(handler))
        try:
            with pytest.raises(GitHubAPIError) as exc_info:
                await client.update_repo_description(
                    owner="octocat",
                    repo="hello-world",
                    description="Should fail",
                )
            assert exc_info.value.status_code == 403
        finally:
            await client.close()


class TestUpdateRepoTopics:
    async def test_replaces_topics(self):
        """PUT with names list, verify response."""
        requests_log: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests_log.append(request)
            return httpx.Response(
                200,
                json={"names": ["python", "devcard", "cli"]},
                headers={"X-RateLimit-Remaining": "4999"},
            )

        client = _make_client(httpx.MockTransport(handler))
        try:
            result = await client.update_repo_topics(
                owner="octocat",
                repo="hello-world",
                topics=["python", "devcard", "cli"],
            )

            assert result == {"names": ["python", "devcard", "cli"]}

            put_request = requests_log[0]
            assert put_request.method == "PUT"
            body = json.loads(put_request.content)
            assert body == {"names": ["python", "devcard", "cli"]}
        finally:
            await client.close()
