# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Exact paired sign-flip permutation test with a test-inversion interval.

All arithmetic is exact (``Fraction``). For cluster differences ``d`` and a
hypothesized effect ``delta0``, flipping the signs of a subset ``S`` gives a sum at
least as large as the observed one exactly when ``mean(d over S) <= delta0``. So
the one-sided p-value is ``(1 + #{non-empty S : mean_S(d) <= delta0}) / 2^k``, and
the interval bounds are order statistics of the ``2^k - 1`` subset means
(specs/decision §4).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

MAX_CLUSTERS = 20  # 2^20 subsets; beyond this the exact enumeration is refused


@dataclass(frozen=True, slots=True)
class SignFlipResult:
    k: int
    mean: Fraction
    p_two_sided: Fraction  # at delta0 = 0
    lower: Fraction | None  # None: unbounded at this alpha (too few clusters)
    upper: Fraction | None


def min_clusters(alpha: float) -> int:
    """Smallest k with floor(alpha * 2^k) >= 1, i.e. any finite bound exists."""
    k = 1
    while math.floor(alpha * 2**k) < 1:
        k += 1
    return k


def _subset_means(d: Sequence[Fraction]) -> list[Fraction]:
    means: list[Fraction] = []
    for size in range(1, len(d) + 1):
        for subset in combinations(d, size):
            means.append(Fraction(sum(subset, Fraction(0)), size))
    return sorted(means)


def p_two_sided(d: Sequence[Fraction]) -> Fraction:
    """P(|sum of sign-flipped d| >= |sum d|) over all 2^k sign assignments."""
    observed = abs(sum(d, Fraction(0)))
    k = len(d)
    hits = 0
    for mask in range(2**k):
        total: Fraction = sum(((-x if mask >> i & 1 else x) for i, x in enumerate(d)), Fraction(0))
        hits += abs(total) >= observed
    return Fraction(hits, 2**k)


def sign_flip(d: Sequence[Fraction], alpha: float) -> SignFlipResult:
    """Exact test and the (1 - 2*alpha) interval for the mean of cluster differences."""
    k = len(d)
    if not 1 <= k <= MAX_CLUSTERS:
        raise ValueError(f"need 1..{MAX_CLUSTERS} clusters, got {k}")
    mean = Fraction(sum(d, Fraction(0)), k)
    r = math.floor(alpha * 2**k)  # rejected iff #{subset means <= delta0} <= r - 1
    means = _subset_means(d)
    lower = means[r - 1] if r >= 1 else None
    upper = means[len(means) - r] if r >= 1 else None
    return SignFlipResult(k, mean, p_two_sided(d), lower, upper)
