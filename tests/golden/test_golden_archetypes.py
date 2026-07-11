"""Archetypes B/C/D pin the Approve / Human-Review / Reject paths, plus the money shot."""
import pytest

from trustlink.baseline.traditional import score as baseline_score
from trustlink.data.generator import load
from trustlink.data.personas import ALL_PERSONAS
from trustlink.engine import run_pipeline


def _run(app):
    borrower, application, events = load(app)
    result = run_pipeline(borrower, application, events, ALL_PERSONAS[app].as_of)
    return borrower, result


@pytest.mark.parametrize(
    "app,recommendation,fraud",
    [
        ("APP002", "Approve", "Low"),
        ("APP003", "Human Review", "Medium"),
        ("APP004", "Reject / Request more info", "High"),
    ],
)
def test_archetype_routing(app, recommendation, fraud):
    _b, r = _run(app)
    assert r.ai_recommendation == recommendation
    assert r.fraud_level == fraud


def test_money_shot_thin_file_rejected_by_bureau_but_approved_by_tie():
    borrower, result = _run("APP001")
    base = baseline_score(borrower)
    assert base.decision == "REJECT"          # bureau cannot score a thin file
    assert base.score is None
    assert result.ai_recommendation.lower().startswith("approve")  # TIE approves on behaviour


def test_high_risk_rejected_amount_zero():
    _b, r = _run("APP004")
    assert r.suggested_amount == 0
