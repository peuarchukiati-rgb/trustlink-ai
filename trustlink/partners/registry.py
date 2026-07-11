"""The approved-partner registry and its data-provenance contract.

A ``Partner`` is a fintech data source the bank is permitted to use inside the regulatory sandbox.
Each declares the consent *scopes* it needs (so consent can be checked before any data is used) and
its sandbox approval status (so an unapproved source is never scored). The mock Open-Banking
partner wraps the existing applicant-file pipeline; a real partner would implement the same
provenance contract behind a live API.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_PARTNER_ID = "mock_open_banking"


@dataclass(frozen=True)
class Partner:
    partner_id: str
    display_name: str
    category: str                 # e.g. "open_banking", "payroll", "national_registry"
    sandbox_status: str           # "approved" partners are the only ones the engine will score
    required_scopes: tuple[str, ...]   # consent scopes a borrower must grant before use
    description: str = ""

    @property
    def approved(self) -> bool:
        return self.sandbox_status == "approved"

    def to_public(self) -> dict:
        return {
            "partner_id": self.partner_id,
            "display_name": self.display_name,
            "category": self.category,
            "sandbox_status": self.sandbox_status,
            "approved": self.approved,
            "required_scopes": list(self.required_scopes),
            "description": self.description,
        }


# The sandbox allow-list. Only "approved" partners may supply data the engine scores.
_REGISTRY: dict[str, Partner] = {
    DEFAULT_PARTNER_ID: Partner(
        partner_id=DEFAULT_PARTNER_ID,
        display_name="Mock Open Banking (sandbox)",
        category="open_banking",
        sandbox_status="approved",
        required_scopes=("open_banking:read",),
        description="Aggregated account transactions via an approved Open-Banking aggregator.",
    ),
    "payroll_partner": Partner(
        partner_id="payroll_partner",
        display_name="Approved Payroll Partner",
        category="payroll",
        sandbox_status="approved",
        required_scopes=("open_banking:read", "payslip:read"),
        description="Employer pay-slip income corroboration via an approved HR/payroll provider.",
    ),
    "national_data_centre": Partner(
        partner_id="national_data_centre",
        display_name="National Data Centre (social-insurance)",
        category="national_registry",
        sandbox_status="approved",
        required_scopes=("open_banking:read", "national_data:read"),
        description="Declared-income corroboration against the national social-insurance registry.",
    ),
    "unlisted_scraper": Partner(
        partner_id="unlisted_scraper",
        display_name="Unlisted Data Scraper",
        category="open_banking",
        sandbox_status="unapproved",
        required_scopes=("open_banking:read",),
        description="NOT sandbox-approved — present to prove the engine refuses unapproved sources.",
    ),
}


def list_partners(approved_only: bool = False) -> list[Partner]:
    ps = list(_REGISTRY.values())
    return [p for p in ps if p.approved] if approved_only else ps


def get_partner(partner_id: str) -> Partner | None:
    return _REGISTRY.get(partner_id)


def is_approved(partner_id: str) -> bool:
    p = _REGISTRY.get(partner_id)
    return bool(p and p.approved)
