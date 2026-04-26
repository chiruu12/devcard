from __future__ import annotations

from io import StringIO

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from devcard.models import DevCard


def render_compare(card1: DevCard, card2: DevCard) -> str:
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=100)

    console.print(Panel(
        f"[bold]{card1.identity.username}[/] vs [bold]{card2.identity.username}[/]",
        title="DevCard Compare",
        border_style="blue",
    ))

    _compare_identity(console, card1, card2)
    _compare_languages(console, card1, card2)
    _compare_stack(console, card1, card2)
    _compare_expertise(console, card1, card2)
    _compare_quality(console, card1, card2)
    _compare_activity(console, card1, card2)
    _compare_projects(console, card1, card2)

    return buf.getvalue()


def _compare_identity(console: Console, c1: DevCard, c2: DevCard) -> None:
    table = Table(show_header=True, border_style="dim")
    table.add_column("", style="bold")
    table.add_column(c1.identity.username)
    table.add_column(c2.identity.username)

    t1 = (c1.expertise.profile_type or "—") if c1.expertise else "—"
    t2 = (c2.expertise.profile_type or "—") if c2.expertise else "—"
    table.add_row("Type", t1.replace("_", " ").title(), t2.replace("_", " ").title())

    f1 = f"{c1.identity.followers:,}" if c1.identity.followers else "0"
    f2 = f"{c2.identity.followers:,}" if c2.identity.followers else "0"
    table.add_row("Followers", f1, f2)

    r1 = str(c1.identity.public_repos)
    r2 = str(c2.identity.public_repos)
    table.add_row("Public repos", r1, r2)

    console.print(table)


def _compare_languages(console: Console, c1: DevCard, c2: DevCard) -> None:
    all_langs = set()
    l1 = {lang.name: lang.percentage for lang in c1.languages}
    l2 = {lang.name: lang.percentage for lang in c2.languages}
    all_langs.update(l1.keys())
    all_langs.update(l2.keys())

    if not all_langs:
        return

    table = Table(title="Languages", border_style="green")
    table.add_column("Language", style="bold")
    table.add_column(c1.identity.username, justify="right")
    table.add_column(c2.identity.username, justify="right")
    table.add_column("Shared")

    sorted_langs = sorted(
        all_langs,
        key=lambda n: max(l1.get(n, 0), l2.get(n, 0)),
        reverse=True,
    )
    for name in sorted_langs[:8]:
        p1 = f"{l1[name]:.1f}%" if name in l1 else "—"
        p2 = f"{l2[name]:.1f}%" if name in l2 else "—"
        shared = "✓" if name in l1 and name in l2 else ""
        table.add_row(name, p1, p2, shared)

    console.print(table)


def _truncated_list(items: list[str], limit: int) -> str:
    if len(items) <= limit:
        return ", ".join(items)
    return f"{', '.join(items[:limit])} (+{len(items) - limit} more)"


def _get_stack_names(devcard: DevCard) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    if not devcard.stack:
        return result
    for field, label in [
        ("frameworks", "Frameworks"), ("libraries", "Libraries"),
        ("databases", "Databases"), ("tools", "Tools"),
        ("platforms", "Platforms"), ("ci_cd", "CI/CD"), ("testing", "Testing"),
        ("other", "Other"),
    ]:
        items = getattr(devcard.stack, field, [])
        if items:
            result[label] = {item.name for item in items}
    return result


def _compare_stack(console: Console, c1: DevCard, c2: DevCard) -> None:
    s1_all = set()
    s2_all = set()
    for names in _get_stack_names(c1).values():
        s1_all |= names
    for names in _get_stack_names(c2).values():
        s2_all |= names

    if not s1_all and not s2_all:
        return

    shared = sorted(s1_all & s2_all)
    only1 = sorted(s1_all - s2_all)
    only2 = sorted(s2_all - s1_all)

    lines: list[str] = []
    if shared:
        lines.append(f"[bold green]Shared:[/] {_truncated_list(shared, 10)}")
    if only1:
        lines.append(f"[bold]{c1.identity.username} only:[/] {_truncated_list(only1, 10)}")
    if only2:
        lines.append(f"[bold]{c2.identity.username} only:[/] {_truncated_list(only2, 10)}")

    if lines:
        console.print(Panel("\n".join(lines), title="Stack Overlap", border_style="yellow"))


