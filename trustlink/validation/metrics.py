"""Discrimination metrics for a credit score: AUC, KS, Gini.

Convention: `default` is 1 for a bad outcome, 0 for good. A HIGHER score should mean LOWER default
risk, so a well-ordered score gives AUC > 0.5 (0.5 = random, 1.0 = perfect separation).
"""
from __future__ import annotations


def auc(scores: list[float], defaults: list[int]) -> float:
    """P(score of a random good > score of a random bad), via average ranks (handles ties)."""
    n = len(scores)
    ng = defaults.count(0)
    nb = n - ng
    if ng == 0 or nb == 0:
        return float("nan")
    order = sorted(range(n), key=lambda i: scores[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0            # 1-based average rank for the tie group
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    sum_ranks_good = sum(ranks[i] for i in range(n) if defaults[i] == 0)
    return (sum_ranks_good - ng * (ng + 1) / 2.0) / (ng * nb)


def ks(scores: list[float], defaults: list[int]) -> float:
    """Kolmogorov–Smirnov: max gap between cumulative good and bad score distributions."""
    ng = defaults.count(0)
    nb = len(defaults) - ng
    if ng == 0 or nb == 0:
        return float("nan")
    cum_g = cum_b = 0.0
    best = 0.0
    for _s, d in sorted(zip(scores, defaults)):
        if d == 1:
            cum_b += 1
        else:
            cum_g += 1
        best = max(best, abs(cum_b / nb - cum_g / ng))
    return best


def gini(auc_value: float) -> float:
    return 2.0 * auc_value - 1.0
