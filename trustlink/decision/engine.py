"""Decision layer: combine Trust Score + fraud veto + affordability into a recommendation.

Thresholds are the Volume 5 decision bands. Fraud can only ever make the outcome MORE
conservative (veto), never less.
"""
from __future__ import annotations

from ..domain.enums import FraudLevel, TrustTier
from ..domain.models import Affordability, Application, Decision
from ..versioning import load_weights


def decide(
    application: Application,
    trust_score: int,
    tier: TrustTier,
    fraud_level: FraudLevel,
    affordability: Affordability,
    confidence: float,
) -> Decision:
    tiers = load_weights()["tiers"]
    strong_min = tiers["strong_min"]
    moderate_min = tiers["moderate_min"]

    if fraud_level == FraudLevel.HIGH or trust_score < moderate_min:
        recommendation = "Reject / Request more info"
    elif fraud_level == FraudLevel.MEDIUM or trust_score < strong_min:
        recommendation = "Human Review"
    else:  # score >= strong_min and fraud Low
        recommendation = "Approve with adjusted amount" if affordability.adjusted else "Approve"

    requires_human_review = (
        affordability.adjusted
        or fraud_level != FraudLevel.LOW
        or trust_score < strong_min
    )
    return Decision(
        application_id=application.application_id,
        ai_recommendation=recommendation,
        suggested_amount=affordability.suggested_amount,
        suggested_tenor_months=affordability.suggested_tenor_months,
        decision_confidence=confidence,
        requires_human_review=requires_human_review,
    )
