"""LLM-powered enrichment for DevCard profiles."""
from __future__ import annotations

import json
import logging
from typing import Any

from devcard.config import DevCardConfig
from devcard.enrichment.models import EnrichmentResponse
from devcard.enrichment.provider import FireworksProvider, ModelConfig
from devcard.models import DevCard, Enriched, ProjectHighlight

logger = logging.getLogger(__name__)


def _serialize_devcard_for_llm(devcard: DevCard) -> str:
    data: dict[str, Any] = {}

    data["identity"] = {
        "username": devcard.identity.username,
        "name": devcard.identity.name,
        "bio": devcard.identity.bio,
        "location": devcard.identity.location,
        "followers": devcard.identity.followers,
        "public_repos": devcard.identity.public_repos,
    }

    if devcard.languages:
        data["languages"] = [
            {"name": lang.name, "percentage": lang.percentage, "category": lang.category}
            for lang in devcard.languages[:8]
        ]

    if devcard.stack:
        stack: dict[str, list[str]] = {}
        for field in (
            "frameworks", "libraries", "databases", "tools",
            "platforms", "ci_cd", "testing",
        ):
            items = getattr(devcard.stack, field, [])
            if items:
                stack[field] = [item.name for item in items]
        data["stack"] = stack

    if devcard.projects:
        data["projects"] = [
            {
                "name": p.name,
                "description": p.description,
                "stars": p.stars,
                "forks": p.forks,
                "language": p.language,
                "topics": p.topics,
                "status": p.status,
                "classification": p.classification,
            }
            for p in devcard.projects
        ]

    if devcard.expertise:
        expertise_data: dict[str, Any] = {
            "profile_type": devcard.expertise.profile_type,
            "domains": [
                {"name": d.name, "confidence": d.confidence, "skill_level": d.skill_level}
                for d in devcard.expertise.domains
            ],
        }
        if devcard.expertise.focus_areas:
            expertise_data["focus_areas"] = [
                fa.name for fa in devcard.expertise.focus_areas
            ]
        data["expertise"] = expertise_data

    if devcard.activity:
        data["activity"] = {
            "status": devcard.activity.status,
            "commits_last_year": devcard.activity.commits_last_year,
            "consistency_score": devcard.activity.consistency_score,
            "consistency_description": devcard.activity.consistency_description,
        }

    if devcard.quality:
        data["quality"] = {
            "score": devcard.quality.score,
            "ci_adoption": devcard.quality.ci_adoption,
            "test_adoption": devcard.quality.test_adoption,
            "docs_adoption": devcard.quality.docs_adoption,
            "license_adoption": devcard.quality.license_adoption,
            "linter_adoption": devcard.quality.linter_adoption,
            "recommendations": devcard.quality.recommendations,
        }

    return json.dumps(data, indent=2, default=str)


async def enrich_devcard(devcard: DevCard, config: DevCardConfig) -> Enriched | None:
    if not config.fireworks_api_key:
        return None

    provider = FireworksProvider(
        api_key=config.fireworks_api_key,
        base_url=config.fireworks_base_url,
    )
    model_config = ModelConfig(
        model=config.llm_model,
        temperature=0.3,
        max_tokens=2048,
    )

    try:
        devcard_data = _serialize_devcard_for_llm(devcard)
        result = await provider.get_structured_output(
            output_model=EnrichmentResponse,
            context={"devcard_data": devcard_data},
            message=f"Analyze this developer profile for {devcard.identity.username}.",
            model_config=model_config,
        )

        highlights = [
            ProjectHighlight(
                name=h.name,
                reason=h.reason,
                significance=h.significance,
            )
            for h in result.project_highlights
        ]

        return Enriched(
            summary=result.summary,
            archetype=result.archetype,
            strengths=result.strengths,
            suggestions=result.suggestions,
            project_highlights=highlights,
        )
    except Exception:
        logger.warning("Enrichment failed for %s", devcard.identity.username, exc_info=True)
        return None
    finally:
        await provider.close()
