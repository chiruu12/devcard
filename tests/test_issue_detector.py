from __future__ import annotations

from datetime import UTC, datetime

from devcard.analyzers.issue_detector import detect_issues
from devcard.models import (
    DevCard,
    Generator,
    Identity,
    Issue,
    ProfileRepoData,
    Project,
    Quality,
)


def _make_devcard(**overrides) -> DevCard:
    defaults = dict(
        generated_at=datetime.now(UTC),
        generator=Generator(name="test", version="0.0.1"),
        identity=Identity(username="testuser"),
    )
    defaults.update(overrides)
    return DevCard(**defaults)


class TestIssueDetector:
    def test_missing_bio_detected(self):
        card = _make_devcard(identity=Identity(username="u", bio=None))
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "missing_bio" in types

    def test_bio_present_no_issue(self):
        card = _make_devcard(identity=Identity(username="u", bio="I code"))
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "missing_bio" not in types

    def test_missing_profile_readme(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_profile_readme=False)
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "missing_profile_readme" in types

    def test_missing_descriptions(self):
        card = _make_devcard(
            projects=[
                Project(name="a", description=None),
                Project(name="b", description=None),
                Project(name="c", description="Has a description"),
            ],
        )
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        desc_issues = [i for i in issues if i.type == "missing_descriptions"]
        assert len(desc_issues) == 1
        assert sorted(desc_issues[0].repos) == ["a", "b"]
        assert "c" not in desc_issues[0].repos

    def test_missing_topics(self):
        card = _make_devcard(
            projects=[
                Project(name="no-topics", topics=[]),
                Project(name="has-topics", topics=["python", "cli"]),
            ],
        )
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        topic_issues = [i for i in issues if i.type == "missing_topics"]
        assert len(topic_issues) == 1
        assert "no-topics" in topic_issues[0].repos
        assert "has-topics" not in topic_issues[0].repos

    def test_missing_licenses(self):
        card = _make_devcard(quality=Quality(license_adoption=0.3))
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "missing_licenses" in types

    def test_no_devcard_json(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_devcard_json=False)
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "no_devcard_json" in types

    def test_no_llms_txt(self):
        card = _make_devcard()
        profile = ProfileRepoData(has_llms_txt=False)
        issues = detect_issues(card, profile)
        types = [i.type for i in issues]
        assert "no_llms_txt" in types

    def test_perfect_profile_no_issues(self):
        card = _make_devcard(
            identity=Identity(username="u", bio="Full-stack dev"),
            projects=[
                Project(name="proj", description="Great project", topics=["python"]),
            ],
            quality=Quality(license_adoption=0.8, docs_adoption=0.8),
        )
        profile = ProfileRepoData(
            has_profile_readme=True,
            has_devcard_json=True,
            has_llms_txt=True,
        )
        issues = detect_issues(card, profile)
        assert len(issues) == 0

    def test_returns_list_of_issue_models(self):
        card = _make_devcard()
        profile = ProfileRepoData()
        issues = detect_issues(card, profile)
        assert len(issues) > 0
        for issue in issues:
            assert isinstance(issue, Issue)
            assert issue.severity in ("high", "medium", "low")

    def test_severity_ordering(self):
        card = _make_devcard(
            identity=Identity(username="u", bio=None),
            projects=[
                Project(name="no-desc"),
            ],
            quality=Quality(license_adoption=0.2),
        )
        profile = ProfileRepoData(
            has_profile_readme=False,
            has_devcard_json=False,
            has_llms_txt=False,
        )
        issues = detect_issues(card, profile)
        severity_order = {"high": 0, "medium": 1, "low": 2}
        severity_values = [severity_order[i.severity] for i in issues]
        assert severity_values == sorted(severity_values)
