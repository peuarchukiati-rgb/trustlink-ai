"""Deterministic explanation layer: reason codes + evidence -> human-readable factors.

This is the ONLY place narrative is produced, and it is 100% deterministic (a template over
concrete evidence). An LLM could later replace THIS module behind the same interface — it must
never compute the score. The scoring/fraud/decision layers do not import this module.
"""
from __future__ import annotations

from ..domain.enums import Category, FraudLevel, TransactionType
from ..domain.models import Borrower, DimensionScore, Transaction

MAX_POSITIVE_FACTORS = 4  # demo/report cap; keeps the underwriter view focused


def _subscore(dimensions: list[DimensionScore], name: str) -> float:
    for d in dimensions:
        if d.dimension == name:
            return d.subscore
    return 0.0


def _has_on_time(events, category: Category) -> bool:
    return any(
        t.transaction_type == TransactionType.PAYMENT and t.category == category and t.on_time
        for t in events
    )


def build_factors(
    borrower: Borrower,
    dimensions: list[DimensionScore],
    events,
    consistency: float,
    fraud_level: FraudLevel,
    corroboration=None,
) -> tuple[list[str], list[str]]:
    positive: list[str] = []
    if _subscore(dimensions, "income_stability") >= 70:
        positive.append("Stable monthly inflow")
    if _has_on_time(events, Category.INSURANCE):
        positive.append("Regular insurance payment")
    if _has_on_time(events, Category.UTILITY):
        positive.append("Consistent utility payment")
    # approved-partner corroboration (pay-slip / national data centre) — only when supplied (#8)
    if corroboration is not None and getattr(corroboration, "corroborated", False):
        names = " & ".join(s.name for s in corroboration.sources if s.agrees)
        positive.append(f"Income corroborated by {names}")
    if consistency >= 0.90:
        positive.append("Low spending volatility")
    if _subscore(dimensions, "savings_behaviour") >= 80:
        positive.append("Healthy savings behaviour")
    if _subscore(dimensions, "identity_trust") >= 80:
        positive.append("Verified identity (eKYC)")
    positive = positive[:MAX_POSITIVE_FACTORS]

    risk: list[str] = []
    if corroboration is not None and getattr(corroboration, "conflict", False):
        risk.append("Declared income conflicts with partner records")
    # Thin file is NOT listed as a risk — by design it lowers confidence, not the score.
    if borrower.employment_type.strip().lower() == "freelancer" and \
            _subscore(dimensions, "income_stability") < 80:
        risk.append("Freelance income varies month to month")
    if fraud_level != FraudLevel.LOW:
        risk.append("Elevated fraud signals detected")
    if _subscore(dimensions, "savings_behaviour") <= 50:
        risk.append("Low or negative savings")
    if _subscore(dimensions, "payment_discipline") < 60:
        risk.append("Missed or inconsistent payments")

    return positive, risk
