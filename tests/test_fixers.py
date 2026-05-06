from __future__ import annotations

import json
from datetime import UTC, datetime

from devcard.fixers.agents_md_generator import generate_agents_md
from devcard.fixers.description_generator import generate_description
from devcard.fixers.devcard_deployer import prepare_devcard_files
from devcard.fixers.llms_txt_generator import generate_llms_txt
from devcard.fixers.profile_readme_generator import generate_profile_readme
from devcard.fixers.topic_suggester import suggest_topics
from devcard.models import (
    DevCard,
    Generator,
    Identity,
    Language,
    Project,
)


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="test", version="0.0.1"),
        identity=Identity(username="testuser"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


# --- description_generator ---


class TestDescriptionGenerator:
    def test_generates_from_readme(self):
        repo = {
            "name": "httpclient",
            "language": "Python",
            "classification": "library",
            "readme_first_paragraph": "A fast HTTP client for Python with async support",
            "stack": ["httpx", "asyncio"],
        }
        desc = generate_description(repo)
        assert "fast" in desc.lower() or "HTTP" in desc
        assert len(desc) <= 350

    def test_generates_fallback_without_readme(self):
        repo = {
            "name": "mytool",
            "language": "Go",
            "classification": "tool",
            "readme_first_paragraph": "",
            "stack": ["cobra", "viper"],
        }
        desc = generate_description(repo)
        assert "Go" in desc
        assert "tool" in desc

    def test_returns_string_on_no_data(self):
        repo = {
            "name": "empty-repo",
            "language": None,
            "classification": None,
            "readme_first_paragraph": None,
            "stack": [],
        }
        desc = generate_description(repo)
        assert isinstance(desc, str)
        assert len(desc) > 0


# --- topic_suggester ---


class TestTopicSuggester:
    def test_suggests_from_language(self):
        repo = {
            "name": "mylib",
            "language": "Python",
            "stack": [],
            "readme_keywords": [],
            "existing_topics": [],
        }
        topics = suggest_topics(repo)
        assert "python" in topics
        assert len(topics) <= 20

    def test_suggests_from_stack(self):
        repo = {
            "name": "frontend-app",
            "language": "TypeScript",
            "stack": ["react", "next"],
            "readme_keywords": [],
            "existing_topics": [],
        }
        topics = suggest_topics(repo)
        assert "react" in topics or "nextjs" in topics or "typescript" in topics

    def test_does_not_duplicate_existing(self):
        repo = {
            "name": "mylib",
            "language": "Python",
            "stack": ["python"],
            "readme_keywords": ["python"],
            "existing_topics": ["python"],
        }
        topics = suggest_topics(repo)
        assert topics.count("python") <= 1

    def test_max_20_topics(self):
        repo = {
            "name": "big-project",
            "language": "JavaScript",
            "stack": [f"lib{i}" for i in range(15)],
            "readme_keywords": [f"kw{i}" for i in range(15)],
            "existing_topics": [f"topic{i}" for i in range(5)],
        }
        topics = suggest_topics(repo)
        assert len(topics) <= 20


# --- agents_md_generator ---


class TestAgentsMdGenerator:
    def test_generates_valid_markdown(self):
        repo = {
            "name": "my-project",
            "readme_first_paragraph": "A CLI tool for data processing.",
            "language": "Python",
            "stack": ["click", "pandas"],
            "directories": ["src/", "tests/", "docs/"],
            "config_files": ["pyproject.toml", ".github/workflows/ci.yml"],
        }
        md = generate_agents_md(repo)
        assert "# my-project" in md
        assert "Python" in md
        assert "click" in md or "pandas" in md
        assert "src/" in md or "tests/" in md

    def test_handles_minimal_data(self):
        repo = {
            "name": "bare",
            "readme_first_paragraph": None,
            "language": None,
            "stack": [],
            "directories": [],
            "config_files": [],
        }
        md = generate_agents_md(repo)
        assert isinstance(md, str)
        assert len(md) > 0
        assert "# bare" in md


# --- llms_txt_generator ---


class TestLlmsTxtGenerator:
    def test_generates_valid_llms_txt(self):
        repo = {
            "name": "my-lib",
            "description": "A useful library",
            "language": "Rust",
            "docs_files": ["README.md", "docs/guide.md"],
            "examples_dir": "examples/",
        }
        txt = generate_llms_txt(repo)
        assert "# my-lib" in txt
        assert "docs/guide.md" in txt or "README.md" in txt

    def test_handles_no_docs(self):
        repo = {
            "name": "nodocs",
            "description": None,
            "language": None,
            "docs_files": [],
            "examples_dir": None,
        }
        txt = generate_llms_txt(repo)
        assert isinstance(txt, str)
        assert "# nodocs" in txt


# --- profile_readme_generator ---


class TestProfileReadmeGenerator:
    def test_generates_readme_with_greeting(self):
        card = _make_devcard(
            identity=Identity(username="alice", name="Alice Smith", bio="Open source dev"),
            languages=[Language(name="Python", percentage=60.0)],
            projects=[
                Project(name="coolproject", description="Cool", stars=42),
            ],
        )
        svg = "<svg>card content</svg>"
        readme = generate_profile_readme(card, svg_content=svg)
        assert "Alice Smith" in readme or "alice" in readme
        assert "coolproject" in readme
        assert "<svg>card content</svg>" in readme or "svg" in readme.lower()

    def test_handles_minimal_card(self):
        card = _make_devcard()
        readme = generate_profile_readme(card)
        assert "testuser" in readme


# --- devcard_deployer ---


class TestDevcardDeployer:
    def test_returns_dict_of_files(self):
        card = _make_devcard()
        files = prepare_devcard_files(card)
        assert isinstance(files, dict)
        assert "devcard.json" in files

    def test_json_is_valid(self):
        card = _make_devcard(
            identity=Identity(username="deployme"),
        )
        files = prepare_devcard_files(card)
        parsed = json.loads(files["devcard.json"])
        assert parsed["identity"]["username"] == "deployme"
