from __future__ import annotations

import json

from devcard.extractors.stack import (
    _parse_cargo_toml,
    _parse_composer_json,
    _parse_gemfile,
    _parse_go_mod,
    _parse_package_json,
    _parse_pyproject_toml,
    _parse_requirements_txt,
)


def test_parse_package_json():
    content = json.dumps({
        "dependencies": {"react": "^18.0", "next": "^14.0"},
        "devDependencies": {"jest": "^29"},
    })
    result = _parse_package_json(content)
    assert "react" in result
    assert "next" in result
    assert "jest" in result


def test_parse_package_json_scoped():
    content = '{"dependencies": {"@tanstack/react-query": "^5.0", "axios": "^1.0"}}'
    result = _parse_package_json(content)
    assert "react-query" in result
    assert "axios" in result


def test_parse_requirements_txt():
    content = """
fastapi>=0.100
sqlalchemy>=2.0
# comment
-r base.txt
pydantic[email]>=2.0
"""
    result = _parse_requirements_txt(content)
    assert "fastapi" in result
    assert "sqlalchemy" in result
    assert "pydantic" in result
    assert len([r for r in result if r.startswith("#")]) == 0
    assert len([r for r in result if r.startswith("-")]) == 0


def test_parse_pyproject_toml():
    content = """
[project]
dependencies = [
    "fastapi>=0.100",
    "pydantic>=2.0",
]
"""
    result = _parse_pyproject_toml(content)
    assert "fastapi" in result
    assert "pydantic" in result


def test_parse_pyproject_toml_poetry():
    content = """
[tool.poetry.dependencies]
python = "^3.11"
django = "^5.0"
celery = "^5.3"
"""
    result = _parse_pyproject_toml(content)
    assert "django" in result
    assert "celery" in result
    assert "python" not in result


def test_parse_go_mod():
    content = """module github.com/user/repo

go 1.21

require (
\tgithub.com/gin-gonic/gin v1.9.0
\tgithub.com/stretchr/testify v1.8.0
)
"""
    result = _parse_go_mod(content)
    assert "gin" in result
    assert "testify" in result


def test_parse_cargo_toml():
    content = """
[dependencies]
serde = "1.0"
tokio = { version = "1", features = ["full"] }

[dev-dependencies]
criterion = "0.5"
"""
    result = _parse_cargo_toml(content)
    assert "serde" in result
    assert "tokio" in result
    assert "criterion" in result


def test_parse_gemfile():
    content = """
source 'https://rubygems.org'
gem 'rails', '~> 7.0'
gem "sidekiq"
gem 'rspec', group: :test
"""
    result = _parse_gemfile(content)
    assert "rails" in result
    assert "sidekiq" in result
    assert "rspec" in result


def test_parse_composer_json():
    content = json.dumps({
        "require": {"php": "^8.1", "laravel/framework": "^10.0", "guzzlehttp/guzzle": "^7.0"},
    })
    result = _parse_composer_json(content)
    assert "framework" in result or "laravel" in result
    assert "guzzle" in result
    assert "php" not in result


def test_parse_package_json_invalid():
    assert _parse_package_json("not json") == []


def test_parse_pyproject_toml_invalid():
    assert _parse_pyproject_toml("not [valid toml") == []