def _compare_expertise(console: Console, c1: DevCard, c2: DevCard) -> None:
    d1 = {d.name: d for d in (c1.expertise.domains if c1.expertise else [])}
    d2 = {d.name: d for d in (c2.expertise.domains if c2.expertise else [])}
    all_domains = set(d1.keys()) | set(d2.keys())

    if not all_domains:
        return

    table = Table(title="Expertise", border_style="cyan")
    table.add_column("Domain", style="bold")
    table.add_column(c1.identity.username, justify="right")
    table.add_column(c2.identity.username, justify="right")

    sorted_domains = sorted(
        all_domains,
        key=lambda n: max(
            d1[n].confidence if n in d1 else 0,
            d2[n].confidence if n in d2 else 0,
        ),
        reverse=True,
    )
    for name in sorted_domains[:6]:
        v1 = f"{d1[name].confidence:.0%}" if name in d1 else "—"
        v2 = f"{d2[name].confidence:.0%}" if name in d2 else "—"
        table.add_row(name, v1, v2)

    console.print(table)


def _compare_quality(console: Console, c1: DevCard, c2: DevCard) -> None:
    q1 = c1.quality
    q2 = c2.quality
    if not q1 and not q2:
        return

    table = Table(title="Quality", border_style="magenta")
    table.add_column("Metric", style="bold")
    table.add_column(c1.identity.username, justify="right")
    table.add_column(c2.identity.username, justify="right")

    metrics = [
        ("Score", lambda q: f"{q.score:.0%}" if q else "—"),
        ("Tests", lambda q: f"{q.test_adoption:.0%}" if q else "—"),
        ("CI/CD", lambda q: f"{q.ci_adoption:.0%}" if q else "—"),
        ("Docs", lambda q: f"{q.docs_adoption:.0%}" if q else "—"),
        ("License", lambda q: f"{q.license_adoption:.0%}" if q else "—"),
    ]
    for name, fn in metrics:
        table.add_row(name, fn(q1), fn(q2))

    console.print(table)


def _compare_activity(console: Console, c1: DevCard, c2: DevCard) -> None:
    a1 = c1.activity
    a2 = c2.activity
    if not a1 and not a2:
        return

    table = Table(title="Activity", border_style="green")
    table.add_column("", style="bold")
    table.add_column(c1.identity.username)
    table.add_column(c2.identity.username)

    s1 = a1.status.upper() if a1 else "—"
    s2 = a2.status.upper() if a2 else "—"
    table.add_row("Status", s1, s2)

    c1_val = f"~{a1.commits_last_year:,}" if a1 and a1.commits_last_year else "—"
    c2_val = f"~{a2.commits_last_year:,}" if a2 and a2.commits_last_year else "—"
    table.add_row("Commits/year", c1_val, c2_val)

    cs1 = str(a1.consistency_score) if a1 and a1.consistency_score is not None else "—"
    cs2 = str(a2.consistency_score) if a2 and a2.consistency_score is not None else "—"
    table.add_row("Consistency", cs1, cs2)

    console.print(table)


def _compare_projects(console: Console, c1: DevCard, c2: DevCard) -> None:
    if not c1.projects and not c2.projects:
        return

    left_lines = []
    for p in c1.projects[:3]:
        sig = "★ " if p.is_signature else ""
        left_lines.append(f"{sig}{p.name} ({p.stars:,}⭐)")
    right_lines = []
    for p in c2.projects[:3]:
        sig = "★ " if p.is_signature else ""
        right_lines.append(f"{sig}{p.name} ({p.stars:,}⭐)")

    left_panel = Panel(
        "\n".join(left_lines) or "No projects",
        title=c1.identity.username,
        border_style="blue",
    )
    right_panel = Panel(
        "\n".join(right_lines) or "No projects",
        title=c2.identity.username,
        border_style="blue",
    )
    console.print(Columns([left_panel, right_panel], equal=True))
