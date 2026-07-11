"""Turn features into per-dimension sub-scores (0-100) + coverage + reason codes."""
from __future__ import annotations

from ..domain.models import DimensionScore, FeatureVector
from .bands import primary_feature, scored_dimensions, subscore_for

NEUTRAL_SUBSCORE = 50.0  # used when a dimension has no evidence at all (missing != bad)


def _band_label(subscore: float) -> str:
    if subscore >= 75:
        return "strong"
    if subscore >= 55:
        return "fair"
    return "weak"


def score_dimensions(fv: FeatureVector) -> list[DimensionScore]:
    out: list[DimensionScore] = []
    for dim in scored_dimensions():
        feature = primary_feature(dim)
        value = fv.values[feature]
        coverage = fv.coverage[feature]
        if coverage <= 0.0:
            out.append(
                DimensionScore(dim, NEUTRAL_SUBSCORE, 0.0, [f"{dim}:insufficient_data"])
            )
            continue
        subscore, _band = subscore_for(dim, value)
        out.append(
            DimensionScore(dim, float(subscore), coverage, [f"{dim}:{_band_label(subscore)}"])
        )
    return out
