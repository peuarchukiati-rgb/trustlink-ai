"""Scoring / fraud / affordability / decision unit tests."""
import pytest

from trustlink.decision.affordability import assess
from trustlink.domain.enums import FraudLevel, TrustTier
from trustlink.domain.models import Application, DimensionScore
from trustlink.fraud.veto import fraud_level
from trustlink.domain.models import FraudFlag
from trustlink.scoring.bands import subscore_for
from trustlink.scoring.scorecard import compute_trust_score


def _dim(name, sub, cov=1.0):
    return DimensionScore(name, float(sub), cov, [])


def test_scorecard_weight_math_hits_742():
    dims = [
        _dim("income_stability", 70),
        _dim("payment_discipline", 88),
        _dim("savings_behaviour", 80),
        _dim("financial_trend", 52),
        _dim("lifestyle_stability", 76),
        _dim("identity_trust", 80),
    ]
    score, tier = compute_trust_score(dims)
    assert score == 742
    assert tier == TrustTier.STRONG


def test_tier_boundaries():
    all80 = [_dim(n, 80) for n in (
        "income_stability", "payment_discipline", "savings_behaviour",
        "financial_trend", "lifestyle_stability", "identity_trust")]
    score, tier = compute_trust_score(all80)
    assert score == 800 and tier == TrustTier.STRONG


def test_band_lookup_boundaries():
    # income_stability bands: [0.75,0.86)->70 ; [0.86,..]->82
    assert subscore_for("income_stability", 0.75)[0] == 70
    assert subscore_for("income_stability", 0.859)[0] == 70
    assert subscore_for("income_stability", 0.86)[0] == 82


def test_affordability_adjusts_aom_50m_to_45m():
    app = Application("APP001", "B001", 50_000_000, "x", 12)
    a = assess(app, avg_inflow=18_500_000, avg_outflow=12_200_000)
    assert a.surplus == 6_300_000
    assert a.max_principal == 45_000_000
    assert a.suggested_amount == 45_000_000
    assert a.adjusted is True


def test_affordability_does_not_adjust_when_within_capacity():
    app = Application("APP002", "B002", 40_000_000, "x", 12)
    a = assess(app, avg_inflow=30_000_000, avg_outflow=18_000_000)
    assert a.suggested_amount == 40_000_000
    assert a.adjusted is False


def test_fraud_level_is_max_severity():
    assert fraud_level([]) == FraudLevel.LOW
    flags = [
        FraudFlag("a", FraudLevel.LOW, ""),
        FraudFlag("b", FraudLevel.MEDIUM, ""),
    ]
    assert fraud_level(flags) == FraudLevel.MEDIUM
