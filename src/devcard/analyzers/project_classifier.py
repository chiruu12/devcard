from __future__ import annotations

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
    "framework": "A {lang} framework with {stars} stars",
    "library": "A {lang} library with {stars} stars",
    "tool": "A {lang} developer tool with {stars} stars",
    "application": "A {lang} application with {stars} stars",
    "config": "Developer configuration and environment setup",
    "docs": "Documentation and reference material",
    "learning": "Learning resource and examples",
}


def _generate_narratives(devcard: DevCard) -> None:
    for proj in devcard.projects:
        if proj.narrative is not None:
            continue
        template = _NARRATIVE_TEMPLATES.get(
            proj.classification or "application", "A project with {stars} stars"
        )
        lang = proj.language or "multi-language"
        narrative = template.format(lang=lang, stars=f"{proj.stars:,}")
        if proj.is_signature:
            narrative = f"Signature project — {narrative.lower()}"
        if proj.description:
            desc = proj.description[:60]
            if len(proj.description) > 60:
                desc += "..."
            narrative = f"{narrative} — {desc}"
        proj.narrative = narrative
