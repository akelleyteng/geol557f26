"""Cursor-following magnifier lens for Plotly figures shown in a notebook.

The lens is a small second plot that follows the pointer and shows the
traces of the panel underneath it at a higher magnification. The main
figure's axes never change, so readers keep the full-record context.

The lens runs as plain JavaScript in the cell's HTML output, so it works
in Jupyter, VS Code and Colab (and in an exported HTML file) without a
live kernel. Static exports such as PDF cannot run it; they show the
plain-text fallback instead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from IPython.display import display

LENS_SIZE_PX = (340, 220)
MIN_ZOOM_MULTIPLIER = 0.125
MAX_ZOOM_MULTIPLIER = 64
DEFAULT_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Lens:
    """Magnification for one panel, keyed by that panel's x-axis id."""

    x_zoom: float
    y_zoom: float = 1.0
    x_unit: str = ""
    x_decimals: int = 1


def piecewise_linear_vertices(x, y, tol=DEFAULT_TOLERANCE):
    """Drop points that lie on a straight line between their neighbours.

    Plotly draws straight segments between points, so for a series that is
    piecewise linear (like a difference of linearly interpolated values) the
    returned vertices draw exactly the same line with far fewer points. NaN
    gaps are kept as single NaN separators so lines still break there.

    Raises ValueError if dropping points would move the line by more than
    `tol`, which means the input was not piecewise linear.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or x.shape != y.shape:
        raise ValueError("x and y must be 1-D arrays of the same length")
    if len(x) < 3:
        return x.copy(), y.copy()

    finite = np.isfinite(y)
    prev_finite = np.r_[False, finite[:-1]]
    next_finite = np.r_[finite[1:], False]
    is_run_end = finite & ~(prev_finite & next_finite)

    slope = np.diff(y) / np.diff(x)
    bends = ~np.isclose(slope[1:], slope[:-1], rtol=0, atol=tol)
    is_bend = np.r_[False, bends, False] & finite & prev_finite & next_finite

    keep = np.flatnonzero(is_run_end | is_bend)

    # Points in the same finite run share the count of NaNs before them.
    run_id = np.cumsum(~finite)[keep]
    starts_new_run = np.r_[False, np.diff(run_id) != 0]

    out_x, out_y = [], []
    for i, new_run in zip(keep, starts_new_run):
        if new_run:
            out_x.append(np.nan)
            out_y.append(np.nan)
        out_x.append(x[i])
        out_y.append(y[i])
    out_x, out_y = np.array(out_x), np.array(out_y)

    _check_reconstruction(x, y, finite, out_x, out_y, tol)
    return out_x, out_y


def _check_reconstruction(x, y, finite, vx, vy, tol):
    # Interpolate each run separately so values never bridge a NaN gap.
    run_of_point = np.cumsum(~finite)
    vertex_runs = np.cumsum(np.isnan(vy))
    run_ids = np.unique(run_of_point[finite])
    for k, run in enumerate(run_ids):
        in_run = finite & (run_of_point == run)
        vx_run = vx[(vertex_runs == k) & ~np.isnan(vy)]
        vy_run = vy[(vertex_runs == k) & ~np.isnan(vy)]
        order = np.argsort(vx_run)
        rebuilt = np.interp(x[in_run], vx_run[order], vy_run[order])
        error = np.max(np.abs(rebuilt - y[in_run]))
        if error > tol:
            raise ValueError(
                f"series is not piecewise linear within tol={tol} "
                f"(max error {error:.3g}); plot the full data instead"
            )


def magnifier_html(
    fig: go.Figure,
    lenses: Mapping[str, Lens],
    *,
    title: str,
    lens_size: tuple[int, int] = LENS_SIZE_PX,
    include_plotlyjs: str | bool = "cdn",
) -> str:
    """Return HTML for `fig` with a magnifier lens on each panel in `lenses`."""
    panels = [_panel_config(fig, x_id, lens) for x_id, lens in lenses.items()]

    fig = go.Figure(fig)
    fig.update_layout(dragmode=False, hovermode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    config = {
        "panels": panels,
        "size": list(lens_size),
        "minMult": MIN_ZOOM_MULTIPLIER,
        "maxMult": MAX_ZOOM_MULTIPLIER,
    }
    plot = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={"staticPlot": True, "responsive": True},
        post_script=_LENS_JS.replace("__CFG__", json.dumps(config)),
    )
    label = (
        f"{title}. Interactive: move the pointer over a panel, or focus "
        "and use the arrow keys, to magnify. Plus and minus change zoom."
    )
    return _WRAPPER_HTML.format(
        css=_LENS_CSS, label=_escape_attr(label), plot=plot
    )


def display_with_magnifier(
    fig: go.Figure,
    lenses: Mapping[str, Lens],
    *,
    title: str,
    fallback_text: str,
    **kwargs,
) -> None:
    """Show the magnifier figure; static exports show `fallback_text`."""
    html = magnifier_html(fig, lenses, title=title, **kwargs)
    display({"text/html": html, "text/plain": fallback_text}, raw=True)


def _panel_config(fig: go.Figure, x_id: str, lens: Lens) -> dict:
    y_ids = {t.yaxis or "y" for t in fig.data if (t.xaxis or "x") == x_id}
    if len(y_ids) != 1:
        raise ValueError(
            f"x-axis {x_id!r} must carry traces on exactly one y-axis, "
            f"found {sorted(y_ids)}"
        )
    if lens.x_zoom <= 0 or lens.y_zoom <= 0:
        raise ValueError("zoom factors must be positive")
    y_id = y_ids.pop()
    return {
        "xId": x_id,
        "xLayout": "xaxis" + x_id[1:],
        "yLayout": "yaxis" + y_id[1:],
        "xZoom": lens.x_zoom,
        "yZoom": lens.y_zoom,
        "xUnit": lens.x_unit,
        "xDecimals": lens.x_decimals,
    }


def _escape_attr(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace('"', "&quot;")
        .replace("<", "&lt;").replace(">", "&gt;")
    )


_WRAPPER_HTML = """<style>{css}</style>
<div class="mgf-root" tabindex="0" role="group" aria-label="{label}">
  <div class="mgf-bar">
    <span class="mgf-hint">Hover to magnify. Focus and use arrow keys; Esc hides.</span>
    <span class="mgf-zoom">
      Lens zoom
      <button type="button" class="mgf-out" aria-label="Decrease lens zoom">&minus;</button>
      <output class="mgf-level" aria-live="polite"></output>
      <button type="button" class="mgf-in" aria-label="Increase lens zoom">+</button>
    </span>
  </div>
  <div class="mgf-stage">{plot}</div>
