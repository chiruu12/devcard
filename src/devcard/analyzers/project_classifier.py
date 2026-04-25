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
