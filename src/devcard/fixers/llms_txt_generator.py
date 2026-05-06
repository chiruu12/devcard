from __future__ import annotations


def generate_llms_txt(repo_data: dict) -> str:
    """Generate llms.txt. Pure function.

    repo_data keys: name, description, language, docs_files, examples_dir
    """
    sections: list[str] = []

    name = repo_data.get("name") or "Unnamed"
    sections.append(f"# {name}")

    # Description as blockquote
    description = repo_data.get("description")
    if description:
        sections.append(f"> {description}")

    # Language info
    language = repo_data.get("language")
    if language:
        sections.append(f"Primary language: {language}")

    # Docs links
    docs_files: list[str] = repo_data.get("docs_files") or []
    if docs_files:
        lines = ["## Docs", ""]
        for doc in docs_files:
            lines.append(f"- [{doc}]({doc})")
        sections.append("\n".join(lines))

    # Examples note
    examples_dir = repo_data.get("examples_dir")
    if examples_dir:
        sections.append(f"## Examples\n\nSee `{examples_dir}` for usage examples.")

    return "\n\n".join(sections)
