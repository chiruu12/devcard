from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

for rel_path in ("src", "devcard-mcp/src"):
    path = str(ROOT / rel_path)
    if path not in sys.path:
        sys.path.insert(0, path)
