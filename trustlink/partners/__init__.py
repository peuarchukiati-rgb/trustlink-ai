"""Approved-partner registry (P4: work with approved fintech-partner data, in-sandbox).

P4 states that direct data-pulling is constrained, so a bank collaborates with *approved* fintech
partners inside a regulatory sandbox. This package formalises that integration seam: every data
bundle the engine scores is attributed to a registered partner whose sandbox status and the
consent scopes it requires are explicit and auditable. Swapping the mock adapter for a real
partner API later is a drop-in — the engine and audit trail are unchanged.
"""
from .registry import (
    DEFAULT_PARTNER_ID,
    Partner,
    get_partner,
    is_approved,
    list_partners,
)

__all__ = [
    "DEFAULT_PARTNER_ID",
    "Partner",
    "get_partner",
    "is_approved",
    "list_partners",
]
