"""Fraud aggregation (#2): a graduated fraud SCORE, not just the single worst flag.

Each flag contributes points by severity; the level is derived from the total. This catches
"several small red flags that add up" — which a plain max() misses — while a single High-severity
flag (e.g. fund parking, big income mismatch) still forces High on its own.

    Low = 15 · Medium = 25 · High = 60 points
    score >= 60 -> High   ·   score >= 25 -> Medium   ·   else Low
"""
from __future__ import annotations

from ..domain.enums import FraudLevel
from ..domain.models import FraudFlag

POINTS = {FraudLevel.LOW: 15, FraudLevel.MEDIUM: 25, FraudLevel.HIGH: 60}
HIGH_MIN = 60
MEDIUM_MIN = 25


def fraud_score(flags: list[FraudFlag]) -> int:
    return sum(POINTS.get(f.severity, 0) for f in flags)


def fraud_level(flags: list[FraudFlag]) -> FraudLevel:
    s = fraud_score(flags)
    if s >= HIGH_MIN:
        return FraudLevel.HIGH
    if s >= MEDIUM_MIN:
        return FraudLevel.MEDIUM
    return FraudLevel.LOW
