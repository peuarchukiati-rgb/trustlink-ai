"""Traditional credit-bureau baseline — the contrast that proves TrustLink's core claim.

A conventional bureau scorer has nothing to score a thin/no-file borrower with, so it declines.
This is exactly the population TrustLink serves via behavioural data.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import Borrower

THIN_FILE_TYPES = {"thin", "none", "thin file", "no file", "limited"}


@dataclass(frozen=True)
class BaselineResult:
    decision: str            # "APPROVE" | "REJECT"
    score: int | None        # FICO-like, None when unscorable
    reason: str


def score(borrower: Borrower) -> BaselineResult:
    thin = borrower.credit_history_type.strip().lower() in THIN_FILE_TYPES
    if thin or borrower.bureau_tradelines <= 0:
        return BaselineResult(
            decision="REJECT",
            score=None,
            reason="Insufficient credit history — no bureau record to score",
        )
    # crude established-file stub: more clean tradelines -> higher score
    fico_like = 600 + min(borrower.bureau_tradelines, 12) * 15
    decision = "APPROVE" if fico_like >= 660 else "REJECT"
    return BaselineResult(
        decision=decision,
        score=fico_like,
        reason="Scored on traditional bureau tradelines",
    )
