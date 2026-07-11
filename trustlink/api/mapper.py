"""Map a PipelineResult into the exact JSON shape the console's render() expects.

This lets the same front-end render results whether they are computed in-browser (fallback) or by
the real Python engine over the API — no changes to render().
"""
from __future__ import annotations

from statistics import mean

from ..baseline.traditional import score as baseline_score
from ..domain.models import Borrower, PipelineResult
from ..versioning import load_weights

_POS = {
    "Stable monthly inflow": "stable_inflow", "Regular insurance payment": "reg_insurance",
    "Consistent utility payment": "consistent_utility", "Low spending volatility": "low_volatility",
    "Healthy savings behaviour": "healthy_savings", "Verified identity (eKYC)": "verified_id",
}
_RISK = {
    "Freelance income varies month to month": "freelance_var",
    "Elevated fraud signals detected": "fraud_signals",
    "Low or negative savings": "low_savings", "Missed or inconsistent payments": "missed_payments",
}


def _cls_and_key(recommendation: str) -> tuple[str, str]:
    r = recommendation.lower()
    if r.startswith("approve"):
        return "ok", ("rec_approve_adjusted" if "adjust" in r else "rec_approve")
    if r.startswith("human"):
        return "warn", "rec_review"
    return "bad", "rec_reject"


def to_render(result: PipelineResult, borrower: Borrower, mode: str = "hand") -> dict:
    weights = load_weights(mode)["weights"]
    sum_w = sum(weights.values()) or 1
    dims = [
        {
            "dim": d.dimension, "sub": int(d.subscore), "cov": round(d.coverage, 2),
            "w": weights.get(d.dimension, 0),
            "contrib": round(weights.get(d.dimension, 0) * d.subscore / sum_w * 10),
        }
        for d in result.dimensions
    ]
    breadth = round(mean(d.coverage for d in result.dimensions), 4) if result.dimensions else 0.0
    cls, rec_key = _cls_and_key(result.ai_recommendation)
    base = baseline_score(borrower)
    return {
        "score": result.trust_score, "tier": result.trust_tier,
        "confidence": round(result.confidence_level, 2), "breadth": breadth,
        "fraud": result.fraud_level, "fpts": result.fraud_score, "dsr": result.dsr,
        "dims": dims,
        "pos": [_POS[p] for p in result.positive_factors if p in _POS],
        "risk": [_RISK[r] for r in result.risk_factors if r in _RISK],
        "cls": cls, "recKey": rec_key, "review": result.requires_human_review,
        "suggested": result.suggested_amount, "maxP": result.max_principal,
        "avgIn": result.avg_inflow, "avgOut": result.avg_outflow, "surplus": result.surplus,
        "base": {"d": base.decision},
        "_backend": "api", "_mode": mode,
    }
