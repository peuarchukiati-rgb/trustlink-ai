"""Frozen domain models. Field names mirror Volume 7 / Volume 8 contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .enums import Category, FraudLevel, TransactionType, TrustTier


@dataclass(frozen=True)
class Borrower:
    borrower_id: str
    full_name: str
    employment_type: str          # Salaried, Freelancer, SME, Gig worker
    occupation: str
    declared_monthly_income: int
    credit_history_type: str      # "thin", "none", "established"
    ekyc_verified: bool = True
    bureau_tradelines: int = 0     # number of traditional credit records
    currency: str = "VND"
    # optional signals (default to a neutral value so existing data is unaffected)
    account_age_months: int | None = None   # None = unknown; small = brand-new account (#3)
    prior_applications: int = 0              # recent loan applications by this borrower (#3)
    existing_monthly_debt: int = 0           # current monthly debt obligations, VND (#4 DSR)
    # approved-partner corroboration sources (P4: "insurance, pay slips, and consumption" +
    # national data centre). None = source not supplied -> neutral, never a penalty (#8).
    payslip_monthly_income: int | None = None    # employer pay-slip income (approved payroll partner)
    registry_monthly_income: int | None = None   # national data centre / social-insurance registry


@dataclass(frozen=True)
class Application:
    application_id: str
    borrower_id: str
    requested_amount: int
    loan_purpose: str
    requested_tenor_months: int
    currency: str = "VND"
    application_status: str = "submitted"


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    application_id: str
    transaction_date: date
    transaction_type: TransactionType
    category: Category
    amount: int                    # positive magnitude in minor-unit-free VND
    on_time: bool = True           # for PAYMENT rows: paid on schedule?
    merchant: str | None = None
    currency: str = "VND"
    source: str = "Mock Open Banking"
    reliability_level: str = "high"


@dataclass(frozen=True)
class FeatureVector:
    values: dict[str, float]
    coverage: dict[str, float]     # 0..1 data-sufficiency per feature
    as_of: date
    window_months: int
    feature_spec_version: str


@dataclass(frozen=True)
class DimensionScore:
    dimension: str
    subscore: float                # 0..100
    coverage: float                # 0..1 -> feeds confidence, never the score
    reason_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TrustScoreResult:
    application_id: str
    trust_score: int               # 0..1000
    trust_tier: TrustTier
    confidence_level: float        # 0..1
    dimensions: list[DimensionScore]
    positive_factors: list[str]
    risk_factors: list[str]


@dataclass(frozen=True)
class FraudFlag:
    rule: str
    severity: FraudLevel
    description: str
    status: str = "open"


@dataclass(frozen=True)
class Affordability:
    surplus: int
    max_principal: int
    suggested_amount: int
    suggested_tenor_months: int
    adjusted: bool                 # was the requested amount reduced?
    rationale: str
    dsr: float = 0.0               # debt-service ratio at the offered amount (#4)
    binding: str = "surplus"       # which cap decided the offer: surplus / dsr / requested


@dataclass(frozen=True)
class Decision:
    application_id: str
    ai_recommendation: str
    suggested_amount: int
    suggested_tenor_months: int
    decision_confidence: float
    requires_human_review: bool


@dataclass(frozen=True)
class PipelineResult:
    application_id: str
    trust_score: int
    trust_tier: str
    confidence_level: float
    positive_factors: list[str]
    risk_factors: list[str]
    fraud_level: str
    fraud_flags: list[FraudFlag]
    ai_recommendation: str
    suggested_amount: int
    suggested_tenor_months: int
    decision_confidence: float
    requires_human_review: bool
    dimensions: list[DimensionScore]
    snapshot: dict
    fraud_score: int = 0           # additive fraud points (#2)
    dsr: float = 0.0               # debt-service ratio at the offer (#4)
    avg_inflow: float = 0.0        # observed avg monthly inflow (for the API/affordability view)
    avg_outflow: float = 0.0
    surplus: int = 0
    max_principal: int = 0
    corroboration: dict = field(default_factory=dict)   # approved-partner income corroboration (#8)

    def trust_score_payload(self) -> dict:
        """Matches Volume 8 POST /trust-score response shape."""
        return {
            "application_id": self.application_id,
            "trust_score": self.trust_score,
            "trust_tier": self.trust_tier,
            "confidence_level": round(self.confidence_level, 2),
            "positive_factors": list(self.positive_factors),
            "risk_factors": list(self.risk_factors),
        }

    def decision_payload(self) -> dict:
        """Matches Volume 8 POST /decision response shape."""
        return {
            "application_id": self.application_id,
            "ai_recommendation": self.ai_recommendation,
            "suggested_amount": self.suggested_amount,
            "suggested_tenor_months": self.suggested_tenor_months,
            "decision_confidence": round(self.decision_confidence, 2),
            "requires_human_review": self.requires_human_review,
        }

    def fraud_payload(self) -> dict:
        """Matches Volume 8 POST /fraud-analysis response shape."""
        return {
            "application_id": self.application_id,
            "fraud_risk_level": self.fraud_level,
            "fraud_flags": [
                {"rule": f.rule, "severity": f.severity.value.lower(), "description": f.description}
                for f in self.fraud_flags
            ],
        }
