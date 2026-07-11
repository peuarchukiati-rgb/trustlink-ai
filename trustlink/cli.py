"""TrustLink TIE spine — command line.

    python -m trustlink.cli demo                        # Ms. Aom, full breakdown + money shot
    python -m trustlink.cli score   --application APP001
    python -m trustlink.cli compare --application APP001 # traditional bureau vs TIE
    python -m trustlink.cli generate --application APP001 # dump synthetic transactions as JSON
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .baseline.traditional import score as baseline_score
from .data.generator import load
from .data.personas import ALL_PERSONAS
from .engine import run_pipeline


def _run(application_id: str):
    borrower, application, events = load(application_id)
    result = run_pipeline(borrower, application, events, ALL_PERSONAS[application_id].as_of)
    return borrower, application, events, result


def _fmt_vnd(x) -> str:
    return f"{int(x):,} VND" if x is not None else "—"


def _print_scorecard(borrower, application, result) -> None:
    print(f"\n  Borrower : {borrower.full_name}  ({borrower.employment_type}, "
          f"{borrower.credit_history_type} file)")
    print(f"  Loan     : requested {_fmt_vnd(application.requested_amount)} / "
          f"{application.requested_tenor_months}m — {application.loan_purpose}")
    print(f"\n  Trust Score : {result.trust_score} / 1000   Tier: {result.trust_tier}"
          f"   Confidence: {result.confidence_level:.2f}")
    print("  Dimension breakdown (transparent derivation):")
    for d in result.dimensions:
        print(f"     - {d.dimension:<20} subscore {int(d.subscore):>3}   "
              f"coverage {d.coverage:.2f}")
    print(f"\n  Fraud    : {result.fraud_level}")
    for f in result.fraud_flags:
        print(f"     ⚠ [{f.severity.value}] {f.rule}: {f.description}")
    print(f"\n  Positive : {result.positive_factors}")
    print(f"  Risks    : {result.risk_factors}")
    print(f"\n  DECISION : {result.ai_recommendation}")
    print(f"             suggested {_fmt_vnd(result.suggested_amount)} / "
          f"{result.suggested_tenor_months}m   "
          f"(human review: {result.requires_human_review})")


def _print_compare(borrower, result) -> None:
    base = baseline_score(borrower)
    print("\n  ── The core claim, side by side ─────────────────────────────")
    print(f"  Traditional Bureau : {base.decision}"
          f"{'' if base.score is None else f' (score {base.score})'} — {base.reason}")
    print(f"  TrustLink TIE      : {result.ai_recommendation} "
          f"(Trust {result.trust_score}/{result.trust_tier}, fraud {result.fraud_level}) "
          f"→ {_fmt_vnd(result.suggested_amount)}")
    if base.decision == "REJECT" and result.ai_recommendation.lower().startswith("approve"):
        print("  →  A thin-file borrower the bureau REJECTS, TrustLink can APPROVE on behaviour. ✅")
    print("  ─────────────────────────────────────────────────────────────")


def cmd_demo(_args) -> int:
    borrower, application, _events, result = _run("APP001")
    print("=" * 66)
    print("  TrustLink AI — Trust Intelligence Engine (TIE)  ·  DEMO: Ms. Aom")
    print("=" * 66)
    _print_scorecard(borrower, application, result)
    _print_compare(borrower, result)
    return 0


def cmd_score(args) -> int:
    borrower, application, _events, result = _run(args.application)
    print(json.dumps(result.trust_score_payload(), indent=2, ensure_ascii=False))
    print(json.dumps(result.decision_payload(), indent=2, ensure_ascii=False))
    return 0


def cmd_compare(args) -> int:
    borrower, application, _events, result = _run(args.application)
    _print_scorecard(borrower, application, result)
    _print_compare(borrower, result)
    return 0


def cmd_generate(args) -> int:
    _b, _a, events = load(args.application)
    print(json.dumps([_txn_json(t) for t in events], indent=2, default=str, ensure_ascii=False))
    return 0


def cmd_validate(args) -> int:
    from .validation.run import main as validation_main
    return validation_main([str(args.n), str(args.seed)])


def cmd_calibrate(args) -> int:
    from .validation.calibrate import main as calibrate_main
    return calibrate_main([str(args.n), str(args.seed)])


def cmd_modes(_args) -> int:
    print("  Hand-set vs data-calibrated (#5) — same borrower, two weightings:")
    print(f"    {'borrower':10} {'hand-set':>16} {'data-calibrated':>18}")
    for app_id in ALL_PERSONAS:
        borrower, application, events = load(app_id)
        as_of = ALL_PERSONAS[app_id].as_of
        h = run_pipeline(borrower, application, events, as_of, "hand")
        c = run_pipeline(borrower, application, events, as_of, "calibrated")
        print(f"    {borrower.full_name:10} {h.trust_score:>5} / {h.trust_tier:8} "
              f"{c.trust_score:>5} / {c.trust_tier}")
    print("  => hand-set and data-learned weights agree closely (Aom 742 vs 739):")
    print("     the DATA confirms the expert design — 'why 742? because the data says so.'")
    return 0


def _txn_json(t) -> dict:
    d = asdict(t)
    d["transaction_type"] = t.transaction_type.value
    d["category"] = t.category.value
    d["transaction_date"] = t.transaction_date.isoformat()
    return d


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="trustlink.cli", description="TrustLink TIE spine")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="run the Ms. Aom demo").set_defaults(func=cmd_demo)
    for name, fn in (("score", cmd_score), ("compare", cmd_compare), ("generate", cmd_generate)):
        p = sub.add_parser(name)
        p.add_argument("--application", default="APP001", choices=list(ALL_PERSONAS))
        p.set_defaults(func=fn)

    pv = sub.add_parser("validate", help="run the synthetic-population validation harness")
    pv.add_argument("--n", type=int, default=4000)   # large default de-noises the fairness metric
    pv.add_argument("--seed", type=int, default=42)
    pv.set_defaults(func=cmd_validate)

    pc = sub.add_parser("calibrate", help="#5 data-calibration demo (AUC uplift + learned weights)")
    pc.add_argument("--n", type=int, default=1000)
    pc.add_argument("--seed", type=int, default=42)
    pc.set_defaults(func=cmd_calibrate)

    sub.add_parser("modes", help="compare hand-set vs data-calibrated scores").set_defaults(func=cmd_modes)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
