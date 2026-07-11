# TrustLink AI — Trust Intelligence Engine (TIE) spine

The runnable, testable **core** of TrustLink AI (Shinhan P4). It proves the central claim:

> *A financially-responsible thin-file borrower whom a traditional credit bureau would **reject**
> can be confidently **approved** via trusted behavioural data.*

This is the engine only — no FastAPI/UI/LLM/real Open Banking (those attach later without a core
refactor). Everything is deterministic and explainable.

## Pipeline

```
raw events ─► features ─► dimension sub-scores ─► weighted Trust Score (0–1000)
                              │                         │
                              └─ coverage ─► confidence  ├─ Fraud VETO (independent) ─┐
                                                         └─ Affordability (surplus) ──┴─► Decision
```

- **Deterministic only** — no LLM computes the score. `explain/` renders narrative from reason
  codes and is never imported by `scoring/ fraud/ decision/` (an LLM can replace `explain/` later).
- **Point-in-time correct** — features read only events dated ≤ `as_of`.
- **Missing ≠ bad** — features return `(value, coverage)`; missingness lowers *confidence*, not score.
- **Fraud is a veto**, not a weighted 5% — a high income score can't buy back a fraud signal.
- **Reproducible** — every result carries a `snapshot` (input hash + feature values + versions).

## Run

```bash
pip install -r requirements.txt

python -m trustlink.cli demo                          # Ms. Aom: full breakdown + money shot
python -m trustlink.cli compare --application APP001  # traditional bureau vs TIE
python -m trustlink.cli score   --application APP002  # JSON (Volume 8 contract shapes)
python -m trustlink.cli generate --application APP001 # synthetic transactions as JSON

pytest                                                # golden + unit tests
```

## Anchor (calibrated, transparently derived — see `config/calibration_note.md`)

| Borrower | Trust | Tier | Fraud | Decision | Amount |
|---|---|---|---|---|---|
| Ms. Aom (thin-file freelancer) | **742** | Strong | Low | Approve (adjusted) | 45,000,000 |
| Mr. Bao (salaried) | 802 | Strong | Low | Approve | 80,000,000 |
| Ms. Chi (irregular income) | 715 | Moderate | Medium | Human Review | — |
| Mr. Dat (high risk) | 564 | Weak | High | Reject | 0 |

## Layout

`config/` declarative feature spec + weights + bands + calibration note ·
`trustlink/features` pure feature functions · `trustlink/scoring` bands→dimensions→scorecard +
confidence · `trustlink/fraud` veto · `trustlink/decision` affordability + decision ·
`trustlink/baseline` traditional-bureau contrast · `trustlink/explain` deterministic narrative ·
`trustlink/engine.py` the orchestration entrypoint · `tests/golden` pinned outputs.
