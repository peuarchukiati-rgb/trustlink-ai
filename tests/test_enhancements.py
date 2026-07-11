"""Tests for the hackathon-extra features #2–#5, #7."""
from datetime import date

from trustlink.decision.affordability import assess
from trustlink.domain.enums import Category, FraudLevel, TransactionType
from trustlink.domain.models import Application, Borrower, FraudFlag, Transaction
from trustlink.fraud.rules import evaluate
from trustlink.fraud.veto import fraud_level, fraud_score
from trustlink.data.generator import load
from trustlink.data.personas import ALL_PERSONAS
from trustlink.engine import run_pipeline
from trustlink.validation.calibrate import run_calibration
from trustlink.validation.run import run_validation

AS_OF = date(2026, 6, 30)


def _income_events(inflows):
    ev = []
    for m, inf in enumerate(inflows, start=1):
        ev.append(Transaction(f"I{m}", "A", date(2026, m, 1), TransactionType.INCOME, Category.OTHER, inf))
    return ev


def _app():
    return Application("A", "B", 40_000_000, "x", 12)


# ---------- #2 fraud scoring ----------
def test_fraud_score_combines_weak_signals():
    # three sub-High flags: max() would call this Medium; the additive score escalates to High
    flags = [FraudFlag("a", FraudLevel.MEDIUM, ""), FraudFlag("b", FraudLevel.MEDIUM, ""),
             FraudFlag("c", FraudLevel.LOW, "")]
    assert fraud_score(flags) == 65
    assert fraud_level(flags) == FraudLevel.HIGH
    assert all(f.severity != FraudLevel.HIGH for f in flags)


def test_single_high_is_high_and_low_is_low():
    assert fraud_level([FraudFlag("x", FraudLevel.HIGH, "")]) == FraudLevel.HIGH
    assert fraud_level([FraudFlag("x", FraudLevel.LOW, "")]) == FraudLevel.LOW
    assert fraud_level([]) == FraudLevel.LOW


# ---------- #3 extra checks ----------
def test_occupation_income_norm_flags_absurd_declared():
    b = Borrower("B", "x", "Salaried", "Teacher", 300_000_000, "thin", True, 0)  # teacher declaring 300M
    flags = evaluate(b, _app(), _income_events([300_000_000] * 6), AS_OF, 6)
    assert any(f.rule == "occupation_income_norm" for f in flags)


def test_new_account_flags():
    b = Borrower("B", "x", "Salaried", "Teacher", 20_000_000, "thin", True, 0, account_age_months=1)
    flags = evaluate(b, _app(), _income_events([20_000_000] * 6), AS_OF, 6)
    assert any(f.rule == "new_account" for f in flags)


# ---------- #4 DSR affordability ----------
def test_dsr_binds_when_existing_debt_is_high():
    app = Application("A", "B", 100_000_000, "x", 12)
    no_debt = assess(app, 20_000_000, 8_000_000, existing_debt=0)
    with_debt = assess(app, 20_000_000, 8_000_000, existing_debt=7_000_000)
    assert with_debt.suggested_amount < no_debt.suggested_amount
    assert with_debt.binding == "dsr"
    assert with_debt.dsr <= 0.46


def test_dsr_backward_compatible_no_debt():
    # Ms. Aom's cashflow, no existing debt -> surplus still binds at 45M (unchanged)
    app = Application("APP001", "B001", 50_000_000, "x", 12)
    a = assess(app, 18_500_000, 12_200_000, existing_debt=0)
    assert a.suggested_amount == 45_000_000
    assert 0.20 <= a.dsr <= 0.25


# ---------- #5 data calibration ----------
def test_calibration_runs_and_is_interpretable():
    r = run_calibration(n=500, seed=42)
    assert 0.4 < r["auc_hand"] < 1.0
    assert 0.4 < r["auc_model"] < 1.0
    imp = {x["dimension"]: x["data_pct"] for x in r["importance"]}
    assert imp["identity_trust"] < 5.0          # constant feature -> ~0 importance
    assert abs(sum(imp.values()) - 100.0) < 1.0


def test_calibration_deterministic():
    assert run_calibration(300, 7)["auc_model"] == run_calibration(300, 7)["auc_model"]


# ---------- #5 calibrated mode in the engine ----------
def test_calibrated_mode_runs_and_hand_is_unchanged():
    b, a, e = load("APP001")
    as_of = ALL_PERSONAS["APP001"].as_of
    hand = run_pipeline(b, a, e, as_of, "hand")
    cal = run_pipeline(b, a, e, as_of, "calibrated")
    assert hand.trust_score == 742                    # default mode preserves the anchor
    assert cal.trust_score != 742
    assert 700 < cal.trust_score < 780                # data-learned weights land Aom in the same range


# ---------- #7 fairness ----------
def test_fairness_metric_present():
    r = run_validation(n=400, seed=42)
    assert 0.0 <= r["disparate_impact"] <= 1.0
    assert len(r["groups"]) >= 3
