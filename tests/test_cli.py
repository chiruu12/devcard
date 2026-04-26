from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from devcard.cli import app
from devcard.models import DevCard, Generator, Identity

runner = CliRunner()


def _mock_devcard() -> DevCard:
    return DevCard(
        generated_at=datetime.now(UTC),
        generator=Generator(name="devcard", version="0.1.0"),
        identity=Identity(username="testuser", name="Test User"),
    )


def test_generate_json_output():
    with patch("devcard.cli.generate_devcard", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_devcard()
        result = runner.invoke(app, ["generate", "testuser", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["identity"]["username"] == "testuser"
        assert "$schema" in data


def test_generate_terminal_output():
    with patch("devcard.cli.generate_devcard", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_devcard()
        result = runner.invoke(app, ["generate", "testuser", "--format", "terminal"])
        assert result.exit_code == 0
        assert "testuser" in result.stdout


def test_validate_valid_file(tmp_path):
    valid = {
        "version": "1.0",
        "generated_at": "2025-01-01T00:00:00Z",
        "generator": {"name": "test", "version": "0.1"},
        "identity": {
            "username": "test", "public_repos": 0, "public_gists": 0,
            "followers": 0, "following": 0,
        },
    }
    f = tmp_path / "valid.json"
    f.write_text(json.dumps(valid))
    result = runner.invoke(app, ["validate", str(f)])
    assert result.exit_code == 0


def test_validate_invalid_file(tmp_path):
    f = tmp_path / "invalid.json"
    f.write_text('{"not": "a devcard"}')
    result = runner.invoke(app, ["validate", str(f)])
    assert result.exit_code == 1


def test_validate_missing_file():
    result = runner.invoke(app, ["validate", "/nonexistent/file.json"])
    assert result.exit_code == 1


def test_generate_markdown_output():
    with patch("devcard.cli.generate_devcard", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_devcard()
        result = runner.invoke(app, ["generate", "testuser", "--format", "markdown"])
        assert result.exit_code == 0
        assert "testuser" in result.stdout


def test_generate_toon_output():
    with patch("devcard.cli.generate_devcard", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_devcard()
        result = runner.invoke(app, ["generate", "testuser", "--format", "toon"])
        assert result.exit_code == 0
        assert "testuser" in result.stdout


def test_generate_agent_output():
    with patch("devcard.cli.generate_devcard", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_devcard()
        result = runner.invoke(app, ["generate", "testuser", "--format", "agent"])
        assert result.exit_code == 0
        assert "DEVCARD" in result.stdout
        assert "testuser" in result.stdout


def test_generate_llms_txt_output(tmp_path):
    with patch("devcard.cli.generate_devcard", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_devcard()
        out = tmp_path / "test.llms.txt"
        result = runner.invoke(
            app, ["generate", "testuser", "--format", "llms-txt", "-o", str(out)]
        )
        assert result.exit_code == 0
        content = out.read_text()
        assert "DevCard: testuser" in content


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.stdout
    assert "validate" in result.stdout
