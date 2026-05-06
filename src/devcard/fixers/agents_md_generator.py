from __future__ import annotations


def generate_agents_md(repo_data: dict) -> str:
    """Generate AGENTS.md. Pure function.

    repo_data keys: name, readme_first_paragraph, language, stack, directories, config_files
    """
    sections: list[str] = []

    name = repo_data.get("name") or "Unnamed"
    sections.append(f"# {name}")

    # Overview
    overview = repo_data.get("readme_first_paragraph")
    if overview:
        sections.append(f"## Overview\n\n{overview}")
    else:
        sections.append(f"## Overview\n\n{name} repository.")

    # Tech Stack
    language = repo_data.get("language")
    stack: list[str] = repo_data.get("stack") or []
    if language or stack:
        lines = ["## Tech Stack", ""]
        if language:
            lines.append(f"- Language: {language}")
        for item in stack:
            lines.append(f"- {item}")
        sections.append("\n".join(lines))

    # Structure
    directories: list[str] = repo_data.get("directories") or []
    if directories:
        lines = ["## Structure", ""]
        for d in directories:
            lines.append(f"- `{d}`")
        sections.append("\n".join(lines))

    # Configuration
    config_files: list[str] = repo_data.get("config_files") or []
    if config_files:
        lines = ["## Configuration", ""]
        for f in config_files:
            lines.append(f"- `{f}`")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
