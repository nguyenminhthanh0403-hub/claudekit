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


# Driver field, target cell key, target field, kind, and the current hand value/sign
# (hand values copied from ELASTICITY for the report; sign is what verdict checks).
CELLS = [
    ('ffr','us2y','us2y','level', 0.92),   ('ffr','us10y','us10y','level', 0.42),
    ('ffr','spx_pct','spx','pct', -0.045), ('ffr','gold_pct','gold_px','pct', -0.030),
    ('ffr','dxy_add','dxy','level', 2.20),
    ('vix','spx_pct','spx','pct', -0.0085),('vix','us10y','us10y','level', -0.0090),
    ('vix','gold_pct','gold_px','pct', 0.0045), ('vix','dxy_add','dxy','level', 0.080),
    ('dxy','gold_pct','gold_px','pct', -0.0075), ('dxy','wti_pct','wti_px','pct', -0.0055),
    ('dxy','spx_pct','spx','pct', -0.0020),
    ('wti_px','spx_pct','spx','pct', -0.0009), ('wti_px','us10y','us10y','level', 0.0035),
]


def fit_cell(hist, train, drv_field, tgt_field, kind):
    """First-difference fit of the target's daily change on the driver's daily change,
    over dates in the training set where BOTH are present. pct targets use fractional
    change; level/add targets use raw change."""
    dates = [d for d in sorted(hist)
             if d in train and drv_field in hist[d] and tgt_field in hist[d]]
    xs = [float(hist[d][drv_field]) for d in dates]
    ys = [float(hist[d][tgt_field]) for d in dates]
    dxs, dys = first_diff(dates, xs, ys)
    if kind == 'pct':
        dys = [ (ys[i]-ys[i-1]) / ys[i-1] if ys[i-1] else 0.0 for i in range(1, len(ys)) ]
    return ols(dxs, dys)


def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    doc = json.load(open(path))
    hist = doc['history'] if isinstance(doc, dict) and 'history' in doc else doc
    train = train_split(list(hist.keys()))
    lines = [f"Bullion Mk12 calibration — train split {len(train)} days "
             f"(first 80% of {len(hist)}); first-difference OLS.\n"]
    for drv, tgtkey, tgtfield, kind, hand in CELLS:
        fit = fit_cell(hist, train, drv, tgtfield, kind)
        hand_sign = 1 if hand > 0 else -1
        if 'error' in fit:
            lines.append(f"{drv:7s}-> {tgtkey:9s}  FIT FAILED: {fit['error']}")
            continue
        tier, why = verdict(hand_sign, fit)
        lines.append(
            f"{drv:7s}-> {tgtkey:9s}  n={fit['n']:3d}  span={fit['x_span']:.3g}  "
            f"slope={fit['slope']:+.5g}  hand={hand:+.4g}  r={fit['r']:+.2f}  "
            f"t={fit['t']:+.1f}  =>  {tier.upper()} ({why})")
    report = "\n".join(lines) + "\n"
    print(report)
    open('calibration_report.txt', 'w').write(report)


if __name__ == '__main__':
    main()
