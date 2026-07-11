"""Parse an applicant .md file into domain objects (mirrors the console's JS parser)."""
from __future__ import annotations

import re
from datetime import date

from ..domain.enums import Category, TransactionType
from ..domain.models import Application, Borrower, Transaction


def _num(s: str) -> int:
    return int(re.sub(r"[, ]", "", re.sub(r"(?i)vnd", "", s)))


def _bool(s: str, default: bool = True) -> bool:
    if s is None:
        return default
    return bool(re.match(r"(true|yes|1)$", s.strip(), re.I))


def parse_applicant(text: str):
    """Return (borrower, application, events, as_of). Raises ValueError on missing required fields."""
    section = ""
    A: dict[str, str] = {}
    inflow_by_month: list[tuple[int, int]] = []
    out_lines: list[tuple[str, TransactionType, int, bool]] = []

    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("#"):
            hd = raw.replace("#", "").lower()
            if "applicant" in hd and "file" not in hd:
                section = "applicant"
            elif "loan" in hd or "request" in hd:
                section = "loan"
            elif "inflow" in hd:
                section = "inflow"
            elif "outflow" in hd:
                section = "outflow"
            else:
                section = ""
            continue
        item = re.sub(r"^[-*]\s*", "", raw)
        if section in ("applicant", "loan"):
            if ":" in item:
                k, v = item.split(":", 1)
                A[k.strip().lower().replace(" ", "_")] = v.strip()
        elif section == "inflow":
            if ":" in item:
                try:
                    inflow_by_month.append((len(inflow_by_month) + 1, _num(item.rsplit(":", 1)[1])))
                except ValueError:
                    pass
        elif section == "outflow":
            if "|" in item:
                pr = [x.strip() for x in item.split("|")]
                try:
                    amt = _num(pr[2])
                except (ValueError, IndexError):
                    continue
                typ = TransactionType.PAYMENT if re.search("pay", pr[1] if len(pr) > 1 else "", re.I) else TransactionType.EXPENSE
                on_time = bool(re.match(r"(on[_ ]?time|yes|true|1|paid)$", pr[3], re.I)) if len(pr) > 3 else True
                out_lines.append((pr[0].lower(), typ, amt, on_time))

    errs = []
    if not A.get("name"):
        errs.append("missing '- name:' in ## Applicant")
    if len(inflow_by_month) < 2:
        errs.append("need at least 2 monthly inflow lines under ## Monthly Inflow")
    if not (A.get("requested_amount") and _num(A["requested_amount"]) > 0):
        errs.append("missing/invalid '- requested_amount:' in ## Loan Request")
    if errs:
        raise ValueError(" · ".join(errs))

    age = A.get("account_age_months")
    payslip = A.get("payslip_monthly_income")
    registry = A.get("registry_monthly_income") or A.get("national_data_income")
    borrower = Borrower(
        borrower_id="API", full_name=A["name"], employment_type=A.get("employment", ""),
        occupation=A.get("occupation", ""), declared_monthly_income=_num(A.get("declared_monthly_income", "0")),
        credit_history_type=A.get("credit_history", "thin").lower(),
        ekyc_verified=_bool(A.get("ekyc_verified"), True),
        bureau_tradelines=int(A.get("bureau_tradelines", "0") or 0),
        account_age_months=int(age) if age is not None else None,
        prior_applications=int(A.get("prior_applications", "0") or 0),
        existing_monthly_debt=_num(A.get("existing_monthly_debt", "0")),
        payslip_monthly_income=_num(payslip) if payslip else None,
        registry_monthly_income=_num(registry) if registry else None,
    )
    application = Application(
        application_id="API", borrower_id="API", requested_amount=_num(A["requested_amount"]),
        loan_purpose=A.get("purpose", ""), requested_tenor_months=int(A.get("tenor_months", "12") or 12),
    )

    # place transactions across the most recent months ending at the last labelled month
    n = len(inflow_by_month)
    months = [(2026, m) for m in range(1, n + 1)]
    events, k = [], 0
    for (y, m), (_, inf) in zip(months, inflow_by_month):
        k += 1
        events.append(Transaction(f"I{k}", "API", date(y, m, 1), TransactionType.INCOME, Category.OTHER, inf))
        for cat, typ, amt, ot in out_lines:
            if amt <= 0:
                continue
            k += 1
            day = 10 if typ == TransactionType.PAYMENT else 5
            try:
                c = Category(cat)
            except ValueError:
                c = Category.OTHER
            events.append(Transaction(f"X{k}", "API", date(y, m, day), typ, c, amt, on_time=ot))
    as_of = date(months[-1][0], months[-1][1], 28)
    return borrower, application, events, as_of
