from __future__ import annotations

from datetime import UTC, datetime

from devcard.advisor.context import AdvisorContext, build_context
from devcard.advisor.engine import (
    evaluate_all_rules,
    evaluate_condition,
    evaluate_rule,
    format_message,
    load_rules,
)
from devcard.advisor.models import (
    AdvisorCategory,
    AdvisorRule,
    Condition,
    ConditionOp,
    Severity,
    VerdictType,
)
from devcard.models import (
    Activity,
    CodingHabits,
    Collaboration,
    CommitQuality,
    DevCard,
    Generator,
    Identity,
    LinesChanged,
    NotableContribution,
    Quality,
    ReadmeDepth,
    ReviewActivity,
)


def _minimal_devcard(**kwargs):
    return DevCard(
        generated_at=datetime.now(UTC),
        generator=Generator(name="test", version="0.1"),
        identity=Identity(username="testdev", **kwargs),
    )


def _default_context(**overrides) -> AdvisorContext:
    """Build an AdvisorContext with sensible defaults, overriding specific fields."""
    defaults = dict(
        bio_empty=False,
        followers=10,
        public_repos=5,
        has_blog=False,
        has_twitter=False,
        hireable=False,
        activity_status="moderate",
        consistency_score=50,
        commits_last_year=100,
        quality_score=0.5,
        ci_adoption=0.5,
        test_adoption=0.5,
        docs_adoption=0.5,
        linter_adoption=0.5,
        avg_message_length=40.0,
        conventional_commits_pct=30.0,
        multiline_pct=20.0,
        readme_avg_word_count=150.0,
        has_code_blocks_pct=50.0,
        has_install_section_pct=50.0,
        has_images_pct=30.0,
        reviews_given=3,
        notable_count=0,
        orgs_count=1,
        external_contributions=2,
        total_lines_added=5000,
        total_lines_deleted=2000,
        indentation="spaces",
        avg_line_length=60.0,
        human_score=50,
        agent_score=40,
    )
    defaults.update(overrides)
    return AdvisorContext(**defaults)


