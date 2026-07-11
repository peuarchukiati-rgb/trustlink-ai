"""Declarative persona specs. Ms. Aom (B001) is the calibrated anchor; B/C/D exercise the
Approve / Human-Review / Reject paths. All amounts are VND.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..domain.enums import Category, TransactionType
from ..domain.models import Application, Borrower

AS_OF = date(2026, 6, 30)

# (category, transaction_type, monthly_amount, on_time) — applied every month
OutflowLine = tuple[Category, TransactionType, int, bool]


@dataclass(frozen=True)
class PersonaSpec:
    borrower: Borrower
    application: Application
    monthly_inflows: tuple[int, ...]        # one income deposit per month, chronological
    outflow_lines: tuple[OutflowLine, ...]
    as_of: date = AS_OF
    income_category: Category = Category.PAYROLL


# --------------------------------------------------------------------------- Ms. Aom (anchor)
AOM = PersonaSpec(
    borrower=Borrower(
        borrower_id="B001",
        full_name="Ms. Aom",
        employment_type="Freelancer",
        occupation="Digital Designer",
        declared_monthly_income=18_500_000,
        credit_history_type="thin",
        ekyc_verified=True,
        bureau_tradelines=0,
    ),
    application=Application(
        application_id="APP001",
        borrower_id="B001",
        requested_amount=50_000_000,
        loan_purpose="Business equipment",
        requested_tenor_months=12,
    ),
    # mean 18.5M, CV ~0.175 (freelance variance), flat trend (non-monotonic)
    monthly_inflows=(18_200_000, 14_500_000, 22_900_000, 14_800_000, 22_200_000, 18_400_000),
    outflow_lines=(
        (Category.RENT, TransactionType.EXPENSE, 4_500_000, True),
        (Category.FOOD, TransactionType.EXPENSE, 2_500_000, True),
        (Category.TRANSPORT, TransactionType.EXPENSE, 1_000_000, True),
        (Category.UTILITY, TransactionType.PAYMENT, 800_000, True),
        (Category.INSURANCE, TransactionType.PAYMENT, 716_000, True),
        (Category.SHOPPING, TransactionType.EXPENSE, 2_684_000, True),
    ),
    income_category=Category.OTHER,
)

# --------------------------------------------------------------------------- B: salaried approve
SALARIED = PersonaSpec(
    borrower=Borrower(
        borrower_id="B002",
        full_name="Mr. Bao",
        employment_type="Salaried",
        occupation="Bank Officer",
        declared_monthly_income=30_000_000,
        credit_history_type="established",
        ekyc_verified=True,
        bureau_tradelines=5,
    ),
    application=Application(
        application_id="APP002",
        borrower_id="B002",
        requested_amount=80_000_000,
        loan_purpose="Home improvement",
        requested_tenor_months=12,
    ),
    monthly_inflows=(30_000_000,) * 6,           # very stable payroll
    outflow_lines=(
        (Category.RENT, TransactionType.EXPENSE, 7_000_000, True),
        (Category.FOOD, TransactionType.EXPENSE, 4_000_000, True),
        (Category.TRANSPORT, TransactionType.EXPENSE, 2_000_000, True),
        (Category.UTILITY, TransactionType.PAYMENT, 1_200_000, True),
        (Category.INSURANCE, TransactionType.PAYMENT, 1_300_000, True),
        (Category.SHOPPING, TransactionType.EXPENSE, 2_500_000, True),
    ),
)

# --------------------------------------------------------------------------- C: irregular -> review
IRREGULAR = PersonaSpec(
    borrower=Borrower(
        borrower_id="B003",
        full_name="Ms. Chi",
        employment_type="Gig worker",
        occupation="Rideshare Driver",
        declared_monthly_income=18_000_000,
        credit_history_type="thin",
        ekyc_verified=True,
        bureau_tradelines=0,
    ),
    application=Application(
        application_id="APP003",
        borrower_id="B003",
        requested_amount=40_000_000,
        loan_purpose="Vehicle maintenance",
        requested_tenor_months=12,
    ),
    # CV > 50% -> income-instability flag (Medium) -> Human Review
    monthly_inflows=(8_000_000, 28_000_000, 6_000_000, 30_000_000, 10_000_000, 26_000_000),
    outflow_lines=(
        (Category.RENT, TransactionType.EXPENSE, 5_000_000, True),
        (Category.FOOD, TransactionType.EXPENSE, 3_500_000, True),
        (Category.UTILITY, TransactionType.PAYMENT, 900_000, True),
        (Category.INSURANCE, TransactionType.PAYMENT, 600_000, True),
        (Category.SHOPPING, TransactionType.EXPENSE, 3_000_000, True),
    ),
)

# --------------------------------------------------------------------------- D: high risk -> reject
HIGH_RISK = PersonaSpec(
    borrower=Borrower(
        borrower_id="B004",
        full_name="Mr. Dat",
        employment_type="Self-employed",
        occupation="Trader",
        declared_monthly_income=40_000_000,   # far above observed inflow -> High mismatch
        credit_history_type="thin",
        ekyc_verified=True,
        bureau_tradelines=0,
    ),
    application=Application(
        application_id="APP004",
        borrower_id="B004",
        requested_amount=60_000_000,
        loan_purpose="Working capital",
        requested_tenor_months=12,
    ),
    monthly_inflows=(12_000_000,) * 6,
    outflow_lines=(
        (Category.RENT, TransactionType.EXPENSE, 6_000_000, True),
        (Category.FOOD, TransactionType.EXPENSE, 4_000_000, True),
        (Category.UTILITY, TransactionType.PAYMENT, 900_000, False),   # missed
        (Category.INSURANCE, TransactionType.PAYMENT, 700_000, False),  # missed
        (Category.SHOPPING, TransactionType.EXPENSE, 1_500_000, True),
    ),
)

# --------------------------------------------------------------------------- E: lumpy freelancer
# One big project month (a >3x spike). The OLD spike rule flagged this as fraud (High -> Reject);
# the upgraded rule treats it as legitimate variable income, so no fraud-reject.
LUMPY_FREELANCER = PersonaSpec(
    borrower=Borrower(
        borrower_id="B005",
        full_name="Ms. Fah",
        employment_type="Freelancer",
        occupation="Video Editor",
        declared_monthly_income=21_000_000,
        credit_history_type="thin",
        ekyc_verified=True,
        bureau_tradelines=0,
    ),
    application=Application(
        application_id="APP005",
        borrower_id="B005",
        requested_amount=40_000_000,
        loan_purpose="Equipment upgrade",
        requested_tenor_months=12,
    ),
    # steady small months + one big legitimate project payout (50M) -> a >3x spike
    monthly_inflows=(16_000_000, 14_000_000, 15_000_000, 50_000_000, 15_000_000, 16_000_000),
    outflow_lines=(
        (Category.RENT, TransactionType.EXPENSE, 5_000_000, True),
        (Category.FOOD, TransactionType.EXPENSE, 3_000_000, True),
        (Category.UTILITY, TransactionType.PAYMENT, 800_000, True),
        (Category.INSURANCE, TransactionType.PAYMENT, 600_000, True),
        (Category.SHOPPING, TransactionType.EXPENSE, 2_000_000, True),
    ),
    income_category=Category.OTHER,
)

ALL_PERSONAS = {
    "APP001": AOM,
    "APP002": SALARIED,
    "APP003": IRREGULAR,
    "APP004": HIGH_RISK,
    "APP005": LUMPY_FREELANCER,
}
