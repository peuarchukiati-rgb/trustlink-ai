"""Income corroboration across approved-partner data sources (P4 alternative data).

The P4 brief asks for scoring on "insurance, pay slips, and consumption" plus national-data-centre
signals. Open-Banking inflow is our primary behavioural signal; a pay-slip (approved payroll
partner) and a national-data / social-insurance registry figure are *corroborating* sources.

Design rules (kept faithful to the engine's philosophy):
  * Corroboration NEVER enters the weighted 6-dimension Trust Score. A borrower who supplies no
    pay-slip / registry figure is not penalised — missing is not bad. It only affects CONFIDENCE
    (how sure we are) and, on a material conflict, raises a fraud signal.
  * A source that AGREES with observed inflow (within TOLERANCE) adds a small, bounded confidence
    bonus — independent evidence that the behavioural picture is real.
  * A source that materially DISAGREES (gap > CONFLICT_GAP) is surfaced as a conflict for the
    fraud layer / underwriter, never silently averaged away.
"""
from __future__ import annotations

from dataclasses import dataclass

from .domain.models import Borrower

TOLERANCE = 0.15          # within 15% of observed inflow -> the source agrees
CONFLICT_GAP = 0.30       # more than 30% away -> a material conflict (for the fraud layer)
BONUS_PER_SOURCE = 0.03   # confidence bonus per agreeing source...
MAX_BONUS = 0.06          # ...capped so corroboration can never dominate confidence


@dataclass(frozen=True)
class CorroborationSource:
    name: str          # "Pay-slip", "National Data Centre"
    reported: int      # income the source reports (VND / month)
    gap: float         # relative gap vs observed inflow (0 = exact match)
    agrees: bool
    conflicts: bool


@dataclass(frozen=True)
class Corroboration:
    observed_avg_inflow: int
    sources: list[CorroborationSource]
    corroborated: bool         # >=1 source agrees with observed inflow
    conflict: bool             # >=1 source materially disagrees
    confidence_bonus: float    # bounded add-on to confidence when corroborated


def _candidate_sources(borrower: Borrower) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    if borrower.payslip_monthly_income is not None:
        out.append(("Pay-slip", int(borrower.payslip_monthly_income)))
    if borrower.registry_monthly_income is not None:
        out.append(("National Data Centre", int(borrower.registry_monthly_income)))
    return out


def assess(borrower: Borrower, observed_avg_inflow: float) -> Corroboration:
    """Compare each supplied partner income figure against observed Open-Banking inflow."""
    observed = int(round(observed_avg_inflow))
    sources: list[CorroborationSource] = []
    for name, reported in _candidate_sources(borrower):
        if observed <= 0 or reported <= 0:
            gap = 1.0
        else:
            gap = abs(reported - observed) / observed
        sources.append(
            CorroborationSource(
                name=name,
                reported=reported,
                gap=round(gap, 4),
                agrees=gap <= TOLERANCE,
                conflicts=gap > CONFLICT_GAP,
            )
        )

    agree_count = sum(1 for s in sources if s.agrees)
    corroborated = agree_count > 0
    conflict = any(s.conflicts for s in sources)
    bonus = min(MAX_BONUS, BONUS_PER_SOURCE * agree_count) if corroborated else 0.0
    return Corroboration(
        observed_avg_inflow=observed,
        sources=sources,
        corroborated=corroborated,
        conflict=conflict,
        confidence_bonus=round(bonus, 4),
    )
