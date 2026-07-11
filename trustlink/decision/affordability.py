"""Affordability / capacity — separate from trustworthiness.

The offer is capped by TWO tests, and the tighter one wins:
  1. Disposable surplus  — a prudent share of (inflow - outflow) over the tenor.
  2. Debt-service ratio (#4) — total monthly debt (existing + this loan's installment at an
     assumed APR) must stay within DSR_MAX of income. This is the responsible-lending test and
     needs the borrower's existing obligations; with no existing debt it simply reflects this loan.
Both constants are policy levers (see calibration_note.md).
"""
from __future__ import annotations

from ..domain.models import Affordability, Application

SURPLUS_UTILISATION_CAP = 0.60   # share of monthly surplus a prudent installment may consume
ROUNDING_STEP = 5_000_000         # offers are rounded down to a clean step
ASSUMED_APR = 0.18                # nominal annual rate assumed for the DSR installment (#4)
DSR_MAX = 0.45                    # total debt service must stay within this share of income


def _installment(principal: float, tenor: int, apr: float) -> float:
    r = apr / 12.0
    if principal <= 0:
        return 0.0
    if r == 0:
        return principal / tenor
    return principal * r / (1 - (1 + r) ** (-tenor))


def _principal_for_installment(installment: float, tenor: int, apr: float) -> float:
    r = apr / 12.0
    if installment <= 0:
        return 0.0
    if r == 0:
        return installment * tenor
    return installment * (1 - (1 + r) ** (-tenor)) / r


def assess(application: Application, avg_inflow: float, avg_outflow: float,
           existing_debt: float = 0.0) -> Affordability:
    tenor = application.requested_tenor_months
    surplus = int(round(avg_inflow - avg_outflow))
    surplus_cap = max(0.0, SURPLUS_UTILISATION_CAP * surplus * tenor)

    max_installment = max(0.0, DSR_MAX * avg_inflow - existing_debt)
    dsr_cap = _principal_for_installment(max_installment, tenor, ASSUMED_APR)

    raw = min(surplus_cap, dsr_cap)
    max_principal = max(0, int(raw // ROUNDING_STEP) * ROUNDING_STEP)
    suggested = min(application.requested_amount, max_principal)
    adjusted = suggested < application.requested_amount

    if suggested == application.requested_amount:
        binding = "requested"
    elif dsr_cap <= surplus_cap:
        binding = "dsr"
    else:
        binding = "surplus"

    inst = _installment(suggested, tenor, ASSUMED_APR)
    dsr = round((existing_debt + inst) / avg_inflow, 3) if avg_inflow else 0.0

    rationale = (
        f"surplus cap {int(surplus_cap):,} vs DSR cap {int(dsr_cap):,} → offer {suggested:,} "
        f"(DSR {dsr:.0%}, bound by {binding})"
    )
    return Affordability(
        surplus=surplus, max_principal=max_principal, suggested_amount=suggested,
        suggested_tenor_months=tenor, adjusted=adjusted, rationale=rationale,
        dsr=dsr, binding=binding,
    )
