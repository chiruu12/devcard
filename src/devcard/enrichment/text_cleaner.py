"""Clean LLM output before storing in DevCard models."""
from __future__ import annotations

import re

_REPLACEMENTS: list[tuple[str, str]] = [
    ("—", "-"),
    ("–", "-"),
    ("‘", "'"),
    ("’", "'"),
    ("“", '"'),
    ("”", '"'),
    ("…", "..."),
    (" ", " "),
    ("​", ""),
    ("‍", ""),
    ("⁠", ""),
    ("﻿", ""),
]

_STRIP_RE = re.compile(
    r"\*{2,}"
    r"|#{1,3}\s"
    r"|`{1,3}",
)


def clean_llm_text(text: str) -> str:
    if not text:
        return text
    for old, new in _REPLACEMENTS:
        text = text.replace(old, new)
    text = _STRIP_RE.sub("", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()
