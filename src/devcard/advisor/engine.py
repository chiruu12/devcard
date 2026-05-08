from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

import yaml

from devcard.advisor.context import AdvisorContext
from devcard.advisor.models import AdvisorRule, Condition, ConditionOp
from devcard.models import Verdict

logger = logging.getLogger(__name__)

_RULES_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "mappings" / "advisor_rules.yaml"
)


def load_rules(path: Path | None = None) -> list[AdvisorRule]:
    """Load and parse advisor_rules.yaml into typed AdvisorRule models."""
    target = path or _RULES_PATH
    with open(target, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return [AdvisorRule.model_validate(r) for r in data.get("rules", [])]


def evaluate_condition(condition: Condition, context: AdvisorContext) -> bool:
    """Evaluate a single condition against context. Pure function."""
    ctx_value = getattr(context, condition.field, None)
    if ctx_value is None:
        return False
    match condition.operator:
        case ConditionOp.eq:
            return ctx_value == condition.value
        case ConditionOp.gt:
            return ctx_value > condition.value
        case ConditionOp.gte:
            return ctx_value >= condition.value
        case ConditionOp.lt:
            return ctx_value < condition.value
        case ConditionOp.lte:
            return ctx_value <= condition.value
        case ConditionOp.is_true:
            return bool(ctx_value) is True
        case ConditionOp.is_false:
            return bool(ctx_value) is False
    return False


def evaluate_rule(rule: AdvisorRule, context: AdvisorContext) -> Verdict | None:
    """Evaluate all conditions in a rule (AND logic). Returns Verdict if all match."""
    if not all(evaluate_condition(c, context) for c in rule.conditions):
        return None
    message = format_message(rule.message, context)
    action = format_message(rule.action, context) if rule.action else None
    return Verdict(
        category=rule.category.value,
        type=rule.type.value,
        message=message,
        action=action,
        severity=rule.severity.value if rule.severity else None,
    )


def evaluate_all_rules(rules: list[AdvisorRule], context: AdvisorContext) -> list[Verdict]:
    """Evaluate all rules, return list of matching verdicts."""
    verdicts: list[Verdict] = []
    for rule in rules:
        verdict = evaluate_rule(rule, context)
        if verdict is not None:
            verdicts.append(verdict)
    return verdicts


def format_message(template: str, context: AdvisorContext) -> str:
    """Replace {field} placeholders with context values."""
    ctx_dict = asdict(context)
    result = template
    for key, value in ctx_dict.items():
        placeholder = f"{{{key}}}"
        if placeholder in result:
            display = "N/A" if value is None else str(value)
            result = result.replace(placeholder, display)
    return result
