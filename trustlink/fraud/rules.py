"""Fraud rules — Volume 5 (AI Agent Architecture), plus a fairness upgrade to rule 2.

    IF income_variance > 50%                            -> flag income instability (Medium)
    IF an income spike looks like fund-parking          -> flag fund_parking       (High)
       (a spike for a STEADY-income earner is a softer  -> unexplained_income_spike (Medium))
    IF declared_income significantly > observed inflow   -> flag mismatch (Low/Med/High by gap)

Rule 2 upgrade (#1): a large one-off inflow is NORMAL for variable-income workers
(freelancer / gig / self-employed) — that is our target segment, so we must not flag it as
fraud. We only flag a spike when it behaves like *fund parking* (money moved straight back out
to inflate the balance), or when it is unexplained for someone whose income should be steady.

Fraud is an INDEPENDENT VETO — it never enters the weighted Trust Score.
"""
from __future__ import annotations

from datetime import date
from statistics import mean, median, pstdev

from ..domain.enums import FraudLevel, TransactionType
from ..domain.models import Application, Borrower, FraudFlag, Transaction
from ..features.functions import FeatureContext, _in_window, _is_income, _monthly_sums

INCOME_VARIANCE_LIMIT = 0.50        # rule 1
SPIKE_FACTOR = 3.0                  # rule 2: a month > 3x the median monthly inflow
PARKING_TRANSFER_FRACTION = 0.60    # >=60% of a spike leaving as transfer soon after = parking
MISMATCH_MIN_GAP = 0.02             # rule 3: ignore trivial declared-vs-observed differences
MISMATCH_MED_GAP = 0.15
MISMATCH_HIGH_GAP = 0.35

# --- extra checks (#3) ---
OCCUPATION_NORM_FACTOR = 2.5        # flag if declared income exceeds 2.5x the occupation ceiling
NEW_ACCOUNT_MONTHS = 3             # accounts younger than this are a thin-history caution
REPEAT_APPLICATION_LIMIT = 2       # more recent applications than this looks like velocity/gaming
ROUND_UNIT = 10_000_000            # "suspiciously round" = an exact multiple of 10M...
ROUND_MISMATCH_GAP = 0.15         # ...AND declared sits well above observed inflow

# Typical monthly income ceiling (VND) by occupation; unknown occupations are skipped (no flag).
OCCUPATION_INCOME_CEILING = {
    "digital designer": 40_000_000, "video editor": 40_000_000, "bank officer": 60_000_000,
    "rideshare driver": 35_000_000, "trader": 100_000_000, "engineer": 70_000_000,
    "teacher": 35_000_000, "nurse": 40_000_000, "sales": 45_000_000, "accountant": 55_000_000,
}

# Employment types whose income is expected to be lumpy — a spike is not, by itself, suspicious.
VARIABLE_INCOME_TYPES = {
    "freelancer", "gig worker", "gig", "self-employed", "self employed", "contractor",
}


def _is_variable_income(borrower: Borrower) -> bool:
    return (borrower.employment_type or "").strip().lower() in VARIABLE_INCOME_TYPES


def _next_month(key: tuple[int, int]) -> tuple[int, int]:
    y, m = key
    return (y + 1, 1) if m == 12 else (y, m + 1)


def _is_transfer(t: Transaction) -> bool:
    return t.transaction_type == TransactionType.TRANSFER


def _parking_detected(txns, spike_month, spike_amount) -> bool:
    """A spike looks like parking if a large transfer leaves in the spike month or the next."""
    transfer_by_month = dict(_monthly_sums(txns, _is_transfer))
    moved = transfer_by_month.get(spike_month, 0) + transfer_by_month.get(_next_month(spike_month), 0)
    return spike_amount > 0 and moved >= PARKING_TRANSFER_FRACTION * spike_amount


