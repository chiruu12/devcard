from __future__ import annotations

import json

from devcard.models import DevCard


def to_json(devcard: DevCard) -> str:
    data = json.loads(devcard.model_dump_json(exclude_none=True))
    data["$schema"] = "https://devcard.dev/schema/v1"
    ordered = {"$schema": data.pop("$schema")}
    ordered.update(data)
    return json.dumps(ordered, indent=2)