class TestBuildContext:
    def test_build_context_from_full_devcard(self):
        card = DevCard(
            generated_at=datetime.now(UTC),
            generator=Generator(name="test", version="0.1"),
            identity=Identity(
                username="fulldev",
                bio="I build things",
                followers=200,
                public_repos=30,
                blog="https://example.com",
                twitter_username="fulldev",
                hireable=True,
            ),
            activity=Activity(
                status="active",
                consistency_score=75,
                commits_last_year=500,
            ),
            quality=Quality(
                score=0.8,
                ci_adoption=0.7,
                test_adoption=0.6,
                docs_adoption=0.9,
                linter_adoption=0.5,
            ),
            commit_quality=CommitQuality(
                avg_message_length=55.0,
                conventional_commits_pct=70.0,
                multiline_pct=40.0,
            ),
            readme_depth=ReadmeDepth(
                avg_word_count=300.0,
                has_code_blocks_pct=80.0,
                has_install_section_pct=60.0,
                has_images_pct=25.0,
            ),
            collaboration=Collaboration(
                organizations=["org1", "org2"],
                external_contributions=10,
                notable_contributions=[
                    NotableContribution(
                        repo="big/project",
                        repo_stars=5000,
                        contribution_type="pull_request",
                        count=3,
                        url="https://github.com/big/project",
                    ),
                ],
                review_activity=ReviewActivity(reviews_given=15),
            ),
            lines_changed=LinesChanged(total_added=20000, total_deleted=8000),
            coding_habits=CodingHabits(indentation="spaces", avg_line_length=72.5),
        )

        ctx = build_context(card, human_score=80, agent_score=65)

        assert ctx.bio_empty is False
        assert ctx.followers == 200
        assert ctx.public_repos == 30
        assert ctx.has_blog is True
        assert ctx.has_twitter is True
        assert ctx.hireable is True
        assert ctx.activity_status == "active"
        assert ctx.consistency_score == 75
        assert ctx.commits_last_year == 500
        assert ctx.quality_score == 0.8
        assert ctx.ci_adoption == 0.7
        assert ctx.test_adoption == 0.6
        assert ctx.docs_adoption == 0.9
        assert ctx.linter_adoption == 0.5
        assert ctx.avg_message_length == 55.0
        assert ctx.conventional_commits_pct == 70.0
        assert ctx.multiline_pct == 40.0
        assert ctx.readme_avg_word_count == 300.0
        assert ctx.has_code_blocks_pct == 80.0
        assert ctx.has_install_section_pct == 60.0
        assert ctx.has_images_pct == 25.0
        assert ctx.reviews_given == 15
        assert ctx.notable_count == 1
        assert ctx.orgs_count == 2
        assert ctx.external_contributions == 10
        assert ctx.total_lines_added == 20000
        assert ctx.total_lines_deleted == 8000
        assert ctx.indentation == "spaces"
        assert ctx.avg_line_length == 72.5
        assert ctx.human_score == 80
        assert ctx.agent_score == 65

    def test_build_context_handles_missing_data(self):
        card = _minimal_devcard()
        ctx = build_context(card, human_score=0, agent_score=0)

        assert ctx.bio_empty is True
        assert ctx.followers == 0
        assert ctx.public_repos == 0
        assert ctx.has_blog is False
        assert ctx.has_twitter is False
        assert ctx.hireable is False
        assert ctx.activity_status == "dormant"
        assert ctx.consistency_score == 0
        assert ctx.commits_last_year == 0
        assert ctx.quality_score == 0.0
        assert ctx.ci_adoption == 0.0
        assert ctx.test_adoption == 0.0
        assert ctx.docs_adoption == 0.0
        assert ctx.linter_adoption == 0.0
        assert ctx.avg_message_length == 0.0
        assert ctx.conventional_commits_pct == 0.0
        assert ctx.multiline_pct == 0.0
        assert ctx.readme_avg_word_count == 0.0
        assert ctx.has_code_blocks_pct == 0.0
        assert ctx.has_install_section_pct == 0.0
        assert ctx.has_images_pct == 0.0
        assert ctx.reviews_given == 0
        assert ctx.notable_count == 0
        assert ctx.orgs_count == 0
        assert ctx.external_contributions == 0
        assert ctx.total_lines_added == 0
        assert ctx.total_lines_deleted == 0
        assert ctx.indentation == "unknown"
        assert ctx.avg_line_length == 0.0
        assert ctx.human_score == 0
        assert ctx.agent_score == 0


class TestEvaluateCondition:
    def test_condition_eq(self):
        ctx = _default_context(activity_status="dormant")
        cond = Condition(field="activity_status", operator=ConditionOp.eq, value="dormant")
        assert evaluate_condition(cond, ctx) is True

        cond_no = Condition(field="activity_status", operator=ConditionOp.eq, value="active")
        assert evaluate_condition(cond_no, ctx) is False

    def test_condition_gt(self):
        ctx = _default_context(followers=100)
        cond = Condition(field="followers", operator=ConditionOp.gt, value=50)
        assert evaluate_condition(cond, ctx) is True

        cond_eq = Condition(field="followers", operator=ConditionOp.gt, value=100)
        assert evaluate_condition(cond_eq, ctx) is False

    def test_condition_gte(self):
        ctx = _default_context(followers=50)
        cond_eq = Condition(field="followers", operator=ConditionOp.gte, value=50)
        assert evaluate_condition(cond_eq, ctx) is True

        cond_above = Condition(field="followers", operator=ConditionOp.gte, value=51)
        assert evaluate_condition(cond_above, ctx) is False

    def test_condition_is_true(self):
        ctx = _default_context(bio_empty=True)
        cond = Condition(field="bio_empty", operator=ConditionOp.is_true)
        assert evaluate_condition(cond, ctx) is True

        ctx_false = _default_context(bio_empty=False)
        assert evaluate_condition(cond, ctx_false) is False

    def test_condition_is_false(self):
        ctx = _default_context(has_blog=False)
        cond = Condition(field="has_blog", operator=ConditionOp.is_false)
        assert evaluate_condition(cond, ctx) is True

        ctx_true = _default_context(has_blog=True)
        assert evaluate_condition(cond, ctx_true) is False


