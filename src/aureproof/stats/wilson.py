# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Wilson score interval for a binomial proportion (per configuration)."""

from __future__ import annotations

import math
from statistics import NormalDist


def wilson(successes: int, trials: int, alpha: float) -> tuple[float, float] | None:
    """The (1 - 2*alpha) Wilson interval, or None when there are no trials."""
    if trials == 0:
        return None
    if not 0 <= successes <= trials:
        raise ValueError("successes must be within 0..trials")
    z = NormalDist().inv_cdf(1 - alpha)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)
