from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

MAPS_PATH = Path("data/maps.json")


@lru_cache(maxsize=1)
def load_map_names() -> dict[int, str | None]:
    if not MAPS_PATH.exists():
        return {}
    raw = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    return {int(key): value for key, value in raw.items()}


def format_map_name(map_id: int | None) -> str:
    if map_id is None:
        return "N/A"
    name = load_map_names().get(map_id)
    return name or f"地图 #{map_id}"
