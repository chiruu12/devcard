from __future__ import annotations

from devcard.models import DevCard


def compute_quality_score(devcard: DevCard) -> None:
    if devcard.quality is None:
        return

    q = devcard.quality
    q.score = round(
        q.test_adoption * 0.3
        + q.ci_adoption * 0.25
        + q.docs_adoption * 0.2
        + q.license_adoption * 0.15
        + q.linter_adoption * 0.1,
        3,
    )
