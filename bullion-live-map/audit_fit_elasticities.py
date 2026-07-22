#!/usr/bin/env python3
"""One-off audit: fit the two elasticity coefficients that CAN be fit from
data.json (both driver and target are daily series present in the file).

This is NOT part of the daily pipeline. It exists to check two hardcoded
scenario magnitudes against the data, so their provenance tier can be set
honestly. Run it, read the report, decide per cell:

  * ELASTICITY.ffr.vix_add  = 1.10    (points of VIX per +1pp of fed funds)
  * ELASTICITY.wti_px.spx_pct = -0.0010 (fractional SPX move per +$1/bbl WTI)

Stdlib only (Python 3.9): no numpy/scipy/statsmodels/pandas on this machine,
and statistics.correlation/linear_regression only landed in 3.10, so OLS is
hand-rolled here.

Usage:  python3 audit_fit_elasticities.py [path/to/data.json]
"""
import json
import math
import sys


def load_history(path):
    with open(path) as fh:
        doc = json.load(fh)
    # v2 envelope: {"schema":2, "history": {date: {field: value}}, ...}
    hist = doc["history"] if isinstance(doc, dict) and "history" in doc else doc
    return hist


def aligned_series(hist, field_x, field_y):
    """Return (dates, xs, ys) for dates where BOTH fields are present, sorted."""
    dates, xs, ys = [], [], []
    for d in sorted(hist):
        row = hist[d]
        if field_x in row and field_y in row:
            dates.append(d)
            xs.append(float(row[field_x]))
            ys.append(float(row[field_y]))
    return dates, xs, ys


def ols(xs, ys):
    """Simple OLS y = a + b*x. Returns dict with slope, intercept, r, r2, n,
    and the t-statistic on the slope. Pure stdlib."""
    n = len(xs)
    if n < 3:
        return {"n": n, "error": "need >=3 points"}
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return {"n": n, "error": "no variance in regressor (x is constant)",
                "x_range": (min(xs), max(xs))}
    slope = sxy / sxx
    intercept = my - slope * mx
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else float("nan")
    r2 = r * r
    # standard error of slope + t-stat (df = n-2)
    ss_resid = syy - slope * sxy          # residual sum of squares
    df = n - 2
    se_slope = math.sqrt((ss_resid / df) / sxx) if df > 0 and ss_resid > 0 else float("nan")
    t = slope / se_slope if se_slope and not math.isnan(se_slope) and se_slope != 0 else float("nan")
    return {"n": n, "slope": slope, "intercept": intercept, "r": r, "r2": r2,
            "t": t, "x_range": (min(xs), max(xs)), "x_span": max(xs) - min(xs),
            "se_slope": se_slope}


def first_diff(dates, xs, ys):
    """Consecutive-day first differences (dx, dy) for adjacent calendar-aligned
    dates. Aligns on the already-joined date list."""
    dxs, dys = [], []
    for i in range(1, len(dates)):
        dxs.append(xs[i] - xs[i - 1])
        dys.append(ys[i] - ys[i - 1])
    return dxs, dys


def report(title, hardcoded, unit, fit, note=""):
    print(f"\n=== {title} ===")
    print(f"  hardcoded coefficient : {hardcoded}  ({unit})")
    if "error" in fit:
        print(f"  FIT FAILED            : {fit['error']}")
        if "x_range" in fit:
            print(f"  regressor range       : {fit['x_range']}")
        if note:
            print(f"  note                  : {note}")
        return
    print(f"  n (aligned days)      : {fit['n']}")
    print(f"  regressor range       : {fit['x_range'][0]:.4g} .. {fit['x_range'][1]:.4g}"
          f"  (span {fit['x_span']:.4g})")
    print(f"  fitted slope          : {fit['slope']:.5g}  ({unit})")
    print(f"  Pearson r / R^2       : {fit['r']:.3f} / {fit['r2']:.3f}")
    print(f"  slope std err / t     : {fit['se_slope']:.4g} / {fit['t']:.2f}")
    if note:
        print(f"  note                  : {note}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    hist = load_history(path)

    # ---- 1) ffr -> vix : points of VIX per +1pp fed funds -------------------
    dates, ffr, vix = aligned_series(hist, "ffr", "vix")
    lvl = ols(ffr, vix)
    report("ffr -> vix  (LEVELS)", 1.10, "VIX pts per +1pp FFR", lvl,
           note="levels regression of two persistent series - interpret with care")
    dffr, dvix = first_diff(dates, ffr, vix)
    diff = ols(dffr, dvix)
    report("ffr -> vix  (FIRST DIFFERENCES)", 1.10, "d(VIX) per d(FFR)", diff,
           note="daily changes; FFR barely moves intraday so regressor variance is tiny")

    # ---- 2) wti_px -> spx : fractional SPX move per +$1/bbl WTI --------------
    dates2, wti, spx = aligned_series(hist, "wti_px", "spx")
    # target is a PERCENT move, so fit daily SPX % change on daily WTI $ change
    dwti, dspx = first_diff(dates2, wti, spx)
    # convert dspx (index points) into fractional return using prior-day level
    dspx_frac = []
    for i in range(1, len(dates2)):
        prev = spx[i - 1]
        dspx_frac.append((spx[i] - spx[i - 1]) / prev if prev else 0.0)
    fit2 = ols(dwti, dspx_frac)
    report("wti_px -> spx  (daily: SPX %return on WTI $change)", -0.0010,
           "fractional SPX per +$1 WTI", fit2,
           note="contemporaneous same-day; no lag modelled")

    print("\n--- interpretation guide ---")
    print("  Promote to a sourced tier only if: sign matches the hardcoded sign,")
    print("  |t| is meaningfully > 2, and the regressor actually varied over the")
    print("  window. Otherwise the 1-year sample cannot support the number and the")
    print("  cell should stay UNVERIFIED or be deleted.")


if __name__ == "__main__":
    main()
