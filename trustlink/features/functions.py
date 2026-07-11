"""The behavioural feature functions (Trust Intelligence Engine note, section 9).

Every function is PURE and POINT-IN-TIME CORRECT: it reads only events dated on/before
`ctx.as_of` and returns ``(value, coverage)``. ``coverage`` (0..1) captures how much evidence
backs the value; missingness lands only here, never in ``value`` — so a thin file is never
silently penalised (it surfaces as lower confidence instead).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean, median, pstdev

from ..domain.enums import (
    DISCRETIONARY_CATEGORIES,
    ESSENTIAL_CATEGORIES,
    RECURRING_CATEGORIES,
    Category,
    TransactionType,
)
from ..domain.models import Application, Borrower, Transaction


@dataclass(frozen=True)
class FeatureContext:
    borrower: Borrower
    application: Application
    events: tuple[Transaction, ...]
    as_of: date
    window_months: int


# --------------------------------------------------------------------------- helpers
def _window_month_keys(as_of: date, n: int) -> set[tuple[int, int]]:
    keys: set[tuple[int, int]] = set()
    y, m = as_of.year, as_of.month
    for _ in range(n):
        keys.add((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return keys


def _in_window(ctx: FeatureContext) -> list[Transaction]:
    keys = _window_month_keys(ctx.as_of, ctx.window_months)
    return [
        e for e in ctx.events
        if e.transaction_date <= ctx.as_of
        and (e.transaction_date.year, e.transaction_date.month) in keys
    ]


def _monthly_sums(txns: list[Transaction], predicate) -> list[tuple[tuple[int, int], int]]:
    """Chronologically ordered [(month_key, summed_amount)] for months that have matching txns."""
    buckets: dict[tuple[int, int], int] = {}
    for t in txns:
        if predicate(t):
            key = (t.transaction_date.year, t.transaction_date.month)
            buckets[key] = buckets.get(key, 0) + t.amount
    return sorted(buckets.items())


def _cov(observed_months: int, ideal_months: int) -> float:
    if ideal_months <= 0:
        return 1.0
    return min(1.0, observed_months / ideal_months)


def _is_income(t: Transaction) -> bool:
    return t.transaction_type == TransactionType.INCOME


def _is_outflow(t: Transaction) -> bool:
    return t.transaction_type in (TransactionType.EXPENSE, TransactionType.PAYMENT)


# --------------------------------------------------------------------------- features
def income_stability_index(ctx: FeatureContext, ideal_months: int) -> tuple[float, float]:
    txns = _in_window(ctx)
    monthly = [amt for _, amt in _monthly_sums(txns, _is_income)]
    cov = _cov(len(monthly), ideal_months)
    if len(monthly) < 2:
        return 0.60, cov  # neutral value; low coverage flags the thin evidence
    m = mean(monthly)
    cv = (pstdev(monthly) / m) if m else 1.0
    return max(0.0, min(1.0, 1.0 - cv)), cov


def saving_ratio(ctx: FeatureContext, ideal_months: int) -> tuple[float, float]:
    txns = _in_window(ctx)
    inflow = [amt for _, amt in _monthly_sums(txns, _is_income)]
    outflow = [amt for _, amt in _monthly_sums(txns, _is_outflow)]
    cov = _cov(min(len(inflow), len(outflow)) if outflow else len(inflow), ideal_months)
    if not inflow:
        return 0.0, cov
    avg_in = mean(inflow)
    avg_out = mean(outflow) if outflow else 0.0
    return max(-1.0, min(1.0, (avg_in - avg_out) / avg_in)), cov


def payment_consistency(ctx: FeatureContext, ideal_months: int) -> tuple[float, float]:
    txns = _in_window(ctx)
    payments = [
        t for t in txns
        if t.transaction_type == TransactionType.PAYMENT and t.category in RECURRING_CATEGORIES
    ]
    months = {(t.transaction_date.year, t.transaction_date.month) for t in payments}
    cov = _cov(len(months), ideal_months)
    if not payments:
        return 0.60, cov  # no recurring commitments observed -> neutral, low coverage
    on_time = sum(1 for t in payments if t.on_time)
    return on_time / len(payments), cov


def income_growth_rate(ctx: FeatureContext, ideal_months: int) -> tuple[float, float]:
    txns = _in_window(ctx)
    monthly = [amt for _, amt in _monthly_sums(txns, _is_income)]
    cov = _cov(len(monthly), ideal_months)
    if len(monthly) < 2:
        return 0.0, cov
    half = len(monthly) // 2
    first = mean(monthly[:half])
    second = mean(monthly[half:])
    if first == 0:
        return 0.0, cov
    return max(-1.0, min(1.0, (second - first) / first)), cov


def lifestyle_stability_index(ctx: FeatureContext, ideal_months: int) -> tuple[float, float]:
    txns = _in_window(ctx)
    spend = [t for t in txns if _is_outflow(t)]
    months = {(t.transaction_date.year, t.transaction_date.month) for t in spend}
    cov = _cov(len(months), ideal_months)
    total = sum(t.amount for t in spend)
    if total == 0:
        return 0.60, cov
    essential = sum(t.amount for t in spend if t.category in ESSENTIAL_CATEGORIES)
    # essential-spend ratio; a healthy balance sits high but not at the extreme.
    return max(0.0, min(1.0, essential / total)), cov


def median_daily_balance(ctx: FeatureContext, ideal_months: int) -> tuple[float, float]:
    """MEDIAN of a reconstructed daily balance series (median resists parked-cash gaming)."""
    txns = sorted(_in_window(ctx), key=lambda t: t.transaction_date)
    months = {(t.transaction_date.year, t.transaction_date.month) for t in txns}
    cov = _cov(len(months), ideal_months)
    if not txns:
        return 0.0, cov
    # running end-of-day balance from a zero opening, sampled per active day
    daily: dict[date, int] = {}
    bal = 0
    for t in txns:
        bal += t.amount if _is_income(t) else -t.amount
        daily[t.transaction_date] = bal
    return float(median(daily.values())), cov


def expense_diversity(ctx: FeatureContext, ideal_months: int) -> tuple[float, float]:
    """Simpson-style diversity of spend across categories: 1 - sum(share^2)."""
    txns = _in_window(ctx)
    spend = [t for t in txns if _is_outflow(t)]
    months = {(t.transaction_date.year, t.transaction_date.month) for t in spend}
    cov = _cov(len(months), ideal_months)
    total = sum(t.amount for t in spend)
    if total == 0:
        return 0.0, cov
    by_cat: dict[Category, int] = {}
    for t in spend:
        by_cat[t.category] = by_cat.get(t.category, 0) + t.amount
    return 1.0 - sum((v / total) ** 2 for v in by_cat.values()), cov


def identity_confidence(ctx: FeatureContext, ideal_months: int) -> tuple[float, float]:
    """KYC-derived. VALUE = strength of the identity signal; COVERAGE = corroborating breadth.

    For a thin file these differ: eKYC gives a strong *value*, but with only one data source
    the *coverage* stays modest (which lowers confidence, not the score).
    """
    b = ctx.borrower
    sources = {t.source for t in _in_window(ctx)}
    value = 0.80 if b.ekyc_verified else 0.40
    coverage = (0.50 if b.ekyc_verified else 0.20) + 0.20 * min(len(sources), 2)
    return value, min(1.0, coverage)


# name -> function registry (compute.py dispatches by feature name)
REGISTRY = {
    "income_stability_index": income_stability_index,
    "saving_ratio": saving_ratio,
    "payment_consistency": payment_consistency,
    "income_growth_rate": income_growth_rate,
    "lifestyle_stability_index": lifestyle_stability_index,
    "median_daily_balance": median_daily_balance,
    "expense_diversity": expense_diversity,
    "identity_confidence": identity_confidence,
}
