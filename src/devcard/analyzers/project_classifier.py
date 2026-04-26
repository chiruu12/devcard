from __future__ import annotations

from devcard.mappings import TOPICS_TO_DOMAINS
from devcard.models import DevCard

_LIB_SIGNALS = {"lib", "sdk", "library", "package", "module", "client", "wrapper", "binding"}
_TOOL_SIGNALS = {"cli", "tool", "utility", "command", "script", "generator", "linter", "formatter"}
_DOCS_SIGNALS = {"docs", "documentation", "wiki", "guide", "tutorial", "handbook", "reference"}
_LEARNING_SIGNALS = {
    "tutorial", "learning", "course", "example", "demo",
    "starter", "boilerplate", "template", "awesome",
}
_FRAMEWORK_SIGNALS = {"framework", "engine", "platform"}
_CONFIG_SIGNALS = {"dotfiles", "config", "configuration", "setup", "nvim", "vim", "emacs", "nix"}


def _classify_one(name: str, description: str, topics: list[str]) -> str:
    tokens = set(name.lower().replace("-", " ").replace("_", " ").split())
    desc_lower = description.lower().replace("-", " ").replace("_", " ")
    desc_tokens = set(desc_lower.split()) if description else set()
    topic_set = {t.lower() for t in topics}
    all_signals = tokens | desc_tokens | topic_set

    if all_signals & _FRAMEWORK_SIGNALS:
        return "framework"
    if all_signals & _LIB_SIGNALS:
        return "library"
    if all_signals & _TOOL_SIGNALS:
        return "tool"
    if all_signals & _CONFIG_SIGNALS:
        return "config"
    if all_signals & _DOCS_SIGNALS:
        return "docs"
    if all_signals & _LEARNING_SIGNALS:
        return "learning"
    return "application"


def classify_projects(devcard: DevCard) -> None:
    for project in devcard.projects:
        if project.classification is None:
            project.classification = _classify_one(
                project.name,
                project.description or "",
                project.topics,
            )
    _mark_signature(devcard)
    _generate_narratives(devcard)


def _mark_signature(devcard: DevCard) -> None:
    if not devcard.projects:
        return
    best = max(
        devcard.projects,
        key=lambda p: p.stars * 3 + p.forks * 2 + (10 if p.status == "active" else 0),
    )
    if best.stars > 0 or best.forks > 0:
        best.is_signature = True


_NARRATIVE_TEMPLATES: dict[str, str] = {
    "framework": "{lang} framework",
    "library": "{lang} library",
    "tool": "{lang} developer tool",
    "application": "{lang} project",
    "config": "{lang} configuration",
    "docs": "{lang} documentation",
    "learning": "{lang} project",
}


_DOMAIN_SHORT_LABELS: dict[str, str] = {
    "Machine Learning": "ML",
    "Data Science": "Data",
    "Frontend Development": "Frontend",
    "Backend Development": "Backend",
    "DevOps": "DevOps",
    "Mobile Development": "Mobile",
    "Systems Programming": "Systems",
    "Databases": "Database",
    "Web Development": "Web",
    "Security": "Security",
}


def _infer_domain_label(proj) -> str | None:
    for topic in proj.topics:
        domain = TOPICS_TO_DOMAINS.get(topic.lower())
        if domain:
            return _DOMAIN_SHORT_LABELS.get(domain, domain)
    return None


def _generate_narratives(devcard: DevCard) -> None:
    for proj in devcard.projects:
        if proj.narrative is not None:
            continue
        template = _NARRATIVE_TEMPLATES.get(
            proj.classification or "application", "{lang} project"
        )
        lang = proj.language or "Multi-language"
        base = template.format(lang=lang)

        domain = _infer_domain_label(proj)
        if domain:
            first_char = base[0].lower()
            base = f"{domain} {first_char}{base[1:]}"

        parts = [base]
        if proj.stars:
            parts.append(f"{proj.stars:,} stars")
        narrative = " · ".join(parts)

        if proj.is_signature:
            narrative = f"Flagship: {narrative}"

        if proj.description:
            desc = proj.description[:80].rstrip()
            if len(proj.description) > 80:
                desc += "..."
            narrative = f"{narrative} — {desc}"

        proj.narrative = narrative
