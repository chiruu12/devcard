from __future__ import annotations

from devcard.models import DevCard


def analyze_contribution_style(devcard: DevCard) -> str:
    collab = devcard.collaboration
    if collab is None:
        return "solo_builder"

    external = collab.external_contributions
    prs = collab.pull_requests_opened
    orgs = len(collab.organizations)

    total_stars = sum(p.stars for p in devcard.projects)
    num_projects = len(devcard.projects)

    if num_projects > 3 and total_stars > 100 and external < 5:
        return "maintainer"

    if external > 10 or (prs > 5 and orgs > 2):
        return "contributor"

    if num_projects > 0 and external < 3 and orgs <= 1:
        return "solo_builder"

    return "explorer"
