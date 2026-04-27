from __future__ import annotations

from devcard.models import DevCard
from devcard.output.json_output import to_json


def prepare_devcard_files(devcard: DevCard, theme: str = "default") -> dict[str, str]:
    """Prepare files for deploying. Returns {filename: content}.

    Currently returns devcard.json only. SVG can be added later.
    """
    return {"devcard.json": to_json(devcard)}
