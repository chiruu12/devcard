from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Theme:
    name: str
    background: str
    foreground: str
    secondary: str
    accent: str
    border: str
    border_radius: int = 10
    font_family: str = '"Segoe UI", Ubuntu, "Helvetica Neue", sans-serif'
    font_mono: str = '"SF Mono", "Cascadia Code", Consolas, monospace'
    bar_colors: list[str] = field(default_factory=lambda: [
        "#3572A5", "#f1e05a", "#3178c6", "#e34c26", "#555555",
        "#89e051", "#f34b7d", "#DA5B0B", "#0298c3", "#427819",
    ])
    card_width: int = 495
    card_padding: int = 25