</div>
"""

_LENS_CSS = """
.mgf-root { --mgf-ink: #52514e; --mgf-muted: #898781; --mgf-line: #c9c7bf;
  --mgf-bg: #ffffff; --mgf-accent: #2a78d6;
  font: 13px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif;
  color: var(--mgf-ink); background: var(--mgf-bg); border-radius: 6px; }
.mgf-root:focus-visible { outline: 2px solid var(--mgf-accent); outline-offset: 2px; }
.mgf-bar { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center;
  justify-content: space-between; padding: 6px 8px; }
.mgf-hint { color: var(--mgf-muted); }
.mgf-zoom { display: inline-flex; align-items: center; gap: 6px; }
.mgf-zoom button { width: 28px; height: 28px; border: 1px solid var(--mgf-line);
  border-radius: 4px; background: var(--mgf-bg); color: var(--mgf-ink);
  font-size: 16px; line-height: 1; cursor: pointer; }
.mgf-zoom button:focus-visible { outline: 2px solid var(--mgf-accent); }
.mgf-level { min-width: 3.5em; text-align: center; font-variant-numeric: tabular-nums; }
.mgf-stage { position: relative; }
.mgf-lens { position: absolute; display: none; pointer-events: none; z-index: 10;
  background: var(--mgf-bg); border: 1px solid var(--mgf-line); border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.18); overflow: hidden; }