class TestEvaluateRule:
    def test_rule_all_conditions_must_match(self):
        """Rule with 2 conditions where only 1 matches returns None."""
        rule = AdvisorRule(
            category=AdvisorCategory.profile,
            conditions=[
                Condition(field="bio_empty", operator=ConditionOp.is_true),
                Condition(field="followers", operator=ConditionOp.gte, value=500),
            ],
            type=VerdictType.suggestion,
            severity=Severity.medium,
            message="Bio is empty but you have followers.",
        )
        # bio_empty=True matches, but followers=10 < 500 does not
        ctx = _default_context(bio_empty=True, followers=10)
        assert evaluate_rule(rule, ctx) is None

    def test_rule_returns_verdict_when_all_match(self):
        """Rule where all conditions match returns a Verdict."""
        rule = AdvisorRule(
            category=AdvisorCategory.activity,
            conditions=[
                Condition(field="activity_status", operator=ConditionOp.eq, value="active"),
                Condition(field="consistency_score", operator=ConditionOp.gte, value=70),
            ],
            type=VerdictType.praise,
            severity=Severity.info,
            message="Active and consistent developer.",
            action="Keep it up.",
        )
        ctx = _default_context(activity_status="active", consistency_score=80)
        verdict = evaluate_rule(rule, ctx)

        assert verdict is not None
        assert verdict.category == "activity"
        assert verdict.type == "praise"
        assert verdict.message == "Active and consistent developer."
        assert verdict.action == "Keep it up."
        assert verdict.severity == "info"


class TestEvaluateAllRules:
    def test_evaluate_all_rules_filters_matching(self):
        """Mix of matching and non-matching rules — only matching ones returned."""
        rule_match = AdvisorRule(
            category=AdvisorCategory.profile,
            conditions=[
                Condition(field="bio_empty", operator=ConditionOp.is_true),
            ],
            type=VerdictType.critique,
            severity=Severity.high,
            message="Bio is empty.",
        )
        rule_no_match = AdvisorRule(
            category=AdvisorCategory.repos,
            conditions=[
                Condition(field="public_repos", operator=ConditionOp.eq, value=0),
            ],
            type=VerdictType.critique,
            severity=Severity.high,
            message="No repos.",
        )
        rule_match2 = AdvisorRule(
            category=AdvisorCategory.collaboration,
            conditions=[
                Condition(field="reviews_given", operator=ConditionOp.gte, value=3),
            ],
            type=VerdictType.praise,
            severity=Severity.info,
            message="Good reviewer.",
        )

        ctx = _default_context(bio_empty=True, public_repos=5, reviews_given=5)
        verdicts = evaluate_all_rules([rule_match, rule_no_match, rule_match2], ctx)

        assert len(verdicts) == 2
        assert verdicts[0].category == "profile"
        assert verdicts[1].category == "collaboration"


class TestFormatMessage:
    def test_format_message_replaces_placeholders(self):
        ctx = _default_context(followers=250, public_repos=42)
        template = "You have {followers} followers and {public_repos} public repos."
        result = format_message(template, ctx)
        assert result == "You have 250 followers and 42 public repos."


class TestLoadRules:
    def test_load_rules_parses_yaml(self):
        """Loads actual advisor_rules.yaml and returns list of AdvisorRule."""
        rules = load_rules()
        assert len(rules) > 0
        assert all(isinstance(r, AdvisorRule) for r in rules)
        # Verify structure of first rule
        first = rules[0]
        assert first.category in AdvisorCategory.__members__.values()
        assert len(first.conditions) > 0
        assert first.message
