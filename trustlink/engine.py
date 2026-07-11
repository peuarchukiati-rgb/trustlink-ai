r"""run_pipeline — the single orchestration entrypoint.

raw events -> features -> dimensions -> Trust Score
                                   \-> confidence (data sufficiency)
              fraud veto (independent) -\
              affordability (capacity) ---> decision
A later FastAPI layer wraps each already-pure sub-step; no core refactor needed.
"""
from __future__ import annotations

from datetime import date
from statistics import mean

from . import corroboration as corrob
from .decision.affordability import assess
from .decision.engine import decide
from .domain.enums import FraudLevel
from .domain.models import Application, Borrower, FraudFlag, PipelineResult, Transaction
from .explain.templates import build_factors
from .features.compute import compute_features
from .features.functions import FeatureContext, _in_window, _is_income, _is_outflow, _monthly_sums
from .fraud.rules import evaluate as fraud_evaluate
from .fraud.veto import fraud_level as compute_fraud_level
from .fraud.veto import fraud_score as compute_fraud_score
from .scoring.confidence import cashflow_consistency, compute_confidence
from .scoring.dimensions import score_dimensions
from .scoring.scorecard import compute_trust_score
from .versioning import make_snapshot


def _avg_cashflow(borrower, application, events, as_of, window) -> tuple[float, float]:
    ctx = FeatureContext(borrower, application, tuple(events), as_of, window)
    txns = _in_window(ctx)
    inflow = [amt for _, amt in _monthly_sums(txns, _is_income)]
    outflow = [amt for _, amt in _monthly_sums(txns, _is_outflow)]
    return (mean(inflow) if inflow else 0.0), (mean(outflow) if outflow else 0.0)


def run_pipeline(
    borrower: Borrower,
    application: Application,
    events: list[Transaction],
    as_of: date,
    mode: str = "hand",
) -> PipelineResult:
    fv = compute_features(borrower, application, events, as_of)
    window = fv.window_months

    dimensions = score_dimensions(fv)
    trust_score, tier = compute_trust_score(dimensions, mode)

    avg_in, avg_out = _avg_cashflow(borrower, application, events, as_of, window)

    # Approved-partner corroboration (pay-slip / national data centre). It only lifts CONFIDENCE
    # when a source agrees, or raises a fraud flag when one materially conflicts — it never enters
    # the weighted Trust Score, and a borrower who supplies no source is not penalised.
    corr = corrob.assess(borrower, avg_in)

    consistency = cashflow_consistency(borrower, application, events, as_of, window)
    confidence = compute_confidence(dimensions, consistency)
    if corr.corroborated:
        confidence = round(min(1.0, confidence + corr.confidence_bonus), 2)

    fraud_flags = fraud_evaluate(borrower, application, events, as_of, window)
    if corr.conflict:
        worst = max((s.gap for s in corr.sources if s.conflicts), default=0.0)
        sev = FraudLevel.HIGH if worst >= 2 * corrob.CONFLICT_GAP else FraudLevel.MEDIUM
        fraud_flags = [
            *fraud_flags,
            FraudFlag(
                rule="income_source_conflict",
                severity=sev,
                description="Partner income source conflicts with observed Open-Banking inflow",
            ),
        ]
    fraud_level = compute_fraud_level(fraud_flags)
    fraud_pts = compute_fraud_score(fraud_flags)

    affordability = assess(application, avg_in, avg_out, borrower.existing_monthly_debt)

    positive, risk = build_factors(borrower, dimensions, events, consistency, fraud_level, corr)
    decision = decide(application, trust_score, tier, fraud_level, affordability, confidence)

    snapshot = make_snapshot(
        borrower=borrower,
        application=application,
        transactions=events,
        feature_values=fv.values,
        as_of=as_of,
    )

    return PipelineResult(
        application_id=application.application_id,
        trust_score=trust_score,
        trust_tier=tier.value,
        confidence_level=confidence,
        positive_factors=positive,
        risk_factors=risk,
        fraud_level=fraud_level.value,
        fraud_flags=fraud_flags,
        ai_recommendation=decision.ai_recommendation,
        suggested_amount=decision.suggested_amount,
        suggested_tenor_months=decision.suggested_tenor_months,
        decision_confidence=decision.decision_confidence,
        requires_human_review=decision.requires_human_review,
        dimensions=dimensions,
        snapshot=snapshot,
        fraud_score=fraud_pts,
        dsr=affordability.dsr,
        avg_inflow=avg_in,
        avg_outflow=avg_out,
        surplus=affordability.surplus,
        max_principal=affordability.max_principal,
        corroboration={
            "corroborated": corr.corroborated,
            "conflict": corr.conflict,
            "confidence_bonus": corr.confidence_bonus,
            "observed_avg_inflow": corr.observed_avg_inflow,
            "sources": [
                {
                    "name": s.name, "reported": s.reported, "gap": s.gap,
                    "agrees": s.agrees, "conflicts": s.conflicts,
                }
                for s in corr.sources
            ],
        },
    )