.mgf-lens-label { position: absolute; top: 4px; left: 8px; right: 8px; z-index: 1;
  font-size: 11px; color: var(--mgf-ink); font-variant-numeric: tabular-nums; }
.mgf-indicator { position: absolute; display: none; pointer-events: none; z-index: 9;
  border: 1.5px solid var(--mgf-ink); background: rgba(42, 120, 214, 0.08); }
"""

# Reads Plotly's computed axis geometry (_offset, _length, range) to map
# pointer pixels to data values; those fields have been stable across
# Plotly.js 1.x-3.x and there is no public equivalent.
_LENS_JS = r"""
(function () {
  const gd = document.getElementById('{plot_id}');
  const root = gd.closest('.mgf-root');
  const stage = root.querySelector('.mgf-stage');
  const level = root.querySelector('.mgf-level');
  const CFG = __CFG__;
  const [W, H] = CFG.size;
  const GAP_PX = 12;
  const KEY_STEP = 0.02, KEY_STEP_LARGE = 0.1;

  const indicator = document.createElement('div');
  indicator.className = 'mgf-indicator';
  stage.appendChild(indicator);

  let mult = 1;
  let cursor = null;           // {px, py} relative to the plot div
  let activePanel = CFG.panels[0];
  let frame = null;

  const axesOf = p => ({ xa: gd._fullLayout[p.xLayout], ya: gd._fullLayout[p.yLayout] });
  const inside = (a, pix) => pix >= a._offset && pix <= a._offset + a._length;
  const toData = (a, pix, isY) => {
    const t = (pix - a._offset) / a._length, r = a.range;
    return isY ? r[1] - t * (r[1] - r[0]) : r[0] + t * (r[1] - r[0]);
  };
  const fmtZoom = z => (z >= 10 ? Math.round(z) : +z.toFixed(1)) + '×';

  function panelAt(px, py) {
    return CFG.panels.find(p => {
      const { xa, ya } = axesOf(p);
      return xa && ya && inside(xa, px) && inside(ya, py);
    });
  }

  function ensureLens(p) {
    if (p.lens) return p.lens;
    const box = document.createElement('div');
    box.className = 'mgf-lens';
    box.style.width = W + 'px';
    box.style.height = H + 'px';
    box.setAttribute('aria-hidden', 'true');
    const label = document.createElement('div');
    label.className = 'mgf-lens-label';
    const plot = document.createElement('div');
    box.append(label, plot);
    stage.appendChild(box);
    const traces = gd.data
      .filter(t => (t.xaxis || 'x') === p.xId)
      .map(t => Object.assign({}, t, {
        xaxis: 'x', yaxis: 'y', showlegend: false, hoverinfo: 'skip', legend: undefined
      }));
    const { xa, ya } = axesOf(p);
    const axis = { showgrid: true, gridcolor: '#e1e0d9', zeroline: false,
      tickfont: { size: 10, color: '#898781' }, linecolor: '#898781' };
    Plotly.newPlot(plot, traces, {
      width: W, height: H, showlegend: false,
      margin: { l: 42, r: 10, t: 22, b: 26 },
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      xaxis: Object.assign({ range: xa.range.slice() }, axis),
      yaxis: Object.assign({ range: ya.range.slice() }, axis)
    }, { staticPlot: true });
    p.lens = { box, label, plot };
    return p.lens;
  }

  function hide() {
    indicator.style.display = 'none';
    CFG.panels.forEach(p => { if (p.lens) p.lens.box.style.display = 'none'; });
  }

  function render() {
    frame = null;
    const p = cursor && panelAt(cursor.px, cursor.py);
    if (!p) { hide(); return; }
    activePanel = p;
    updateLevel();
    const { xa, ya } = axesOf(p);
    const xz = p.xZoom * mult, yz = p.yZoom;
    const cx = toData(xa, cursor.px, false), cy = toData(ya, cursor.py, true);
    const hx = (xa.range[1] - xa.range[0]) / 2 / xz;
    const hy = (ya.range[1] - ya.range[0]) / 2 / yz;

    const lens = ensureLens(p);
    CFG.panels.forEach(q => { if (q !== p && q.lens) q.lens.box.style.display = 'none'; });
    Plotly.relayout(lens.plot, { 'xaxis.range': [cx - hx, cx + hx], 'yaxis.range': [cy - hy, cy + hy] });
    lens.label.textContent = fmtZoom(xz) + '  ·  ' + cx.toFixed(p.xDecimals) + ' ' + p.xUnit;

    const g = gd.getBoundingClientRect(), s = stage.getBoundingClientRect();
    const ox = g.left - s.left, oy = g.top - s.top;
    const iw = Math.max(2, xa._length / xz), ih = Math.max(2, ya._length / yz);
    Object.assign(indicator.style, {
      display: 'block', width: iw + 'px', height: ih + 'px',
      left: ox + cursor.px - iw / 2 + 'px', top: oy + cursor.py - ih / 2 + 'px'
    });

    // Sit beside the magnified region, flipping left near the right edge.
    let left = cursor.px + iw / 2 + GAP_PX;
    if (left + W > g.width) left = cursor.px - iw / 2 - GAP_PX - W;
    left = Math.max(0, left);
    const top = Math.min(Math.max(0, cursor.py - H / 2), Math.max(0, g.height - H));
    Object.assign(lens.box.style, { display: 'block', left: ox + left + 'px', top: oy + top + 'px' });
  }

  const schedule = () => { if (!frame) frame = requestAnimationFrame(render); };

  function updateLevel() { level.textContent = fmtZoom(activePanel.xZoom * mult); }

  function zoom(factor) {
    mult = Math.min(CFG.maxMult, Math.max(CFG.minMult, mult * factor));
    updateLevel();
    schedule();
  }

  gd.addEventListener('pointermove', e => {
    const r = gd.getBoundingClientRect();
    cursor = { px: e.clientX - r.left, py: e.clientY - r.top };
    schedule();
  });
  gd.addEventListener('pointerleave', () => { cursor = null; schedule(); });
  root.querySelector('.mgf-in').addEventListener('click', () => zoom(2));
  root.querySelector('.mgf-out').addEventListener('click', () => zoom(0.5));

  const ARROWS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  root.addEventListener('keydown', e => {
    if (e.key === '+' || e.key === '=') zoom(2);
    else if (e.key === '-' || e.key === '_') zoom(0.5);
    else if (e.key === 'Escape') { cursor = null; schedule(); }
    else if (ARROWS[e.key]) {
      const { xa, ya } = axesOf(activePanel);
      if (!cursor || !panelAt(cursor.px, cursor.py)) {
        cursor = { px: xa._offset + xa._length / 2, py: ya._offset + ya._length / 2 };
      }
      const step = e.shiftKey ? KEY_STEP_LARGE : KEY_STEP;
      const [dx, dy] = ARROWS[e.key];
      cursor = { px: cursor.px + dx * step * xa._length, py: cursor.py + dy * step * ya._length };
      if (!panelAt(cursor.px, cursor.py)) {
        // Step into the neighbouring panel instead of losing the lens in the gap.
        const next = dx === 0 ? null : CFG.panels.find(p => {
          const a = axesOf(p).xa;
          return p !== activePanel && (dx > 0 ? a._offset > xa._offset : a._offset < xa._offset);
        });
        if (next) {
          const a = axesOf(next);
          cursor = { px: dx > 0 ? a.xa._offset + 1 : a.xa._offset + a.xa._length - 1,
                     py: Math.min(Math.max(cursor.py, a.ya._offset), a.ya._offset + a.ya._length) };
        } else {
          cursor = { px: Math.min(Math.max(cursor.px, xa._offset), xa._offset + xa._length),
                     py: Math.min(Math.max(cursor.py, ya._offset), ya._offset + ya._length) };
        }
      }
      schedule();
    } else return;
    e.preventDefault();
  });

  updateLevel();
})();
"""
