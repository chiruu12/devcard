from __future__ import annotations

_MAX_LEN = 350


def generate_description(repo_data: dict) -> str:
    """Generate a repo description. Pure function.

    repo_data keys: name, language, classification, readme_first_paragraph, stack
    Returns string max 350 chars (GitHub description limit).
    """
    readme = repo_data.get("readme_first_paragraph") or ""
    if len(readme) > 10:
        return readme[:_MAX_LEN]

    language = repo_data.get("language")
    classification = repo_data.get("classification")
    stack: list[str] = repo_data.get("stack") or []

    if language and stack:
        stack_str = ", ".join(stack[:3])
        return f"{language} {classification or 'project'} built with {stack_str}"[:_MAX_LEN]

    if language:
        return f"{language} {classification or 'project'}"[:_MAX_LEN]

    return repo_data.get("name") or ""
