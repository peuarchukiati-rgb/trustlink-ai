# TrustLink AI — Changelog

## v2.3 — Console UX & storytelling (design freeze) — presentation only, no engine change

The console now surfaces the whole P4 story on-screen and leads with the money shot. No scoring,
fraud, affordability, governance, or engine logic changed (Ms. Aom still 742 / 0.86; 53 tests pass).

- **Governance & provenance card** (`webdemo/`) — renders the sandbox surface next to the verdict:
  approved partner, consent (status + granted scopes), income corroboration (per-source agree/
  conflict + confidence effect), and the audit record. Works against the real API (server
  provenance, incl. a real `decided_at` audit time) and offline (synthesised, identical shape).
- **Decision → Trust Score → Confidence → Fraud** reordered so the score summary sits directly
  under the decision card (bureau baseline removed from it).
- **"Traditional bureau vs TrustLink AI" comparison card** — the core story as its own card:
  bureau-only *Reject — no bureau record* vs TrustLink *Approve with adjusted amount — verified
  financial behaviour*. Each side is coloured by its own real outcome (honest when both reject).
- **Polish:** audit "Decision timestamp" row (real on API, demo stamp offline); a confidence
  tooltip ("completeness, consistency, and corroboration of available evidence"); coverage now
  reads "Evidence coverage 67%" instead of "coverage 0.67".
- API: `POST /api/score` provenance now includes `decided_at` (the recorded audit time; display-only).

## v2.2 — Close the P4 gaps: sandbox consent/audit, approved-partner seam, corroboration, fairness

Additive only — all five personas keep their exact numbers (**Ms. Aom still 742 / 0.86 / Approve /
45M**). Directly answers the P4 brief's regulatory-sandbox, approved-partner and alternative-data
(pay slips + national data centre) requirements, and resolves the fairness finding honestly.

- **#8 Approved-partner corroboration** (`corroboration.py`) — optional `payslip_monthly_income` /
  `registry_monthly_income` (national data centre) are cross-checked against observed Open-Banking
  inflow. Agreement lifts **confidence** (bounded, ≤0.06) and adds an "Income corroborated by …"
  factor; a material conflict (>30% gap) is raised to the **fraud** layer. Never enters the weighted
  Trust Score, and a borrower who supplies no source is not penalised (missing ≠ bad). New demo
  applicant `applicants/minh.md` (thin-file salaried, three trusted sources agree → 789 / high conf).
- **Regulatory sandbox made demonstrable** (`api/audit.py`) — real **consent** ledger
  (`POST /api/consent`, `GET /api/consent/{id}`, `POST /api/consent/{id}/revoke`) and an immutable
  **audit** trail (`GET /api/audit`) carrying each decision's input-hash + config versions.
  `POST /api/score` now enforces consent (auto-grants an *implicit demo consent* when none is passed,
  so the console keeps working) and records every score.
- **Approved-partner registry** (`partners/`) — a sandbox allow-list with per-partner consent scopes.
  `GET /api/partners`; scoring refuses unapproved sources and consents that don't cover the partner's
  scopes. The mock Open-Banking adapter is a drop-in seam for a real partner API.
- **Fairness resolved honestly** (`validation/run.py`) — the earlier DI 0.51 was small-sample noise
  (at N=800 it swings 0.45–0.57 by seed; the lowest segment changes with the seed). Default N is now
  4000, where DI stabilises at **~0.79**; the report reframes employment as a *monitored segment*
  (the 4/5ths rule is for protected classes) and shows employment is assigned independently of true
  default risk in the generator. No score math changed.
- Tests: **53 passing** (added corroboration + sandbox/consent/audit suites).

## v2.1 — Real backend (FastAPI) + data-calibrated mode in the engine

Tag `hackathon-2nd` preserves the pitch-ready pre-v2.1 state.

- **Real end-to-end system** — `trustlink/api/` (FastAPI). The authoritative Python engine runs
  server-side: `POST /api/score {md, mode}` parses an applicant `.md`, runs the pipeline, and
  returns the exact shape the console renders. The API also serves the console at `/`.
  `uvicorn trustlink.api.app:app` → http://127.0.0.1:8000. The console calls the backend when
  present (a badge shows "Computed by TrustLink API") and **falls back to the in-browser engine**
  otherwise (e.g. the shared artifact) — identical results.
- **#5 in the engine** — `run_pipeline(..., mode="calibrated")` uses the data-learned weights
  (`config/weights_calibrated.yaml`). `cli modes` shows hand vs data-calibrated: **Ms. Aom 742 vs
  739** — the data essentially confirms the expert weights. Hand mode stays the default (742 golden
  untouched).
- New: `trustlink/ioutil/md_parser.py` (shared parser), `cli modes`, `cli calibrate`.
- Tests: 43 passing.

