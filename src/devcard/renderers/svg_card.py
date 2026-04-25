from __future__ import annotations

from xml.sax.saxutils import escape

from devcard.models import DevCard
from devcard.renderers.themes.base import Theme
from devcard.renderers.themes.default import THEME as DEFAULT_THEME

LINGUIST_COLORS: dict[str, str] = {
    "Assembly": "#6E4C13",
    "C": "#555555",
    "C#": "#178600",
    "C++": "#f34b7d",
    "CSS": "#563d7c",
    "Clojure": "#db5855",
    "Dart": "#00B4AB",
    "Elixir": "#6e4a7e",
    "Go": "#00ADD8",
    "HTML": "#e34c26",
    "Haskell": "#5e5086",
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "Jupyter Notebook": "#DA5B0B",
    "Kotlin": "#A97BFF",
    "Lua": "#000080",
    "Makefile": "#427819",
    "Objective-C": "#438eff",
    "PHP": "#4F5D95",
    "Perl": "#0298c3",
    "Python": "#3572A5",
    "R": "#198CE7",
    "Ruby": "#701516",
    "Rust": "#dea584",
    "Scala": "#c22d40",
    "Shell": "#89e051",
    "Swift": "#F05138",
    "TypeScript": "#3178c6",
    "Vue": "#41b883",
    "Zig": "#ec915c",
}


def _esc(text: str) -> str:
    return escape(text)


