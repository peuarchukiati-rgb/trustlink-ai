"""#6 — the validation harness must show the engine discriminates risk (on synthetic data)."""
from trustlink.validation.run import run_validation


def test_engine_discriminates_default_risk():
    r = run_validation(n=800, seed=42)
    assert r["auc"] > 0.60          # fair discrimination or better
    assert r["ks"] > 0.15
    # Trust tiers must be risk-ordered: Strong defaults less than Moderate less than Weak
    t = r["tiers"]
    rate = lambda name: t[name]["bad"] / t[name]["n"]
    assert rate("Strong") < rate("Moderate") < rate("Weak")


def test_fraud_veto_catches_over_declared():
    r = run_validation(n=800, seed=42)
    assert r["fraud_total"] > 0
    assert r["fraud_caught"] == r["fraud_total"]


def test_validation_is_deterministic():
    a = run_validation(n=300, seed=5)
    b = run_validation(n=300, seed=5)
    assert a["auc"] == b["auc"]
    assert a["default_rate"] == b["default_rate"]
