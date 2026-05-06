from __future__ import annotations

_MAX_TOPICS = 20


def suggest_topics(repo_data: dict) -> list[str]:
    """Suggest GitHub topics. Pure function.

    repo_data keys: name, language, stack, readme_keywords, existing_topics
    Returns deduplicated list max 20 items.
    """
    seen: set[str] = set()
    topics: list[str] = []

    def _add(raw: str) -> None:
        normalised = raw.lower().replace(" ", "-")
        if normalised and normalised not in seen:
            seen.add(normalised)
            topics.append(normalised)

    # Existing topics first (preserve them)
    for t in repo_data.get("existing_topics") or []:
        _add(t)

    # Language
    language = repo_data.get("language")
    if language:
        _add(language)

    # Stack items
    for item in repo_data.get("stack") or []:
        _add(item)

    # Readme keywords
    for kw in repo_data.get("readme_keywords") or []:
        _add(kw)

    return topics[:_MAX_TOPICS]