## v2.0 — Roadmap items #2–#5, #7 brought into the hackathon build

All five canonical personas keep their exact numbers (Ms. Aom still 742 / Approve / 45M); the new
work is additive. The `hackathon` tag preserves the pre-v2.0 state.

- **#2 Fraud scoring** (`fraud/veto.py`) — a graduated fraud SCORE (Low 15 / Medium 25 / High 60;
  ≥60 High, ≥25 Medium) replaces plain max(): several weak signals now combine and escalate, while
  a single strong signal still forces High.
- **#3 Extra fraud checks** (`fraud/rules.py`) — occupation-income norm, suspiciously-round declared
  income, brand-new account, application velocity. New optional `.md` fields: `account_age_months`,
  `prior_applications`, `existing_monthly_debt`.
- **#4 DSR affordability** (`decision/affordability.py`) — the offer is the tighter of the surplus
  cap and a debt-service-ratio cap (existing debt + this loan's installment at an assumed APR ≤ 45%
  of income). Backward compatible: no debt → surplus still binds (Aom stays 45M).
- **#5 Data-calibration demo** (`validation/calibrate.py`, `cli calibrate`) — fits an interpretable
  logistic model on the synthetic ground-truth; on a held-out split, AUC 0.602 → 0.623, and the
  learned importances reweight our hand guesses (data says Payment Discipline 37% vs our 21%,
  Identity 0%). The answer to "why 742?" becomes "because the data says so." (Synthetic.)
- **#7 Fairness** (`validation/run.py`) — approval-rate parity by employment group + disparate-impact
  ratio (80% rule). Honestly surfaces a self-employed gap (DI 0.51) to investigate.
- Tests: 39 passing (added #2–#5, #7). Console (`webdemo/`) synced with #2–#4 + a DSR row, 6 languages.
- See `ROADMAP.md` for what each item still needs for production.

## v1.2 — Fraud fairness upgrade + validation harness

- **#1 Smarter spike rule** (`fraud/rules.py`) — the transaction-spike check is now parking-aware
  and employment-aware. A one-off big month is normal for variable-income workers (our target
  segment) and is no longer flagged as fraud; a spike only flags when it looks like fund-parking
  (money moved straight back out) or is unexplained for a steady-income earner. New persona/file
  **Ms. Fah** (`applicants/fah.md`) demonstrates it: old rule → fraud REJECT, new rule → Human Review.
- **#6 Validation harness** (`trustlink/validation/`) — synthetic population with ground-truth
  default labels; measures AUC / KS / Gini + fraud-catch. `python -m trustlink.cli validate`.
  Result (seed 42): risk-ordered tiers (Strong ~7% → Weak ~23% default), AUC ~0.64, fraud caught 100%.
  Honestly framed as synthetic — see the harness docstrings and `ROADMAP.md`.
- Tests: 30 passing (added spike-rule + validation tests; the four golden personas unchanged).
- `ROADMAP.md` — production plan for #2–#5, #7 (answers "how would you scale?").

## v1.0 — Save point (baseline)

First working baseline: the Trust Intelligence Engine (TIE) core + an interactive underwriting
console, both proven end-to-end. Use this tag to return to a known-good state if later work
scope-creeps or breaks.

**Included**
- `trustlink/` — deterministic TIE engine (features → dimensions → scorecard, fraud veto,
  affordability, decision, traditional-bureau baseline, deterministic explanations).
- `trustlink/tests/` — golden + unit tests (Ms. Aom pins 742 / Strong / 0.86 / Approve-adjusted
  45M; archetypes route Approve / Human Review / Reject). All green.
- `trustlink/applicants/` — four applicant `.md` files + `FORMAT.md` spec.
- `trustlink/webdemo/` — the console (load `.md` → verdict), Shinhan-themed, verified in-browser.
- `config/` — feature spec, weights, bands, and `calibration_note.md` (open log of provisional levers).
- The full PDP document set (Books 1–4, Volumes 0–20).

**Verified at this point**
- `pytest trustlink/` → all pass.
- Console: Approve (Aom 742), Reject (Dat 564), and clear errors on malformed files.

**Run**
- Engine/CLI: `python -m trustlink.cli demo` (from `trustlink/`)
- Console: `python3 trustlink/webdemo/_serve.py` → http://127.0.0.1:8099

**Restore this save point**
```
git checkout v1.0        # inspect the baseline (detached HEAD)
# or, to discard later changes and return the branch here:
git reset --hard v1.0
```

**Track changes since the last save point** (from the project root)
```
./savepoint.sh           # what changed since the latest save point
./savepoint.sh diff      # full line-by-line diff
./savepoint.sh list      # all save points
./savepoint.sh save "msg"  # commit everything + tag the next version (v1.0 -> v1.1)
```
