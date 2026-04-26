from __future__ import annotations

from devcard.models import DevCard
from devcard.output.curated import curate_for_agent


def to_toon(devcard: DevCard) -> str:
    from toon import encode

    return encode(curate_for_agent(devcard))
