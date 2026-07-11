"""API path: parse an applicant .md, run the real engine, map to the console's render shape."""
import os

import pytest

from trustlink.api.mapper import to_render
from trustlink.engine import run_pipeline
from trustlink.ioutil.md_parser import parse_applicant

APPLICANTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "applicants")


def _score(name, mode="hand"):
    with open(os.path.join(APPLICANTS, name), encoding="utf-8") as fh:
        borrower, app, events, as_of = parse_applicant(fh.read())
    return to_render(run_pipeline(borrower, app, events, as_of, mode), borrower, mode)


def test_api_parses_and_scores_aom():
    r = _score("aom.md")
    assert r["score"] == 742
    assert r["cls"] == "ok" and r["recKey"] == "rec_approve_adjusted"
    assert r["base"]["d"] == "REJECT"           # the money shot survives the API path
    assert r["pos"] == ["stable_inflow", "reg_insurance", "consistent_utility", "low_volatility"]
    assert r["risk"] == ["freelance_var"]
    assert r["suggested"] == 45_000_000 and abs(r["dsr"] - 0.223) < 0.01


def test_api_calibrated_mode():
    assert _score("aom.md", "calibrated")["score"] == 739


def test_api_parser_rejects_malformed():
    with pytest.raises(ValueError):
        parse_applicant("just some text, no sections")
