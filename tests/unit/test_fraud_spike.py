"""#1 — the upgraded, parking-aware / employment-aware spike rule.

A one-off big month is normal for variable-income workers (our target segment) and must NOT be
flagged as fraud. A spike only flags when it looks like fund-parking, or is unexplained for a
steady-income earner.
"""
from datetime import date

from trustlink.domain.enums import Category, FraudLevel, TransactionType
from trustlink.domain.models import Application, Borrower, Transaction
from trustlink.fraud.rules import evaluate
from trustlink.fraud.veto import fraud_level

AS_OF = date(2026, 6, 30)
MONTHS = [(2026, m) for m in range(1, 7)]
# steady small months + one big legitimate project payout in month index 3 (a >3x spike)
SPIKY = [16_000_000, 14_000_000, 15_000_000, 50_000_000, 15_000_000, 16_000_000]


def _events(inflows, transfers=None):
    ev, n = [], 0
    for i, ((y, m), inf) in enumerate(zip(MONTHS, inflows)):
        n += 1
        ev.append(Transaction(f"I{n}", "APP", date(y, m, 1), TransactionType.INCOME, Category.OTHER, inf))
        if transfers and i in transfers:
            n += 1
            ev.append(Transaction(f"T{n}", "APP", date(y, m, 15), TransactionType.TRANSFER, Category.OTHER, transfers[i]))
    return ev


def _borrower(employment, declared=21_000_000):
    return Borrower("B", "Test", employment, "", declared, "thin", True, 0)


def _app():
    return Application("APP", "B", 40_000_000, "x", 12)


def test_freelancer_big_month_is_not_fraud():
    flags = evaluate(_borrower("Freelancer"), _app(), _events(SPIKY), AS_OF, 6)
    rules = {f.rule for f in flags}
    # the spike must NOT produce a fraud flag for a freelancer...
    assert "fund_parking" not in rules
    assert "unexplained_income_spike" not in rules
    # ...and nothing here escalates to High (no fraud-reject)
    assert fraud_level(flags) != FraudLevel.HIGH


def test_salaried_unexplained_spike_is_medium():
    # the SAME cashflow, but for someone whose income should be steady -> worth a human look
    flags = evaluate(_borrower("Salaried"), _app(), _events(SPIKY), AS_OF, 6)
    spike = [f for f in flags if f.rule == "unexplained_income_spike"]
    assert spike and spike[0].severity == FraudLevel.MEDIUM


def test_parking_pattern_is_high_even_for_freelancer():
    # spike money moved straight back out (48M of the 50M) -> balance inflation -> High
    events = _events(SPIKY, transfers={3: 48_000_000})
    flags = evaluate(_borrower("Freelancer"), _app(), events, AS_OF, 6)
    park = [f for f in flags if f.rule == "fund_parking"]
    assert park and park[0].severity == FraudLevel.HIGH
    assert fraud_level(flags) == FraudLevel.HIGH
