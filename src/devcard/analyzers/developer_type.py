from __future__ import annotations

from devcard.mappings import DEV_TYPE_RULES
from devcard.models import DevCard


def analyze_developer_type(devcard: DevCard) -> str:
    primary_lang = devcard.languages[0].name.lower() if devcard.languages else ""

    all_topics: set[str] = set()
    for project in devcard.projects:
        all_topics.update(t.lower() for t in project.topics)

    all_stack_names: set[str] = set()
    if devcard.stack:
        for field_name in (
            "frameworks", "libraries", "databases", "tools",
            "platforms", "ci_cd", "testing", "other",
        ):
            for item in getattr(devcard.stack, field_name, []):
                all_stack_names.add(item.name.lower())

    for rule in DEV_TYPE_RULES:
        conditions = rule.get("conditions", {})
        if not conditions:
            return rule.get("type", "full_stack")

        matched = True

        if "primary_language" in conditions:
            if primary_lang not in [v.lower() for v in conditions["primary_language"]]:
                matched = False

        if "topics_include_any" in conditions and matched:
            rule_topics = {t.lower() for t in conditions["topics_include_any"]}
            if not all_topics & rule_topics:
                matched = False

        if "stack_includes_any" in conditions and matched:
            rule_stack = {s.lower() for s in conditions["stack_includes_any"]}
            if not all_stack_names & rule_stack:
                matched = False

        if "language_ratio_above" in conditions and matched:
            lang_map = {lng.name.lower(): lng.percentage for lng in devcard.languages}
            any_above = any(
                lang_map.get(lang.lower(), 0) > threshold * 100
                for lang, threshold in conditions["language_ratio_above"].items()
            )
            if not any_above:
                matched = False

        if matched:
            return rule.get("type", "full_stack")

    return "full_stack"
