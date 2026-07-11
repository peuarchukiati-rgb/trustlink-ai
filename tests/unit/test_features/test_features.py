"""Feature-layer unit tests: point-in-time correctness, coverage, anti-gaming."""
from datetime import date

from trustlink.data.generator import load
from trustlink.data.personas import ALL_PERSONAS
from trustlink.domain.enums import Category, TransactionType
from trustlink.domain.models import Transaction
from trustlink.features.compute import compute_features
from trustlink.features.functions import (
    FeatureContext,
    income_stability_index,
    median_daily_balance,
)


def _aom_ctx(as_of=None):
    borrower, application, events = load("APP001")
    as_of = as_of or ALL_PERSONAS["APP001"].as_of
    return FeatureContext(borrower, application, tuple(events), as_of, 6)


def test_point_in_time_ignores_future_events():
    """An event dated after as_of must not change any feature value."""
    borrower, application, events = load("APP001")
    as_of = ALL_PERSONAS["APP001"].as_of
    base = compute_features(borrower, application, events, as_of)

    future = Transaction(
        transaction_id="FUTURE",
        application_id="APP001",
        transaction_date=date(2026, 12, 1),   # after as_of
        transaction_type=TransactionType.INCOME,
        category=Category.OTHER,
        amount=999_000_000,
    )
    with_future = compute_features(borrower, application, list(events) + [future], as_of)
    assert with_future.values == base.values


def test_coverage_between_zero_and_one():
    fv = compute_features(*load("APP001"), ALL_PERSONAS["APP001"].as_of)
    assert all(0.0 <= c <= 1.0 for c in fv.coverage.values())


def test_income_stability_in_unit_range():
    value, coverage = income_stability_index(_aom_ctx(), 9)
    assert 0.0 <= value <= 1.0
    assert 0.0 < coverage <= 1.0


def test_median_daily_balance_resists_single_spike():
    """Parking a huge one-day balance must not move the MEDIAN (anti-gaming)."""
    borrower, application, events = load("APP001")
    base, _ = median_daily_balance(_aom_ctx(), 6)

    spike = Transaction(
        transaction_id="SPIKE",
        application_id="APP001",
        transaction_date=date(2026, 6, 15),
        transaction_type=TransactionType.INCOME,
        category=Category.OTHER,
        amount=5_000_000_000,   # absurd one-day parked cash
    )
    ctx = FeatureContext(borrower, application, tuple(list(events) + [spike]), date(2026, 6, 30), 6)
    gamed, _ = median_daily_balance(ctx, 6)
    # a mean would explode; the median barely moves
    assert abs(gamed - base) < base * 0.5 + 1
