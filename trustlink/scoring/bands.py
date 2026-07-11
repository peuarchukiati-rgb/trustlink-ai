"""Band lookup: map a feature value to a 0-100 dimension sub-score."""
from __future__ import annotations

from ..versioning import load_bands


def scored_dimensions() -> list[str]:
    return list(load_bands()["dimensions"].keys())


def primary_feature(dimension: str) -> str:
    return load_bands()["dimensions"][dimension]["feature"]


def subscore_for(dimension: str, value: float) -> tuple[int, dict]:
    cfg = load_bands()["dimensions"][dimension]
    for band in cfg["bands"]:
        if band["min"] <= value < band["max"]:
            return int(band["subscore"]), band
    # value at/above the top sentinel -> top band; otherwise the lowest.
    top = cfg["bands"][0]
    if value >= top["max"]:
        return int(top["subscore"]), top
    last = cfg["bands"][-1]
    return int(last["subscore"]), last
