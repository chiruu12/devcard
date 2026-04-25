from __future__ import annotations

import logging
from collections import defaultdict

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubRepo, GitHubUser
from devcard.mappings import TOPICS_TO_DOMAINS
from devcard.models import Domain, Expertise, FocusArea, Language, Stack

logger = logging.getLogger(__name__)

STACK_TO_DOMAIN: dict[str, str] = {
    "React": "Frontend Development",
    "Vue.js": "Frontend Development",
    "Angular": "Frontend Development",
    "Svelte": "Frontend Development",
    "Next.js": "Frontend Development",
    "Tailwind CSS": "Frontend Development",
    "Django": "Backend Development",
    "Flask": "Backend Development",
    "FastAPI": "Backend Development",
    "Express": "Backend Development",
    "Spring Boot": "Backend Development",
    "NestJS": "Backend Development",
    "Gin": "Backend Development",
    "Rails": "Backend Development",
    "TensorFlow": "Machine Learning",
    "PyTorch": "Machine Learning",
    "Keras": "Machine Learning",
    "scikit-learn": "Machine Learning",
    "Transformers": "Machine Learning",
    "pandas": "Data Science",
    "NumPy": "Data Science",
    "Polars": "Data Science",
    "PostgreSQL": "Databases",
    "Redis": "Databases",
    "MongoDB": "Databases",
    "Docker": "DevOps",
    "Kubernetes": "DevOps",
    "Terraform": "DevOps",
    "SwiftUI": "Mobile Development",
    "Jetpack Compose": "Mobile Development",
    "Flutter": "Mobile Development",
}

LANG_DOMAIN_HINTS: dict[str, str] = {
    "TypeScript": "Frontend Development",
    "JavaScript": "Frontend Development",
    "Swift": "Mobile Development",
    "Kotlin": "Mobile Development",
    "C": "Systems Programming",
    "Rust": "Systems Programming",
    "R": "Data Science",
}


async def extract_expertise(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    *,
    languages: list[Language] | None = None,
    stack: Stack | None = None,
    **kwargs,
) -> Expertise | None:
    try:
        domain_signals: dict[str, list[tuple[float, str]]] = defaultdict(list)

        for repo in repos:
            for topic in repo.topics:
                domain = TOPICS_TO_DOMAINS.get(topic.lower())
                if domain:
                    domain_signals[domain].append((0.7, f"topic:{topic} in {repo.name}"))

        if stack:
            for field_name in (
                "frameworks", "libraries", "databases", "tools",
                "platforms", "ci_cd", "testing",
            ):
                for item in getattr(stack, field_name, []):
                    domain = STACK_TO_DOMAIN.get(item.name)
                    if domain:
                        domain_signals[domain].append(
                            (0.6, f"stack:{item.name}")
                        )

        if languages:
            for lang in languages[:5]:
                domain = LANG_DOMAIN_HINTS.get(lang.name)
                if domain:
                    domain_signals[domain].append(
                        (0.3, f"language:{lang.name} ({lang.percentage:.0f}%)")
                    )

        domains: list[Domain] = []
        for name, signals in domain_signals.items():
            max_conf = max(conf for conf, _ in signals)
            bonus = min(0.1 * (len(signals) - 1), 0.3)
            final_conf = min(max_conf + bonus, 1.0)
            domains.append(Domain(name=name, confidence=round(final_conf, 2)))

        domains.sort(key=lambda d: d.confidence, reverse=True)
        domains = domains[:10]

        focus_areas: list[FocusArea] = []
        for domain_obj in domains[:5]:
            evidence = [ev for _, ev in domain_signals[domain_obj.name][:5]]
            focus_areas.append(FocusArea(name=domain_obj.name, evidence=evidence))

        return Expertise(domains=domains, focus_areas=focus_areas) if domains else None
    except Exception:
        logger.warning("Failed to extract expertise for %s", user.login, exc_info=True)
        return None
