"""Weighted additive scorecard -> Trust Score (0-1000) + tier.

score = round( (Σ wᵢ·subscoreᵢ) / Σ wᵢ · 10 )   with subscore in 0..100.
Dividing by Σ wᵢ (=95) is identical to renormalising the doc's integer weights to 100%,
with zero rounding error. Fraud is NOT here — it is an independent veto (see fraud/).
"""
from __future__ import annotations

from ..domain.enums import TrustTier
from ..domain.models import DimensionScore
from ..versioning import load_weights


def compute_trust_score(dimensions: list[DimensionScore], mode: str = "hand") -> tuple[int, TrustTier]:
    cfg = load_weights(mode)
    weights: dict[str, int] = cfg["weights"]
    weighted = sum(weights[d.dimension] * d.subscore for d in dimensions if d.dimension in weights)
    denom = sum(weights.values())
    score = round(weighted / denom * 10)

    tiers = cfg["tiers"]
    if score >= tiers["strong_min"]:
        tier = TrustTier.STRONG
    elif score >= tiers["moderate_min"]:
        tier = TrustTier.MODERATE
    else:
        tier = TrustTier.WEAK
    return score, tier
