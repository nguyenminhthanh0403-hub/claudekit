"""Calibration pure core: deterministic functions for backtest and audit.
Python 3.9, stdlib only."""

import json
import math


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


def train_split(dates):
    """Deterministic 80/20 split rule shared with the in-page backtest:
    train = the first floor(0.8*N) dates after sorting; the rest is held out."""
    ds = sorted(dates)
    cut = int(0.8 * len(ds))
    return set(ds[:cut])


def target_series(hist, field, kind):
    """Return (dates, values) for a field over dates where it is present, sorted.
    kind is 'level' (use raw values) or 'pct' (raw values; caller takes pct change)."""
    dates, vals = [], []
    for d in sorted(hist):
        if field in hist[d]:
            dates.append(d); vals.append(float(hist[d][field]))
    return dates, vals


def verdict(hand_sign, fit):
    """Adoption rubric. Promote to 'measured' only if the fitted sign matches the
    hand sign, |t| > 2, and the regressor actually varied."""
    if 'error' in fit or fit.get('x_span', 0) == 0:
        return 'directional', 'regressor did not vary'
    fit_sign = 1 if fit['slope'] > 0 else -1
    if fit_sign != hand_sign:
        return 'directional', 'fitted sign disagrees with the hand sign'
    if abs(fit.get('t', 0)) <= 2:
        return 'directional', f"|t|={abs(fit['t']):.1f} not significant"
    return 'measured', f"sign matches, |t|={abs(fit['t']):.1f}, span={fit['x_span']:.3g}"
