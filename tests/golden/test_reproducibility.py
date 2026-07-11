"""Same input + same versions => identical result, and versions are recorded in the snapshot."""
from trustlink.data.generator import load
from trustlink.data.personas import ALL_PERSONAS
from trustlink.engine import run_pipeline
from trustlink.versioning import config_versions


def _run():
    borrower, application, events = load("APP001")
    return run_pipeline(borrower, application, events, ALL_PERSONAS["APP001"].as_of)


def test_two_runs_are_identical():
    a, b = _run(), _run()
    assert a.trust_score == b.trust_score
    assert a.confidence_level == b.confidence_level
    assert a.ai_recommendation == b.ai_recommendation
    assert a.snapshot == b.snapshot           # includes input hash + feature values + versions


def test_snapshot_records_versions_and_hash():
    snap = _run().snapshot
    assert snap["versions"] == config_versions()
    assert len(snap["input_hash"]) == 16
    assert "income_stability_index" in snap["feature_values"]