def render_svg(devcard: DevCard, theme: Theme | None = None) -> str:
    t = theme or DEFAULT_THEME
    sections: list[tuple[str, int]] = []
    y = t.card_padding

    header_svg, header_h = _section_header(devcard, t, y)
    sections.append((header_svg, header_h))
    y += header_h + 16

    if devcard.languages:
        lang_svg, lang_h = _section_languages(devcard, t, y)
        sections.append((lang_svg, lang_h))
        y += lang_h + 16

    if devcard.stack and _has_stack_items(devcard):
        stack_svg, stack_h = _section_stack(devcard, t, y)
        sections.append((stack_svg, stack_h))
        y += stack_h + 16

    if devcard.quality:
        qual_svg, qual_h = _section_quality(devcard, t, y)
        sections.append((qual_svg, qual_h))
        y += qual_h + 16

    if devcard.expertise and devcard.expertise.focus_areas:
        focus_svg, focus_h = _section_focus(devcard, t, y)
        sections.append((focus_svg, focus_h))
        y += focus_h + 16

    if devcard.projects:
        proj_svg, proj_h = _section_projects(devcard, t, y)
        sections.append((proj_svg, proj_h))
        y += proj_h + 16

    footer_svg, footer_h = _section_footer(devcard, t, y)
    sections.append((footer_svg, footer_h))
    y += footer_h

    total_h = y + t.card_padding
    w = t.card_width

    body = "\n".join(svg for svg, _ in sections)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{total_h}" viewBox="0 0 {w} {total_h}">
  <style>
    .header {{ font: 600 18px {t.font_family}; fill: {t.foreground}; }}
    .subheader {{ font: 400 14px {t.font_family}; fill: {t.secondary}; }}
    .body {{ font: 400 12px {t.font_family}; fill: {t.foreground}; }}
    .small {{ font: 400 11px {t.font_family}; fill: {t.secondary}; }}
    .label {{ font: 600 13px {t.font_family}; fill: {t.foreground}; }}
    .mono {{ font: 400 11px {t.font_mono}; fill: {t.secondary}; }}
    .accent {{ fill: {t.accent}; }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    .section {{ animation: fadeIn 0.3s ease-in; }}
  </style>
  <rect width="{w}" height="{total_h}" rx="{t.border_radius}" fill="{t.background}" stroke="{t.border}" stroke-width="1"/>
{body}
</svg>'''


def _section_header(devcard: DevCard, t: Theme, y: int) -> tuple[str, int]:
    ident = devcard.identity
    x = t.card_padding
    name = _esc(ident.name or ident.username)
    username = _esc(ident.username)

    initials = "".join(w[0].upper() for w in (ident.name or ident.username).split()[:2])

    parts = [f'  <g class="section" transform="translate({x}, {y})">']
    parts.append(
        f'    <circle cx="22" cy="22" r="22" fill="{t.accent}" opacity="0.15"/>'
    )
    parts.append(
        f'    <text x="22" y="27" text-anchor="middle" '
        f'style="font: 600 16px {t.font_family}; fill: {t.accent};">{_esc(initials)}</text>'
    )
    parts.append(f'    <text x="54" y="18" class="header">{name}</text>')
    parts.append(f'    <text x="54" y="36" class="subheader">@{username}</text>')

    h = 44
    if devcard.expertise and devcard.expertise.profile_type:
        badge = _esc(devcard.expertise.profile_type.replace("_", " ").title())
        parts.append(
            f'    <rect x="54" y="{h}" rx="8" ry="8" width="{len(badge) * 7 + 16}" '
            f'height="20" fill="{t.accent}" opacity="0.15"/>'
        )
        parts.append(
            f'    <text x="62" y="{h + 14}" '
            f'style="font: 600 11px {t.font_family}; fill: {t.accent};">{badge}</text>'
        )
        h += 28

    if ident.bio:
        bio = _esc(ident.bio[:80])
        parts.append(f'    <text x="0" y="{h + 14}" class="body">{bio}</text>')
        h += 22

    meta = []
    if ident.location:
        meta.append(ident.location)
    if ident.followers:
        meta.append(f"{ident.followers:,} followers")
    if meta:
        parts.append(
            f'    <text x="0" y="{h + 14}" class="small">{_esc(" · ".join(meta))}</text>'
        )
        h += 18

    parts.append("  </g>")
    return "\n".join(parts), h


def _section_languages(devcard: DevCard, t: Theme, y: int) -> tuple[str, int]:
    x = t.card_padding
    bar_w = t.card_width - 2 * t.card_padding
    parts = [f'  <g class="section" transform="translate({x}, {y})">']
    parts.append(f'    <text x="0" y="14" class="label">Languages</text>')

    bar_y = 24
    bar_x = 0
    for i, lang in enumerate(devcard.languages[:8]):
        w = max(lang.percentage / 100 * bar_w, 2)
        color = LINGUIST_COLORS.get(lang.name, t.bar_colors[i % len(t.bar_colors)])
        parts.append(
            f'    <rect x="{bar_x:.1f}" y="{bar_y}" width="{w:.1f}" height="8" '
            f'rx="1" fill="{color}"/>'
        )
        bar_x += w

    label_y = bar_y + 22
    lx = 0.0
    for i, lang in enumerate(devcard.languages[:6]):
        color = LINGUIST_COLORS.get(lang.name, t.bar_colors[i % len(t.bar_colors)])
        parts.append(f'    <circle cx="{lx + 5}" cy="{label_y}" r="4" fill="{color}"/>')
        parts.append(
            f'    <text x="{lx + 13}" y="{label_y + 4}" class="small">'
            f'{_esc(lang.name)} {lang.percentage:.1f}%</text>'
        )
        lx += len(lang.name) * 6.5 + 55

        if lx > bar_w - 60:
            lx = 0
            label_y += 16

    parts.append("  </g>")
    h = int(label_y - 24 + 24)
    return "\n".join(parts), h


def _has_stack_items(devcard: DevCard) -> bool:
    if devcard.stack is None:
        return False
    for field in ("frameworks", "libraries", "databases", "tools", "platforms", "ci_cd", "testing"):
        if getattr(devcard.stack, field):
            return True
    return False


def _section_stack(devcard: DevCard, t: Theme, y: int) -> tuple[str, int]:
    x = t.card_padding
    max_w = t.card_width - 2 * t.card_padding
    parts = [f'  <g class="section" transform="translate({x}, {y})">']
    parts.append(f'    <text x="0" y="14" class="label">Stack</text>')

    pill_y = 26
    pill_x = 0.0

    stack = devcard.stack
    if stack is None:
        parts.append("  </g>")
        return "\n".join(parts), 40

    all_items = []
    for field in ("frameworks", "libraries", "databases", "tools", "platforms", "ci_cd", "testing"):
        all_items.extend(getattr(stack, field, []))

    for item in all_items[:15]:
        name = item.name
        pw = len(name) * 7 + 16
        if pill_x + pw > max_w:
            pill_x = 0
            pill_y += 26

        parts.append(
            f'    <rect x="{pill_x:.1f}" y="{pill_y}" rx="10" ry="10" '
            f'width="{pw}" height="22" fill="{t.accent}" opacity="0.1"/>'
        )
        parts.append(
            f'    <text x="{pill_x + 8:.1f}" y="{pill_y + 15}" class="small">'
            f'{_esc(name)}</text>'
        )
        pill_x += pw + 6

    parts.append("  </g>")
    return "\n".join(parts), pill_y + 30


def _section_quality(devcard: DevCard, t: Theme, y: int) -> tuple[str, int]:
    x = t.card_padding
    q = devcard.quality
    if q is None:
        return "", 0

    parts = [f'  <g class="section" transform="translate({x}, {y})">']
    parts.append(f'    <text x="0" y="14" class="label">Quality Score: {q.score:.0%}</text>')

    bar_y = 26
    metrics = [
        ("Tests", q.test_adoption),
        ("CI/CD", q.ci_adoption),
        ("Docs", q.docs_adoption),
        ("License", q.license_adoption),
        ("Linter", q.linter_adoption),
    ]
    bar_w = 120
    for name, val in metrics:
        parts.append(
            f'    <text x="0" y="{bar_y + 10}" class="small">{name}</text>'
        )
        parts.append(
            f'    <rect x="55" y="{bar_y}" width="{bar_w}" height="12" '
            f'rx="3" fill="{t.border}"/>'
        )
        filled = val * bar_w
        color = "#3fb950" if val >= 0.7 else ("#d29922" if val >= 0.4 else "#f85149")
        parts.append(
            f'    <rect x="55" y="{bar_y}" width="{filled:.1f}" height="12" '
            f'rx="3" fill="{color}"/>'
        )
        parts.append(
            f'    <text x="{55 + bar_w + 8}" y="{bar_y + 10}" class="small">{val:.0%}</text>'
        )
        bar_y += 18

    parts.append("  </g>")
    return "\n".join(parts), bar_y + 4


def _section_focus(devcard: DevCard, t: Theme, y: int) -> tuple[str, int]:
    x = t.card_padding
    max_w = t.card_width - 2 * t.card_padding
    parts = [f'  <g class="section" transform="translate({x}, {y})">']
    parts.append(f'    <text x="0" y="14" class="label">Focus Areas</text>')

    tag_y = 26
    tag_x = 0.0
    if devcard.expertise is None:
        parts.append("  </g>")
        return "\n".join(parts), 40

    for area in devcard.expertise.focus_areas[:5]:
        name = area.name
        tw = len(name) * 7 + 16
        if tag_x + tw > max_w:
            tag_x = 0
            tag_y += 28

        parts.append(
            f'    <rect x="{tag_x:.1f}" y="{tag_y}" rx="12" ry="12" '
            f'width="{tw}" height="24" fill="{t.accent}" opacity="0.12"/>'
        )
        parts.append(
            f'    <text x="{tag_x + 8:.1f}" y="{tag_y + 16}" '
            f'style="font: 600 11px {t.font_family}; fill: {t.accent};">'
            f'{_esc(name)}</text>'
        )
        tag_x += tw + 8

    parts.append("  </g>")
    return "\n".join(parts), tag_y + 32


def _section_projects(devcard: DevCard, t: Theme, y: int) -> tuple[str, int]:
    x = t.card_padding
    parts = [f'  <g class="section" transform="translate({x}, {y})">']
    parts.append(f'    <text x="0" y="14" class="label">Top Projects</text>')

    row_y = 28
    for proj in devcard.projects[:5]:
        name = _esc(proj.name)
        stars = f"★ {proj.stars:,}" if proj.stars else ""
        lang = _esc(proj.language or "")

        parts.append(
            f'    <text x="0" y="{row_y + 12}" class="body">{name}</text>'
        )
        parts.append(
            f'    <text x="200" y="{row_y + 12}" class="small">{stars}</text>'
        )
        if lang:
            color = LINGUIST_COLORS.get(proj.language or "", t.secondary)
            parts.append(
                f'    <circle cx="270" cy="{row_y + 8}" r="4" fill="{color}"/>'
            )
            parts.append(
                f'    <text x="278" y="{row_y + 12}" class="small">{lang}</text>'
            )
        row_y += 22

    parts.append("  </g>")
    return "\n".join(parts), row_y + 4


def _section_footer(devcard: DevCard, t: Theme, y: int) -> tuple[str, int]:
    x = t.card_padding
    ts = devcard.generated_at.strftime("%Y-%m-%d")
    parts = [f'  <g class="section" transform="translate({x}, {y})">']
    parts.append(
        f'    <text x="0" y="14" class="mono">'
        f'Generated by devcard · {ts}</text>'
    )
    parts.append("  </g>")
    return "\n".join(parts), 20
