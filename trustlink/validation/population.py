"""Synthetic borrower population with GROUND-TRUTH default labels — for validation only.

Honest framing: this is synthetic. Each borrower has hidden "true" financial traits that drive a
probabilistic default label. The engine sees only a NOISY, partial view of those traits (the
Open-Banking data). If the scoring mechanism is sound, its Trust Score should rank real default
risk well — imperfectly, because of the noise. This demonstrates the *mechanism*; it is not a
claim of real-world predictive accuracy (that needs real outcomes).

The default label is driven by creditworthiness traits (reliability / stability / savings) — NOT
by fraud. Fraud is a separate risk type handled by the veto, and is measured separately.
"""
from __future__ import annotations

import random
from datetime import date

from ..domain.enums import Category, TransactionType
from ..domain.models import Application, Borrower, Transaction

AS_OF = date(2026, 6, 30)
EMPLOYMENTS = ["Salaried", "Freelancer", "Gig worker", "Self-employed"]
VARIABLE = {"Freelancer", "Gig worker", "Self-employed"}


def _months(n: int = 6) -> list[tuple[int, int]]:
    out, y, m = [], 2026, 6
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def make_case(rng: random.Random, i: int):
    """Return (borrower, application, events, default_label, fraud_intent)."""
    # --- hidden "true" financial reality (what actually drives default) ---
    # flatter Betas -> a genuine spread of clearly-good and clearly-risky borrowers
    stability = rng.betavariate(1.7, 1.7)
    savings = rng.betavariate(1.7, 1.8)
    reliability = rng.betavariate(2.6, 1.6)          # skewed toward reliable
    income = rng.choice([12, 15, 18, 22, 28, 35, 45]) * 1_000_000
    emp = rng.choice(EMPLOYMENTS)
    established = rng.random() < 0.35
    fraud_intent = rng.random() < 0.08

    # --- ground-truth default probability from the hidden traits + noise ---
    # steep, convex link: low-risk borrowers almost never default, high-risk ones often do,
    # so the label genuinely separates (a flat link would cap AUC near 0.5 by construction).
    risk_index = 0.40 * (1 - reliability) + 0.35 * (1 - stability) + 0.25 * (1 - savings)
    default_prob = _clip(0.02 + 0.62 * risk_index ** 1.8 + rng.gauss(0, 0.03), 0.005, 0.92)
    default = 1 if rng.random() < default_prob else 0

    # --- OBSERVED Open-Banking data (a noisy view of the hidden traits) ---
    # income trends up for stable borrowers, down for unstable ones (drives Financial Trend)
    trend = (stability - 0.5) * 0.55 + rng.gauss(0, 0.05)
    base_cv = 0.06 + (1 - stability) * 0.48 + (0.04 if emp in VARIABLE else 0.0)
    inflows = []
    for t in range(6):
        drift = 1.0 + trend * ((t - 2.5) / 2.5)      # centred ramp across the 6 months
        v = rng.gauss(income * drift, income * base_cv)
        inflows.append(max(1_000_000, int(round(v / 100_000) * 100_000)))
    avg_in = sum(inflows) / 6

    retain = 0.05 + savings * 0.55                    # savings -> higher retained fraction
    monthly_out = max(500_000, int(avg_in * (1 - retain)))
    ess_ratio = 0.58 + savings * 0.32                 # savings -> more essential, less discretionary
    ess = int(monthly_out * ess_ratio)
    disc = monthly_out - ess
    rent, food = int(ess * 0.5), int(ess * 0.3)
    util, ins = int(ess * 0.1), int(ess * 0.1)

    declared = int(avg_in)
    if fraud_intent:
        declared = int(avg_in * rng.uniform(1.25, 1.8))    # over-declared -> mismatch flag

    app_id = f"A{i:04d}"
    borrower = Borrower(
        borrower_id=f"B{i:04d}", full_name=f"case-{i:04d}", employment_type=emp, occupation="",
        declared_monthly_income=declared,
        credit_history_type="established" if established else "thin",
        ekyc_verified=True, bureau_tradelines=rng.randint(2, 8) if established else 0,
    )
    requested = max(10_000_000, int(avg_in * rng.uniform(1.5, 3.0) / 1_000_000) * 1_000_000)
    app = Application(app_id, borrower.borrower_id, requested, "loan", 12)

    # build events; payment on-time is drawn PER MONTH so payment discipline reflects reliability
    events, n = [], 0
    for (y, m), inf in zip(_months(), inflows):
        n += 1
        events.append(Transaction(f"{app_id}-I{n}", app_id, date(y, m, 1),
                                   TransactionType.INCOME, Category.OTHER, inf))
        bills = [
            (Category.RENT, TransactionType.EXPENSE, rent, True),
            (Category.FOOD, TransactionType.EXPENSE, food, True),
            (Category.UTILITY, TransactionType.PAYMENT, util, rng.random() < reliability),
            (Category.INSURANCE, TransactionType.PAYMENT, ins, rng.random() < reliability),
            (Category.SHOPPING, TransactionType.EXPENSE, disc, True),
        ]
        for cat, typ, amt, ot in bills:
            if amt <= 0:
                continue
            n += 1
            day = 10 if typ == TransactionType.PAYMENT else 5
            events.append(Transaction(f"{app_id}-X{n}", app_id, date(y, m, day),
                                       typ, cat, amt, on_time=ot))
    return borrower, app, events, default, fraud_intent
