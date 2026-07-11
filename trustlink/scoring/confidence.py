"""Confidence = how much we trust the score, driven by data sufficiency (not by the score).

confidence = breadth_weight * breadth + (1 - breadth_weight) * consistency
  breadth     = mean per-dimension coverage         (how much evidence do we see?)
  consistency = 1 - normalised cashflow volatility   (how clean is what we see?)

This operationalises "missing != bad": a thin file lowers breadth, but if the observed
cashflow is clean, consistency keeps confidence high.
"""
from __future__ import annotations

from datetime import date
from statistics import mean, pstdev

from ..domain.models import Application, Borrower, DimensionScore, Transaction
from ..versioning import load_weights
from ..features.functions import FeatureContext, _in_window, _is_outflow, _monthly_sums


def cashflow_consistency(
    borrower: Borrower, application: Application, events, as_of: date, window_months: int
) -> float:
    ctx = FeatureContext(borrower, application, tuple(events), as_of, window_months)
    monthly = [amt for _, amt in _monthly_sums(_in_window(ctx), _is_outflow)]
    if len(monthly) < 2:
        return 1.0  # nothing volatile observed
    m = mean(monthly)
    cv = (pstdev(monthly) / m) if m else 0.0
    return max(0.0, min(1.0, 1.0 - cv))


def compute_confidence(dimensions: list[DimensionScore], consistency: float) -> float:
    breadth_weight = float(load_weights()["confidence"]["breadth_weight"])
    breadth = mean([d.coverage for d in dimensions]) if dimensions else 0.0
    value = breadth_weight * breadth + (1.0 - breadth_weight) * consistency
    return round(max(0.0, min(1.0, value)), 2)
