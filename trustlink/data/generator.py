"""Turn a PersonaSpec into deterministic Open-Banking-style transactions.

Deterministic by construction (no randomness needed for the fixed personas); `seed` is accepted
for forward compatibility when jittered variants are added.
"""
from __future__ import annotations

from datetime import date

from ..domain.enums import TransactionType
from ..domain.models import Application, Borrower, Transaction
from .personas import ALL_PERSONAS, PersonaSpec


def _month_series(as_of: date, n: int) -> list[tuple[int, int]]:
    """Oldest -> newest list of (year, month) ending at as_of's month."""
    out: list[tuple[int, int]] = []
    y, m = as_of.year, as_of.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def generate(spec: PersonaSpec, seed: int = 0) -> tuple[Borrower, Application, list[Transaction]]:
    app_id = spec.application.application_id
    months = _month_series(spec.as_of, len(spec.monthly_inflows))
    events: list[Transaction] = []
    n = 0

    for (year, month), inflow in zip(months, spec.monthly_inflows):
        n += 1
        events.append(Transaction(
            transaction_id=f"{app_id}-TXI{n:02d}",
            application_id=app_id,
            transaction_date=date(year, month, 1),
            transaction_type=TransactionType.INCOME,
            category=spec.income_category,
            amount=inflow,
        ))
        for category, ttype, amount, on_time in spec.outflow_lines:
            n += 1
            day = 10 if ttype.value == "payment" else 5
            events.append(Transaction(
                transaction_id=f"{app_id}-TX{n:03d}",
                application_id=app_id,
                transaction_date=date(year, month, day),
                transaction_type=ttype,
                category=category,
                amount=amount,
                on_time=on_time,
            ))
    return spec.borrower, spec.application, events


def load(application_id: str) -> tuple[Borrower, Application, list[Transaction]]:
    if application_id not in ALL_PERSONAS:
        raise KeyError(f"unknown application_id '{application_id}' (have {list(ALL_PERSONAS)})")
    return generate(ALL_PERSONAS[application_id])
