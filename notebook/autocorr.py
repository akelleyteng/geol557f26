"""Correlation significance corrected for serial correlation in two time series.

Neighbouring points on an interpolated ice-core grid are far from independent,
so the usual correlation test, which treats every point as new information,
overstates significance. These helpers replace the sample size with an
effective sample size based on lag-1 autocorrelation (Bretherton et al.,
1999, J. Climate 12, 1990-2009). An AR(1) model is the standard first-order
correction. It does not capture longer memory, so the adjusted p-values are
still optimistic rather than exact.
"""

import numpy as np
from scipy import stats

MIN_TESTABLE_N = 2


def lag1_autocorr(values, ages, step):
    """Correlation between each value and the next one, one grid step later.

    Pairs that straddle a gap in the grid (ages more than one step apart) are
    skipped, so the gaps don't count as neighbours.
    """
    values = np.asarray(values, dtype=float)
    ages = np.asarray(ages)
    is_neighbour = np.diff(ages) == step
    return np.corrcoef(values[:-1][is_neighbour], values[1:][is_neighbour])[0, 1]


def effective_n_pair(n, r1_x, r1_y):
    """Effective sample size for correlating two AR(1) series (Bretherton eq. 31)."""
    product = r1_x * r1_y
    return min(n, n * (1 - product) / (1 + product))


def pearson_p_with_n(r, n_eff):
    """Two-sided p-value for Pearson r, using n_eff instead of the raw count."""
    if n_eff <= MIN_TESTABLE_N:
        raise ValueError(f"effective sample size {n_eff:.1f} is too small to test")
    df = n_eff - 2
    t = r * np.sqrt(df / (1 - r**2))
    return 2 * stats.t.sf(abs(t), df)
