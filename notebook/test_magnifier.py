import numpy as np
import plotly.graph_objects as go
import pytest

from magnifier import Lens, magnifier_html, piecewise_linear_vertices


def rebuild(vx, vy, x):
    """Evaluate the drawn polyline at x, treating NaN as a line break."""
    out = np.full_like(x, np.nan, dtype=float)
    runs = np.split(np.arange(len(vx)), np.flatnonzero(np.isnan(vy)))
    for idx in runs:
        idx = idx[~np.isnan(vy[idx])]
        if len(idx) == 0:
            continue
        lo, hi = sorted((vx[idx[0]], vx[idx[-1]]))
        span = (x >= lo) & (x <= hi)
        order = np.argsort(vx[idx])
        out[span] = np.interp(x[span], vx[idx][order], vy[idx][order])
    return out


def test_should_keep_only_bends_of_a_piecewise_linear_series():
    x = np.arange(0, 101, dtype=float)
    y = np.interp(x, [0, 30, 60, 100], [0, 15, -5, 10])

    vx, vy = piecewise_linear_vertices(x, y)

    assert list(vx) == [0, 30, 60, 100]
    np.testing.assert_allclose(rebuild(vx, vy, x), y, atol=1e-9)


def test_should_break_lines_at_nan_gaps_with_one_separator():
    x = np.arange(10, dtype=float)
    y = np.array([0, 1, 2, np.nan, np.nan, 5, 5, 5, np.nan, 9], dtype=float)

    vx, vy = piecewise_linear_vertices(x, y)

    assert np.isnan(vy).sum() == 2
    np.testing.assert_array_equal(vx[~np.isnan(vy)], [0, 2, 5, 7, 9])
    finite = np.isfinite(y)
    np.testing.assert_allclose(rebuild(vx, vy, x)[finite], y[finite])


def test_should_match_full_data_for_interpolated_window_differences():
    rng = np.random.default_rng(0)
    ages = np.sort(rng.uniform(0, 5000, 40))
    values = rng.normal(250, 20, 40)
    starts = np.arange(ages.min(), ages.max() - 100)
    y = np.interp(starts, ages, values) - np.interp(starts + 100, ages, values)

    vx, vy = piecewise_linear_vertices(starts, y)

    assert len(vx) < len(starts) / 10
    np.testing.assert_allclose(rebuild(vx, vy, starts), y, atol=1e-6)


def test_should_reject_a_curve_that_is_not_piecewise_linear():
    # Each bend is below tol, but dropping them all bows the line badly.
    x = np.arange(1000, dtype=float)

    with pytest.raises(ValueError, match="not piecewise linear"):
        piecewise_linear_vertices(x, 1e-3 * x**2, tol=1e-2)


def test_should_reject_mismatched_lengths():
    with pytest.raises(ValueError):
        piecewise_linear_vertices([1, 2, 3], [1, 2])


def two_panel_figure():
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], xaxis="x", yaxis="y")
    fig.add_scatter(x=[0, 1], y=[1, 0], xaxis="x2", yaxis="y2")
    fig.update_layout(xaxis2={"anchor": "y2"}, yaxis2={"anchor": "x2"})
    return fig


def test_should_embed_one_lens_config_per_panel_and_lock_main_axes():
    html = magnifier_html(
        two_panel_figure(),
        {"x": Lens(x_zoom=10, x_unit="ka BP"), "x2": Lens(x_zoom=3, y_zoom=2)},
        title="Figure X",
    )

    assert '"xLayout": "xaxis2", "yLayout": "yaxis2"' in html
    assert '"xZoom": 10' in html and '"yZoom": 2' in html
    assert "{plot_id}" not in html and "__CFG__" not in html
    assert '"staticPlot": true' in html
    assert 'aria-label="Figure X. Interactive' in html


def test_should_reject_lens_on_axis_without_traces():
    with pytest.raises(ValueError, match="exactly one y-axis"):
        magnifier_html(two_panel_figure(), {"x3": Lens(x_zoom=2)}, title="t")
