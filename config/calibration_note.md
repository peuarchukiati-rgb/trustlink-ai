# Calibration note — open log of provisional levers

**Decision (product owner):** the engine is calibrated so Ms. Aom scores exactly **742 / Strong /
0.86**, matching every design document — AND the derivation is shown transparently (per-dimension
breakdown in the CLI and in `PipelineResult.dimensions`). No hidden fudge factors: each dimension
sub-score has an honest justification. The levers below are **provisional** and should be **refit
from real outcome data** post-hackathon; the 742 anchor is one calibration point, not a fit.

## Levers

1. **Financial Trend: flat income → sub-score 52** (`config/bands.yaml`, band `[-0.03, 0.03)`).
   The single biggest lever. flat→60 lifts the score to ~748; flat→50 drops it to ~739.
   Choice: "cannot yet establish a trend over a short window" is treated as neutral-low (52),
   not routed into confidence. Defensible either way — revisit with real data.

2. **Band cut-points** (`config/bands.yaml`). Cut-points were chosen so Ms. Aom's actual feature
   values land mid-band (e.g. Income Stability ISI ≈ 0.825 → the `[0.75, 0.86)` → 70 band).
   Treat the anchor as ONE calibration point; do not over-fit the bands to a single borrower.

3. **Confidence split 0.40 / 0.60** (`config/weights.yaml`, `confidence.breadth_weight`).
   Chosen so a thin-but-clean file lands at 0.86: `0.40·breadth(≈0.647) + 0.60·consistency(1.0)`.
   The 0.60 weight on consistency is what keeps thin-file confidence high (the "missing ≠ bad"
   principle in numbers).

4. **Affordability: 0.60 surplus utilisation + 5,000,000 rounding step**
   (`trustlink/decision/affordability.py`). These two constants *are* the "adjusted amount" story:
   `0.60 · 6.3M · 12 = 45.36M → 45M`. At 0.65 utilisation the cap is ~49M and no adjustment
   happens, which would remove the 50M→45M narrative. Flagged prominently.

5. **Weight handling: divide by Σweights (=95)** rather than rounding to messy percentages
   (`trustlink/scoring/scorecard.py`). This is exact and traceable to the doc — no arbitrariness.

## Doc inconsistency reproduced deliberately

Volume 8's Open-Banking mock reports `average_monthly_inflow = 18,500,000`, which equals Ms. Aom's
declared income — so the "declared slightly above observed" income-mismatch flag that V8 also shows
does **not** fire here (there is no gap). Fraud is `Low` either way, so the anchor is unaffected.
The mismatch rule is implemented and exercised by persona D.
