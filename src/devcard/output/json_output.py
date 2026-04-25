from __future__ import annotations

import json

from devcard.models import DevCard


def to_json(devcard: DevCard) -> str:
    data = devcard.model_dump(exclude_none=True, mode="json")
    ordered = {"$schema": "https://devcard.dev/schema/v1"}
    ordered.update(data)
    return json.dumps(ordered, indent=2)
