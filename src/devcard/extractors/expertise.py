from __future__ import annotations

import logging
from collections import defaultdict

from devcard.github.client import GitHubClient
from devcard.github.models import GitHubContent, GitHubRepo, GitHubUser
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

FILE_DOMAIN_SIGNALS: dict[str, str] = {
    "train.py": "Machine Learning",
    "model.py": "Machine Learning",
    "config.yaml": "Machine Learning",
    "notebook": "Data Science",
    "deploy.yaml": "DevOps",
    "deploy.yml": "DevOps",
    "terraform": "DevOps",
    "kubernetes": "DevOps",
    "k8s": "DevOps",
    "Dockerfile": "DevOps",
    "docker-compose.yml": "DevOps",
    "migrations": "Backend Development",
    "alembic": "Backend Development",
    "prisma": "Backend Development",
    "android": "Mobile Development",
    "ios": "Mobile Development",
    "Podfile": "Mobile Development",
}

DOMAIN_TO_PACKAGES: dict[str, set[str]] = {
    "Machine Learning": {
        "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Transformers",
        "XGBoost", "LightGBM", "Hugging Face", "ONNX", "MLflow",
        "Weights & Biases", "DVC", "Ray", "Optuna", "JAX",
    },
    "Data Science": {
        "pandas", "NumPy", "Polars", "Matplotlib", "Seaborn",
        "Plotly", "Jupyter", "Dask", "Apache Spark", "Airflow",
    },
    "Frontend Development": {
        "React", "Vue.js", "Angular", "Svelte", "Next.js",
        "Tailwind CSS", "Vite", "Webpack", "Storybook", "Jest",
        "Cypress", "Playwright", "shadcn/ui", "Radix",
    },
    "Backend Development": {
        "Django", "Flask", "FastAPI", "Express", "NestJS",
        "Spring Boot", "Gin", "Rails", "Laravel", "Phoenix",
        "Prisma", "SQLAlchemy", "Alembic", "GraphQL",
    },
    "DevOps": {
        "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins",
        "GitHub Actions", "GitLab CI", "Prometheus", "Grafana",
        "Helm", "Pulumi", "AWS CDK",
    },
    "Mobile Development": {
        "SwiftUI", "Jetpack Compose", "Flutter", "React Native",
        "Expo", "CocoaPods", "Gradle",
    },
    "Systems Programming": set(),
    "Databases": {
        "PostgreSQL", "Redis", "MongoDB", "MySQL", "SQLite",
        "Cassandra", "DynamoDB", "Elasticsearch",
    },
}


async def extract_expertise(
    client: GitHubClient,
    user: GitHubUser,
    repos: list[GitHubRepo],
    *,
    languages: list[Language] | None = None,
    stack: Stack | None = None,
    starred_repos: list[GitHubRepo] | None = None,
    root_listings: dict[str, list[GitHubContent]] | None = None,
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

        if starred_repos:
            for repo in starred_repos:
                for topic in repo.topics:
                    domain = TOPICS_TO_DOMAINS.get(topic.lower())
                    if domain:
                        domain_signals[domain].append(
                            (0.4, f"starred:{repo.name}")
                        )

        if root_listings:
            for repo_name, contents in root_listings.items():
                file_names = {c.name for c in contents}
                for pattern, domain in FILE_DOMAIN_SIGNALS.items():
                    if pattern in file_names:
                        domain_signals[domain].append(
                            (0.5, f"file:{pattern} in {repo_name}")
                        )

        domains: list[Domain] = []
        for name, signals in domain_signals.items():
            max_conf = max(conf for conf, _ in signals)
            bonus = min(0.1 * (len(signals) - 1), 0.3)
            final_conf = min(max_conf + bonus, 1.0)
            skill_level = _compute_skill_level(name, stack, signals)
            domains.append(Domain(
                name=name,
                confidence=round(final_conf, 2),
                skill_level=skill_level,
            ))

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


def _compute_skill_level(
    domain_name: str,
    stack: Stack | None,
    signals: list[tuple[float, str]],
) -> str:
    known_packages = DOMAIN_TO_PACKAGES.get(domain_name, set())
    if not known_packages or not stack:
        if len(signals) >= 8:
            return "advanced"
        if len(signals) >= 4:
            return "intermediate"
        return "beginner"

    all_stack_names = set()
    for field in ("frameworks", "libraries", "databases", "tools",
                  "platforms", "ci_cd", "testing"):
        for item in getattr(stack, field, []):
            all_stack_names.add(item.name)

    matched = known_packages & all_stack_names
    count = len(matched)
    has_projects = any("topic:" in ev or "file:" in ev for _, ev in signals)

    if count >= 6 and has_projects:
        return "expert"
    if count >= 4 or (count >= 2 and has_projects):
        return "advanced"
    if count >= 2 or len(signals) >= 4:
        return "intermediate"
    return "beginner"
