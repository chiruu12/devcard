from __future__ import annotations

from devcard.models import DevCard


def generate_profile_readme(devcard: DevCard, svg_content: str | None = None) -> str:
    """Generate profile README.md. Pure function."""
    sections: list[str] = []

    identity = devcard.identity
    display_name = identity.name or identity.username
    sections.append(f"# Hi, I'm {display_name}")

    # Bio
    if identity.bio:
        sections.append(identity.bio)

    # DevCard SVG embed
    if svg_content:
        sections.append(f"## DevCard\n\n{svg_content}")

    # Top languages
    if devcard.languages:
        lines = ["## Top Languages", ""]
        for lang in devcard.languages[:5]:
            lines.append(f"- {lang.name} ({lang.percentage:.1f}%)")
        sections.append("\n".join(lines))

    # Top projects
    if devcard.projects:
        lines = ["## Top Projects", ""]
        for proj in devcard.projects[:5]:
            desc = f" -- {proj.description}" if proj.description else ""
            stars_str = f" ({proj.stars} stars)" if proj.stars else ""
            lines.append(f"- **{proj.name}**{desc}{stars_str}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
