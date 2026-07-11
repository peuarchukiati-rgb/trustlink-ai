"""TrustLink API — real end-to-end backend.

The Python engine (the authoritative one) runs server-side; the console posts an applicant .md and
renders what the engine returns. Run:

    pip install -r requirements.txt          # includes fastapi, uvicorn
    uvicorn trustlink.api.app:app --reload   # then open http://127.0.0.1:8000

Endpoints:
    GET  /                          -> the console (served from webdemo/)
    GET  /api/health                -> {status, engine_version}
    GET  /api/samples               -> list of built-in applicant files
    GET  /api/samples/{id}          -> the raw .md text for one applicant
    GET  /api/partners              -> approved fintech partners in the sandbox (P4)
    POST /api/consent               -> grant a scoped, revocable data-use consent
    GET  /api/consent/{id}          -> fetch a consent record
    POST /api/consent/{id}/revoke   -> revoke a consent
    GET  /api/audit                 -> the immutable scoring audit trail
    POST /api/score  {md, mode, ..} -> render-ready result (real engine) + provenance
"""
from __future__ import annotations

import glob
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ..engine import run_pipeline
from ..ioutil.md_parser import parse_applicant
from ..partners import DEFAULT_PARTNER_ID, get_partner, list_partners
from ..versioning import ENGINE_VERSION
from .audit import AUDIT, CONSENT
from .mapper import to_render

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))          # .../trustlink
_WEBDEMO = os.path.join(_ROOT, "webdemo")
_APPLICANTS = os.path.join(_ROOT, "applicants")

app = FastAPI(title="TrustLink API", version=ENGINE_VERSION)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class ScoreRequest(BaseModel):
    md: str
    mode: str = "hand"
    partner_id: str = DEFAULT_PARTNER_ID     # which approved partner supplied the data
    consent_id: Optional[str] = None         # explicit consent; if absent, an implicit demo consent
    borrower_ref: Optional[str] = None
    purpose: str = "credit_scoring"


class ConsentRequest(BaseModel):
    borrower_ref: str = "anonymous"
    scopes: List[str] = ["open_banking:read"]
    purpose: str = "credit_scoring"


@app.get("/api/health")
def health():
    return {"status": "ok", "engine_version": ENGINE_VERSION}


@app.get("/api/samples")
def samples():
    out = []
    for path in sorted(glob.glob(os.path.join(_APPLICANTS, "*.md"))):
        name = os.path.basename(path)
        if name == "FORMAT.md":
            continue
        out.append(name[:-3])
    return {"samples": out}


@app.get("/api/samples/{sample_id}")
def sample(sample_id: str):
    path = os.path.join(_APPLICANTS, f"{os.path.basename(sample_id)}.md")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="unknown sample")
    with open(path, encoding="utf-8") as fh:
        return {"id": sample_id, "md": fh.read()}


@app.get("/api/partners")
def partners():
    return {"partners": [p.to_public() for p in list_partners()]}


@app.post("/api/consent")
def grant_consent(req: ConsentRequest):
    rec = CONSENT.grant(req.borrower_ref, req.scopes, req.purpose)
    AUDIT.append("consent_granted", {"consent_id": rec.consent_id, "scopes": rec.scopes})
    return rec.to_public()


@app.get("/api/consent/{consent_id}")
def get_consent(consent_id: str):
    rec = CONSENT.get(consent_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="unknown consent")
    return rec.to_public()


@app.post("/api/consent/{consent_id}/revoke")
def revoke_consent(consent_id: str):
    rec = CONSENT.revoke(consent_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="unknown consent")
    AUDIT.append("consent_revoked", {"consent_id": rec.consent_id})
    return rec.to_public()


@app.get("/api/audit")
def audit(limit: int = 50):
    return {"entries": [e.to_public() for e in AUDIT.entries(limit)]}


@app.post("/api/score")
def score(req: ScoreRequest):
    try:
        borrower, application, events, as_of = parse_applicant(req.md)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # 1) the data source must be a registered, sandbox-approved partner
    partner = get_partner(req.partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail=f"unknown partner '{req.partner_id}'")
    if not partner.approved:
        raise HTTPException(
            status_code=403,
            detail=f"partner '{partner.partner_id}' is not sandbox-approved",
        )

    # 2) data use must be authorised by a consent covering the partner's scopes
    if req.consent_id:
        consent = CONSENT.get(req.consent_id)
        if consent is None:
            raise HTTPException(status_code=404, detail="unknown consent")
        if not consent.covers(partner.required_scopes):
            raise HTTPException(
                status_code=403,
                detail=f"consent does not cover required scopes {list(partner.required_scopes)}",
            )
    else:  # frictionless demo: auto-grant an implicit consent, recorded as such
        consent = CONSENT.grant(
            req.borrower_ref or borrower.full_name,
            list(partner.required_scopes),
            req.purpose,
            implicit=True,
        )

    mode = "calibrated" if req.mode == "calibrated" else "hand"
    result = run_pipeline(borrower, application, events, as_of, mode)
    render = to_render(result, borrower, mode)
    render["provenance"] = {
        "partner": partner.to_public(),
        "consent": consent.to_public(),
        "corroboration": result.corroboration,
        "input_hash": result.snapshot["input_hash"],
        "versions": result.snapshot["versions"],
    }

    entry = AUDIT.append("score", {
        "application_id": result.application_id,
        "borrower": borrower.full_name,
        "partner_id": partner.partner_id,
        "consent_id": consent.consent_id,
        "consent_implicit": consent.implicit,
        "trust_score": result.trust_score,
        "trust_tier": result.trust_tier,
        "recommendation": result.ai_recommendation,
        "fraud_level": result.fraud_level,
        "input_hash": result.snapshot["input_hash"],
        "versions": result.snapshot["versions"],
    })
    render["provenance"]["decided_at"] = entry.timestamp   # real audit time (display-only)
    return JSONResponse(render)


@app.get("/")
def console():
    index = os.path.join(_WEBDEMO, "index.html")
    if not os.path.isfile(index):
        return JSONResponse({"detail": "console not found"}, status_code=404)
    return FileResponse(index, media_type="text/html")
