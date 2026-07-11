"""Regulatory-sandbox surface: approved-partner gating + scoped consent + audit trail.

These call the endpoint functions directly (like test_api.py) so no HTTP client is required.
"""
import json
import os

import pytest
from fastapi import HTTPException

from trustlink.api import app as A
from trustlink.partners import get_partner, is_approved, list_partners

APPLICANTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "applicants")
_MD = open(os.path.join(APPLICANTS, "minh.md"), encoding="utf-8").read()
_AOM = open(os.path.join(APPLICANTS, "aom.md"), encoding="utf-8").read()


def _body(resp):
    return json.loads(bytes(resp.body))


# --------------------------------------------------------------------------- partners
def test_registry_marks_approval():
    assert is_approved("mock_open_banking")
    assert is_approved("payroll_partner")
    assert not is_approved("unlisted_scraper")
    assert get_partner("does_not_exist") is None
    assert {p.partner_id for p in list_partners(approved_only=True)} == {
        "mock_open_banking", "payroll_partner", "national_data_centre",
    }


# --------------------------------------------------------------------------- consent
def test_score_auto_grants_implicit_consent_and_keeps_console_working():
    r = _body(A.score(A.ScoreRequest(md=_MD)))          # console posts only {md}
    assert r["score"] == 789
    assert r["provenance"]["consent"]["implicit"] is True
    assert r["provenance"]["partner"]["partner_id"] == "mock_open_banking"
    assert r["provenance"]["corroboration"]["corroborated"] is True


def test_explicit_consent_must_cover_partner_scopes():
    ok = A.grant_consent(A.ConsentRequest(scopes=["open_banking:read", "payslip:read"]))
    assert _body(A.score(A.ScoreRequest(
        md=_MD, partner_id="payroll_partner", consent_id=ok["consent_id"]))) ["score"] == 789

    lacking = A.grant_consent(A.ConsentRequest(scopes=["open_banking:read"]))
    with pytest.raises(HTTPException) as exc:
        A.score(A.ScoreRequest(md=_MD, partner_id="payroll_partner", consent_id=lacking["consent_id"]))
    assert exc.value.status_code == 403


def test_unapproved_partner_is_refused():
    with pytest.raises(HTTPException) as exc:
        A.score(A.ScoreRequest(md=_MD, partner_id="unlisted_scraper"))
    assert exc.value.status_code == 403


def test_revoked_consent_blocks_scoring():
    c = A.grant_consent(A.ConsentRequest(scopes=["open_banking:read", "payslip:read"]))
    A.revoke_consent(c["consent_id"])
    with pytest.raises(HTTPException) as exc:
        A.score(A.ScoreRequest(md=_MD, partner_id="payroll_partner", consent_id=c["consent_id"]))
    assert exc.value.status_code == 403


def test_unknown_consent_is_404():
    with pytest.raises(HTTPException) as exc:
        A.score(A.ScoreRequest(md=_MD, consent_id="cs_doesnotexist"))
    assert exc.value.status_code == 404


# --------------------------------------------------------------------------- audit
def test_score_appends_reproducible_audit_entry():
    before = len(A.audit()["entries"])
    r = _body(A.score(A.ScoreRequest(md=_AOM)))
    entries = A.audit()["entries"]
    assert len(entries) == before + 1
    last = entries[-1]
    assert last["action"] == "score"
    # the audit carries the engine's input fingerprint + versions -> reproducible & attributable
    assert last["detail"]["input_hash"] == r["provenance"]["input_hash"]
    assert last["detail"]["trust_score"] == 742
    assert "versions" in last["detail"]
