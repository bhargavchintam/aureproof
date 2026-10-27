# SPDX-FileCopyrightText: 2026 Bindu Bhargava R Chintam
# SPDX-License-Identifier: Apache-2.0
"""Statistics (pure core): exact sign-flip test, Wilson intervals, the decision gate."""

from aureproof.stats.decide import decide
from aureproof.stats.permutation import MAX_CLUSTERS, SignFlipResult, min_clusters, sign_flip
from aureproof.stats.wilson import wilson

__all__ = ["MAX_CLUSTERS", "SignFlipResult", "decide", "min_clusters", "sign_flip", "wilson"]
