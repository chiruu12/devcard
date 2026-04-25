from __future__ import annotations

import yaml

from devcard.models import DevCard


def to_yaml(devcard: DevCard) -> str:
    data = devcard.model_dump(exclude_none=True, mode="json")
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