def evaluate(
    borrower: Borrower, application: Application, events, as_of: date, window_months: int
) -> list[FraudFlag]:
    ctx = FeatureContext(borrower, application, tuple(events), as_of, window_months)
    txns = _in_window(ctx)
    inflow_series = _monthly_sums(txns, _is_income)     # [(month_key, amount)]
    inflow = [amt for _, amt in inflow_series]
    variable = _is_variable_income(borrower)
    flags: list[FraudFlag] = []

    # rule 1 — income instability
    if len(inflow) >= 2:
        m = mean(inflow)
        cv = (pstdev(inflow) / m) if m else 0.0
        if cv > INCOME_VARIANCE_LIMIT:
            # Medium: instability warrants human review, not an outright fraud reject.
            flags.append(FraudFlag(
                "income_instability", FraudLevel.MEDIUM,
                f"Monthly income variance {cv:.0%} exceeds {INCOME_VARIANCE_LIMIT:.0%}",
            ))

    # rule 2 — abnormal spike, but parking-aware and employment-aware (#1)
    if len(inflow) >= 2:
        med = median(inflow)
        if med:
            spike_month, spike_amt = max(inflow_series, key=lambda kv: kv[1])
            if spike_amt > SPIKE_FACTOR * med:
                ratio = spike_amt / med
                if _parking_detected(txns, spike_month, spike_amt):
                    flags.append(FraudFlag(
                        "fund_parking", FraudLevel.HIGH,
                        f"A large inflow ({ratio:.1f}x median) is moved out shortly after "
                        f"— possible balance inflation",
                    ))
                elif not variable:
                    # steady-income earner: an unexplained spike is worth a human look
                    flags.append(FraudFlag(
                        "unexplained_income_spike", FraudLevel.MEDIUM,
                        f"A monthly inflow is {ratio:.1f}x the median with no matching income pattern",
                    ))
                # else: variable-income + not parked -> legitimate lumpy income, no flag.

    # rule 3 — declared vs observed income mismatch
    if inflow:
        observed = mean(inflow)
        declared = borrower.declared_monthly_income
        gap = (declared - observed) / observed if observed else 0.0
        if gap > MISMATCH_MIN_GAP:
            severity = (
                FraudLevel.LOW if gap < MISMATCH_MED_GAP
                else FraudLevel.MEDIUM if gap < MISMATCH_HIGH_GAP
                else FraudLevel.HIGH
            )
            flags.append(FraudFlag(
                "income_mismatch", severity,
                f"Declared income is {gap:.0%} above observed monthly inflow",
            ))

    observed = mean(inflow) if inflow else 0.0

    # rule 4 — declared income far above the norm for the stated occupation
    ceiling = OCCUPATION_INCOME_CEILING.get((borrower.occupation or "").strip().lower())
    if ceiling and borrower.declared_monthly_income > OCCUPATION_NORM_FACTOR * ceiling:
        flags.append(FraudFlag(
            "occupation_income_norm", FraudLevel.MEDIUM,
            f"Declared income far exceeds the norm for '{borrower.occupation}'",
        ))

    # rule 5 — suspiciously round declared income that also sits well above observed inflow
    di = borrower.declared_monthly_income
    if di and di % ROUND_UNIT == 0 and observed and (di - observed) / observed > ROUND_MISMATCH_GAP:
        flags.append(FraudFlag(
            "round_number", FraudLevel.LOW,
            "Declared income is an implausibly round figure above observed inflow",
        ))

    # rule 6 — brand-new account (thin observation history)
    if borrower.account_age_months is not None and borrower.account_age_months < NEW_ACCOUNT_MONTHS:
        flags.append(FraudFlag(
            "new_account", FraudLevel.LOW,
            f"Account is only {borrower.account_age_months} month(s) old",
        ))

    # rule 7 — application velocity (many recent applications)
    if borrower.prior_applications > REPEAT_APPLICATION_LIMIT:
        flags.append(FraudFlag(
            "application_velocity", FraudLevel.MEDIUM,
            f"{borrower.prior_applications} recent applications by this borrower",
        ))

    return flags
