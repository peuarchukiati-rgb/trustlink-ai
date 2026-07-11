"""#5 — data-calibration demo (synthetic).

Shows the METHOD that turns "we hand-set the weights" into "the data set the weights":
fit an interpretable logistic regression on the six dimension sub-scores against the synthetic
ground-truth defaults, then compare — on a held-out test split —
  (a) the hand-set weighted Trust Score, versus
  (b) the data-calibrated model,
by AUC, and show which dimensions the DATA says matter most vs our hand guesses.

Pure Python (no ML libs). Logistic regression stays fully interpretable (linear weights).
Honest framing: synthetic data — this demonstrates the calibration mechanism and the uplift it
would bring; real magnitudes require real lending outcomes.
"""
from __future__ import annotations

import math
import random

from ..engine import run_pipeline
from ..features.compute import compute_features
from ..versioning import load_weights
from . import metrics
from .population import AS_OF, make_case

DIMS = ["income_stability", "payment_discipline", "savings_behaviour",
        "financial_trend", "lifestyle_stability", "identity_trust"]
# the raw continuous feature behind each dimension (the model learns from these, un-banded)
FEATURES = ["income_stability_index", "payment_consistency", "saving_ratio",
            "income_growth_rate", "lifestyle_stability_index", "identity_confidence"]


def _dataset(n: int, seed: int):
    """X = raw continuous features (data-calibrated model); hand = the banded Trust Score."""
    rng = random.Random(seed)
    X, y, hand = [], [], []
    for i in range(n):
        borrower, app, events, default, _fraud = make_case(rng, i)
        r = run_pipeline(borrower, app, events, AS_OF)
        fv = compute_features(borrower, app, events, AS_OF)
        X.append([fv.values[f] for f in FEATURES])
        y.append(default)
        hand.append(r.trust_score)
    return X, y, hand


def _standardize(X, means=None, stds=None):
    n, m = len(X), len(X[0])
    if means is None:
        means = [sum(row[j] for row in X) / n for j in range(m)]
        stds = []
        for j in range(m):
            v = sum((row[j] - means[j]) ** 2 for row in X) / n
            s = math.sqrt(v)
            stds.append(s if s > 1e-6 else 1.0)   # constant feature -> std 1 so it standardises to ~0
    Z = [[(row[j] - means[j]) / stds[j] for j in range(m)] for row in X]
    return Z, means, stds


def _sigmoid(z: float) -> float:
    if z < -30:
        return 0.0
    if z > 30:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def _train_logistic(X, y, epochs=500, lr=0.3, l2=0.001):
    m, n = len(X[0]), len(X)
    w = [0.0] * m
    b = 0.0
    for _ in range(epochs):
        gw = [0.0] * m
        gb = 0.0
        for xi, yi in zip(X, y):
            p = _sigmoid(sum(w[j] * xi[j] for j in range(m)) + b)
            err = p - yi
            for j in range(m):
                gw[j] += err * xi[j]
            gb += err
        for j in range(m):
            w[j] -= lr * (gw[j] / n + l2 * w[j])
        b -= lr * gb / n
    return w, b


def run_calibration(n: int = 1000, seed: int = 42) -> dict:
    X, y, hand = _dataset(n, seed)
    cut = int(n * 0.7)
    Xtr, ytr, Xte, yte = X[:cut], y[:cut], X[cut:], y[cut:]
    hand_te = hand[cut:]

    Ztr, means, stds = _standardize(Xtr)
    Zte, _, _ = _standardize(Xte, means, stds)
    w, b = _train_logistic(Ztr, ytr)

    # model "trust-like" score = 1 - P(default); higher = safer
    model_te = [1.0 - _sigmoid(sum(w[j] * Zte[i][j] for j in range(len(w))) + b) for i in range(len(Zte))]

    auc_hand = metrics.auc(hand_te, yte)
    auc_model = metrics.auc(model_te, yte)

    # interpretable importance: |standardised weight| normalised to %
    abs_w = [abs(v) for v in w]
    tot = sum(abs_w) or 1.0
    hand_weights = load_weights()["weights"]
    hand_tot = sum(hand_weights.values())
    importance = []
    for j, d in enumerate(DIMS):
        importance.append({
            "dimension": d,
            "hand_pct": 100.0 * hand_weights.get(d, 0) / hand_tot,
            "data_pct": 100.0 * abs_w[j] / tot,
        })
    return {
        "n": n, "seed": seed, "test_n": len(yte),
        "auc_hand": auc_hand, "auc_model": auc_model, "uplift": auc_model - auc_hand,
        "importance": importance,
    }


def main(argv=None) -> int:
    import sys
    argv = argv if argv is not None else sys.argv[1:]
    n = int(argv[0]) if len(argv) > 0 else 1000
    seed = int(argv[1]) if len(argv) > 1 else 42
    res = run_calibration(n, seed)
    print("=" * 64)
    print(f"  #5 Data-calibration on SYNTHETIC data (N={res['n']}, test={res['test_n']})")
    print("=" * 64)
    print(f"  AUC — hand-set weights   : {res['auc_hand']:.3f}")
    print(f"  AUC — data-calibrated    : {res['auc_model']:.3f}   ({res['uplift']:+.3f})")
    print()
    print("  Dimension importance — what WE guessed vs what the DATA says:")
    print(f"    {'dimension':22} {'hand-set':>9} {'data':>9}")
    for row in res["importance"]:
        print(f"    {row['dimension']:22} {row['hand_pct']:8.0f}% {row['data_pct']:8.0f}%")
    print()
    print("  => The weights need not be hand-picked. Fed real outcomes, the engine LEARNS them —")
    print("     keeping the same explainable additive form. (Synthetic demo; real data required.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
