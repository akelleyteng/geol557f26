import numpy as np
import pytest
from scipy import stats

from autocorr import (
    effective_n_pair,
    lag1_autocorr,
    pearson_p_with_n,
    regression_variance_inflation,
)


def ar1(phi, n, seed):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + rng.standard_normal()
    return x


def test_should_recover_the_coefficient_of_an_ar1_series():
    x = ar1(0.9, 20_000, seed=1)
    ages = np.arange(len(x)) * 1000

    assert lag1_autocorr(x, ages, step=1000) == pytest.approx(0.9, abs=0.02)


def test_should_ignore_pairs_that_straddle_a_gap_in_the_grid():
    ages = np.array([0, 1000, 2000, 3000, 9000, 10000, 11000])
    values = np.array([0.0, 1.0, 3.0, 2.0, 50.0, 4.0, 6.0])
    expected = np.corrcoef([0, 1, 3, 50, 4], [1, 3, 2, 4, 6])[0, 1]

    assert lag1_autocorr(values, ages, step=1000) == pytest.approx(expected)


def test_should_leave_paired_sample_size_unchanged_without_autocorrelation():
    assert effective_n_pair(800, 0.0, 0.9) == pytest.approx(800)


def test_should_not_grow_paired_sample_size_for_opposite_sign_autocorrelation():
    assert effective_n_pair(800, -0.5, 0.5) == pytest.approx(800)


def test_should_shrink_paired_sample_size_by_the_product_of_both_autocorrelations():
    assert effective_n_pair(800, 0.9, 0.8) == pytest.approx(800 * 0.28 / 1.72)


def test_should_match_scipy_pearson_p_when_no_adjustment_is_applied():
    rng = np.random.default_rng(2)
    x = rng.standard_normal(50)
    y = 0.3 * x + rng.standard_normal(50)
    r, p = stats.pearsonr(x, y)

    assert pearson_p_with_n(r, 50) == pytest.approx(p)


def test_should_give_a_larger_pearson_p_for_a_smaller_effective_sample():
    assert pearson_p_with_n(0.5, 10) > pearson_p_with_n(0.5, 100)


def test_should_reject_an_effective_sample_too_small_to_test():
    with pytest.raises(ValueError):
        pearson_p_with_n(0.5, 2)


def test_should_not_inflate_regression_variance_without_autocorrelation():
    assert regression_variance_inflation(0.0, 0.0) == pytest.approx((1.0, 1.0))


def test_should_inflate_mean_by_residual_and_slope_by_product_autocorrelation():
    mean_factor, slope_factor = regression_variance_inflation(0.9, 0.8)

    assert mean_factor == pytest.approx(1.8 / 0.2)
    assert slope_factor == pytest.approx(1.72 / 0.28)
