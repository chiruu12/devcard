from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


def _detect_token(cli_token: str | None = None) -> str | None:
    if cli_token:
        return cli_token

    env_token = os.environ.get("GITHUB_TOKEN")
    if env_token:
        return env_token

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


@dataclass
class DevCardConfig:
    github_token: str | None = None
    base_url: str = "https://api.github.com"
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "devcard")
    cache_ttl: int = 3600
    max_repos: int = 30
    no_cache: bool = False
    fireworks_api_key: str | None = None
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"
    llm_model: str = "accounts/fireworks/models/gpt-oss-120b"

    @classmethod
    def create(cls, token: str | None = None, **kwargs) -> DevCardConfig:
        resolved_token = _detect_token(token)
        if not resolved_token:
            logger.warning(
                "No GitHub token found. Rate limit: 60 requests/hour. "
                "Set GITHUB_TOKEN or use --token for 5000 requests/hour."
            )
        fireworks_key = kwargs.pop("fireworks_api_key", None) or os.environ.get(
            "FIREWORKS_API_KEY"
        )
        return cls(
            github_token=resolved_token,
            fireworks_api_key=fireworks_key,
            **kwargs,
        )
