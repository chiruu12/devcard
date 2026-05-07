"""Profile Advisor: rules-based verdicts + optional LLM summary."""
from __future__ import annotations

import logging

from devcard.advisor.context import build_context
from devcard.advisor.engine import evaluate_all_rules, load_rules
from devcard.advisor.llm_advisor import AdvisorLLM
from devcard.analyzers.scoring import compute_agent_readiness_score, compute_human_visibility_score
from devcard.config import DevCardConfig
from devcard.github.client import GitHubClient
from devcard.models import ProfileAdvice
from devcard.pipeline import _fetch_profile_repo_data, generate_devcard

logger = logging.getLogger(__name__)


async def advise_pipeline(
    username: str,
    config: DevCardConfig,
    *,
    enrich: bool = False,
) -> ProfileAdvice:
    """Generate profile advice: rules-based verdicts + optional LLM summary."""
    devcard = await generate_devcard(username, config)

    client = GitHubClient(config)
    try:
        profile = await _fetch_profile_repo_data(client, username)
    finally:
        await client.close()

    human_score = compute_human_visibility_score(devcard, profile)
    agent_score = compute_agent_readiness_score(devcard, profile)

    context = build_context(devcard, human_score, agent_score)
    rules = load_rules()
    verdicts = evaluate_all_rules(rules, context)

    summary = None
    if enrich:
        llm = AdvisorLLM.from_config(config)
        if llm:
            try:
                summary = await llm.generate_summary(devcard, verdicts)
            finally:
                await llm.close()

    return ProfileAdvice(
        username=username,
        human_score=human_score,
        agent_score=agent_score,
        verdicts=verdicts,
        summary=summary,
    )
