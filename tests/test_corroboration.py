"""#8 — approved-partner income corroboration (pay-slip / national data centre).

Corroboration must lift confidence when a source agrees, raise a fraud flag when one materially
conflicts, and never change the Trust Score or penalise a borrower who supplies no source.
"""
import os
from dataclasses import replace

from trustlink.engine import run_pipeline
from trustlink.ioutil.md_parser import parse_applicant

APPLICANTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "applicants")


def _load(name):
    with open(os.path.join(APPLICANTS, name), encoding="utf-8") as fh:
        return parse_applicant(fh.read())


def _run(borrower, app, events, as_of):
    return run_pipeline(borrower, app, events, as_of)


def test_agreeing_sources_lift_confidence_not_score():
    b, app, e, as_of = _load("minh.md")
    with_corr = _run(b, app, e, as_of)
    without = _run(replace(b, payslip_monthly_income=None, registry_monthly_income=None),
                   app, e, as_of)
    # score is identical (corroboration never enters the weighted Trust Score)...
    assert with_corr.trust_score == without.trust_score
    # ...but confidence is higher, and the corroboration is recorded + explained
    assert with_corr.confidence_level > without.confidence_level
    assert with_corr.corroboration["corroborated"] is True
    assert any("corroborated" in p.lower() for p in with_corr.positive_factors)


def test_missing_sources_are_never_penalised():
    b, app, e, as_of = _load("aom.md")   # Aom supplies no pay-slip / registry
    r = _run(b, app, e, as_of)
    assert r.trust_score == 742          # the anchor is untouched
    assert r.corroboration["corroborated"] is False
    assert r.corroboration["conflict"] is False


def test_material_conflict_raises_fraud():
    b, app, e, as_of = _load("minh.md")
    # pay-slip far above the ~20M observed inflow -> a material conflict
    r = _run(replace(b, payslip_monthly_income=40_000_000), app, e, as_of)
    assert r.corroboration["conflict"] is True
    assert r.fraud_level == "High"
    assert "Declared income conflicts with partner records" in r.risk_factors
