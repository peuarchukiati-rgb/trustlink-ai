"""The anchor test: Ms. Aom must reproduce the numbers used across every design document."""
from trustlink.data.generator import load
from trustlink.data.personas import ALL_PERSONAS
from trustlink.engine import run_pipeline


def _aom():
    borrower, application, events = load("APP001")
    return run_pipeline(borrower, application, events, ALL_PERSONAS["APP001"].as_of)


def test_aom_trust_score_and_tier():
    r = _aom()
    assert r.trust_score == 742
    assert r.trust_tier == "Strong"


def test_aom_confidence():
    assert _aom().confidence_level == 0.86


def test_aom_fraud_low():
    assert _aom().fraud_level == "Low"


def test_aom_decision():
    r = _aom()
    assert r.ai_recommendation == "Approve with adjusted amount"
    assert r.suggested_amount == 45_000_000
    assert r.suggested_tenor_months == 12
    assert r.requires_human_review is True


def test_aom_factors_exact():
    r = _aom()
    assert r.positive_factors == [
        "Stable monthly inflow",
        "Regular insurance payment",
        "Consistent utility payment",
        "Low spending volatility",
    ]
    assert r.risk_factors == ["Freelance income varies month to month"]


def test_aom_dimension_subscores():
    subs = {d.dimension: int(d.subscore) for d in _aom().dimensions}
    assert subs == {
        "income_stability": 70,
        "payment_discipline": 88,
        "savings_behaviour": 80,
        "financial_trend": 52,
        "lifestyle_stability": 76,
        "identity_trust": 80,
    }


def test_aom_trust_score_payload_shape():
    # matches Volume 8 POST /trust-score
    payload = _aom().trust_score_payload()
    assert set(payload) == {
        "application_id", "trust_score", "trust_tier",
        "confidence_level", "positive_factors", "risk_factors",
    }
    assert payload["application_id"] == "APP001"
