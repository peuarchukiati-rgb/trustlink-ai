# Production Roadmap — TrustLink AI

What the hackathon prototype deliberately leaves for production, why, and how we'd build it.
Use this to answer *"how would you scale / harden this?"* with specifics.

## Done in the prototype
- Deterministic, explainable Trust Intelligence Engine (scorecard + fraud veto + affordability).
- **#1** spike rule parking-/employment-aware (legit lumpy freelancer income no longer flagged).
- **#6** validation harness — synthetic ground-truth, tier separation + fair AUC + 100% fraud-catch.
- **#2** graduated fraud score (weak signals combine).  **#3** occupation-norm / round-number /
  new-account / velocity checks.  **#4** DSR affordability (existing debt + APR).
- **#5** data-calibration demo (`cli calibrate`): interpretable logistic on synthetic outcomes —
  AUC uplift + learned weights ("why 742? the data says so").
- **#7** fairness: approval parity by segment + min/max ratio (`cli validate`) — de-noised at N=4000
  (DI ~0.79), reframed as a monitored segment (employment isn't a protected class).
- **#8** approved-partner corroboration (`corroboration.py`): pay-slip + national-data-centre income
  cross-checked against Open-Banking inflow — lifts confidence on agreement, fraud-flags a conflict.
- **Regulatory sandbox surface**: scoped/revocable **consent** ledger + immutable **audit** trail +
  approved-**partner** registry (`api/audit.py`, `partners/`) — data use is authorised and attributable.

> #2–#5, #7, #8 are **prototyped on synthetic data** for the hackathon — they demonstrate the mechanism.
> What each still needs for PRODUCTION is below (this is the honest "how we scale" answer).

## Roadmap (post-hackathon)

### #2 — Fraud: combine weak signals into a graduated score
**Now:** fraud level = the single max-severity flag. **Next:** a fraud *score* that sums weighted
signals, while keeping hard vetoes for strong ones.
- **Pro:** catches "several small red flags together" that individually pass.
- **Con:** a summed score is less crisp than a rule and needs its own calibration.

### #3 — More fraud checks
Account age, repeat/duplicate applications, round-number patterns, declared-income-vs-occupation
norms, device/velocity signals.
- **Pro:** broader, more realistic coverage.
- **Con:** needs data fields we don't yet collect; each new rule adds false-positive risk — add with tests.

### #4 — Affordability: real DSR (debt-service ratio)
**Now:** a prudent cap on disposable surplus. **Next:** factor existing debts, interest, and
obligations into a true DSR.
- **Pro:** realistic offers; aligns with responsible-lending regulation.
- **Con:** requires debt/obligation data (bureau or declared) we don't collect yet.

### #5 — Calibrate from data, not by hand ★ (biggest lever)
**Now:** weights (25/20/15…) and band cut-points are expert-set and reverse-fit to one anchor
(Ms. Aom = 742). **Next:** with real lending outcomes, refit using **interpretable** models only —
WOE binning + logistic regression, or an Explainable Boosting Machine (EBM/GA2M).
- **Pro:** real predictive validity + defensible metrics (AUC/KS/Gini), and the model self-improves;
  keeps the additive, reason-code structure so explainability survives.
- **Con:** needs 12–24 months of matured outcomes; adds a modelling + monitoring pipeline.
- *This is why the validation AUC is "fair, not high" today — the bands aren't fit to a population yet.*

### #7 — Fairness / bias testing
Test decisions for disparate impact across protected groups; add reject-inference.
- **Pro:** protects the financial-inclusion mission and manages regulatory/reputational risk.
- **Con:** needs sensitive demographic data, handled carefully and compliantly.

## Also on deck (engineering)
- ✅ **FastAPI service** — DONE. `trustlink/api/` runs the real Python engine server-side
  (`POST /api/score`), serves the console, and the console falls back to in-browser when there is no
  backend. (More Volume-8 endpoints — consent, audit, human-review — still to add.)
- ✅ **#5 in the engine** — DONE. `mode="calibrated"` uses data-learned weights (`cli modes`).
- **LLM narration** — swap the deterministic explanation templates for an LLM *behind the same
  reason-code interface* (the LLM must never compute the score).
- **Persistence & audit** — move from in-memory to SQLite/Postgres with the immutable audit log.

## One-line honesty for the pitch
> "Today this is an explainable *mechanism* validated on synthetic data — not yet a statistically
> proven model. The path to proof (#5) is designed and ready; it just needs real outcomes."
