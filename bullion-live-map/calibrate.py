"""Calibration pure core: deterministic functions for backtest and audit.
Python 3.9, stdlib only."""

import json
import math
import re


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
    t = fit.get('t', 0)
    if t is None or (isinstance(t, float) and math.isnan(t)):
        return 'directional', "t-stat undefined (NaN), not significant"
    if abs(t) <= 2:
        return 'directional', f"|t|={abs(t):.1f} not significant"
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
    ('us10y','spx_pct','spx','pct', -0.010), ('us2y','spx_pct','spx','pct', -0.008),
    ('dxy','us10y','us10y','level', 0.02), ('vix','wti_pct','wti_px','pct', -0.004),
    # Mk17 candidates — (driver, target-cell-key, target-field, kind, hand)
    ('us10y','mortgage_lvl','mortgage_30y','level', 0.90),  # mortgages track the 10Y
    ('ffr','sofr_lvl','sofr','level', 1.00),                # SOFR ≈ policy rate
    ('ffr','tbill_lvl','tbill_3m','level', 0.98),           # 3M bill tracks policy
    ('vix','hy_oas_lvl','hy_oas','level', 0.020),           # stress widens HY spread
    ('spx','xlk_pct','xlk','pct', 1.10),                    # tech beta > 1
    ('spx','xlf_pct','xlf','pct', 1.00),                    # financials ≈ market
    ('spx','xle_pct','xle','pct', 0.90),                    # energy < market beta
    ('spx','xlp_pct','xlp','pct', 0.55),                    # staples defensive, low beta
    ('wti_px','xle_pct','xle','pct', 0.010),                # energy sector tracks oil
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


# ─── LINK PASS ──────────────────────────────────────────────────────────────
# Every causal claim on the map is encoded twice: as a LINKS row (a sign, drawn
# as an arrow) and — for the subset the scenario engine models — as an
# ELASTICITY cell (a coefficient, fitted by CELLS above). Only the cells were
# ever calibrated, so 57 of the 86 links carried no confidence tier and the
# audit log filed them all as guesswork. This pass fits every link whose two
# endpoints both bind to a live data.json field, so those tiers can be earned.
#
# Threshold is |t| > 2, the same rule `verdict` applies to cells, plus a
# minimum sample: MIN_LINK_N. Monthly series (cpi_yoy, m2, nfp_mom) yield only
# 3-9 usable daily first differences over a year, and a t-stat on 8 points is
# not evidence of anything. Weekly series (WALCL, MORTGAGE30US, NFCI) give ~40,
# which clears the floor.
MIN_LINK_N = 30

# node id -> data.json field. The first block is Mk17's NODE_LIVE_FIELD (primary
# field only, where a node carries two); the second is driver/alias nodes that
# bind to a field without appearing in that map.
NODE_FIELD = {
    'vix': 'vix', 'credit': 'hy_oas', 'repo': 'sofr', 'mortgage': 'mortgage_30y',
    'm2': 'm2', 'fed': 'fed_bs', 'tbills': 'tbill_3m', 'tech': 'xlk',
    'fins': 'xlf', 'energy': 'xle', 'defn': 'xlp', 'yield': 'us10y',
    'equit': 'spx', 'gold': 'gold_px', 'usd': 'dxy', 'oil': 'wti_px',
    'ffr': 'ffr', 'fomc': 'ffr', 'cpi': 'cpi_yoy', 'nfp': 'nfp_mom',
    'dxy_fx': 'dxy', 'tsy': 'us10y',
}

# Prices and index levels move in percentages; rates, spreads and diffusion
# indices move in points. dxy stays 'level' to match the existing dxy_add cell.
PCT_FIELDS = {'spx', 'gold_px', 'wti_px', 'xlk', 'xlf', 'xle', 'xlp', 'm2', 'fed_bs'}


def field_kind(field):
    """'pct' for price/level series, 'level' for rates and spreads."""
    return 'pct' if field in PCT_FIELDS else 'level'


def _array_rows(html, name):
    """Row strings of a top-level `const <name> = [ {...}, {...} ]` array.

    A brace-depth scan rather than one big regex: link rows carry prose with
    commas and escaped apostrophes, which a naive pattern splits in the wrong
    place. Returns [] when the array is absent (older map versions).
    """
    marker = 'const %s = [' % name
    if marker not in html:
        return []
    start = html.index(marker) + len(marker)
    depth, i = 1, start
    while depth:
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
        i += 1
    body = html[start:i - 1]

    rows, depth, cur = [], 0, ''
    for ch in body:
        if ch == '{':
            depth += 1
        if depth:
            cur += ch
        if ch == '}':
            depth -= 1
            if not depth:
                rows.append(cur)
                cur = ''
    return rows


def _row_fields(r):
    """{'s','t','sign','conf'} for one row, or None if it is not a link row.

    `conf` is normalised to a bare lowercase tier so the quoted literals
    ("conf:'measured'") and the constants ("conf:CONF.MEASURED") that both
    appear in the map read the same way here.
    """
    s = re.search(r"s:'([^']+)'", r)
    t = re.search(r"t:'([^']+)'", r)
    if not (s and t):
        return None
    sign = re.search(r"sign:\s*(-?\d+)", r)
    conf = re.search(r"conf:\s*'?([A-Za-z_.]+)'?", r)
    return {
        's': s.group(1), 't': t.group(1),
        'sign': int(sign.group(1)) if sign else None,
        'conf': conf.group(1).split('.')[-1].lower() if conf else None,
    }


def parse_links(html):
    """The RUNTIME link graph of a map file, not the LINKS literal.

    The page keeps causal claims in two arrays and merges them at load: each
    PLUMBING_LINKS row either SUPERSEDES the LINKS row with the same (s, t)
    pair or is appended (see the `PLUMBING_LINKS.forEach` block in the map).
    Reading only `LINKS` therefore fits rows that never reach the screen — in
    bullion_mkultra.html 9 of the 16 plumbing rows supersede, so the literal's
    86 rows are really 93 at runtime, with different signs and tiers on those 9.
    """
    out, index = [], {}
    for r in _array_rows(html, 'LINKS'):
        f = _row_fields(r)
        if f is None:
            continue
        index[(f['s'], f['t'])] = len(out)
        out.append(f)
    for r in _array_rows(html, 'PLUMBING_LINKS'):
        f = _row_fields(r)
        if f is None:
            continue
        k = (f['s'], f['t'])
        if k in index:
            out[index[k]] = f          # supersede in place
        else:
            index[k] = len(out)
            out.append(f)              # append as a new pair
    return out


def link_candidates(links, node_field=None):
    """The subset of links that can be fitted: both endpoints bind to a field.

    Pairs whose two nodes resolve to the SAME field are dropped — fomc->ffr,
    tsy->yield and usd->dxy_fx would each regress a series on itself and
    "fit" perfectly while proving nothing.
    """
    nf = NODE_FIELD if node_field is None else node_field
    out = []
    for l in links:
        sf, tf = nf.get(l['s']), nf.get(l['t'])
        if not sf or not tf or sf == tf:
            continue
        out.append(dict(l, s_field=sf, t_field=tf, kind=field_kind(tf)))
    return out


def link_verdict(hand_sign, fit):
    """(tier, action, why) for one fitted link.

    Implements the approved conflict policy: data wins where the data is
    strong, the hand sign is kept and flagged where it is weak. `action` is
    one of:
      ''         nothing to do
      'flip'     adopt the fitted sign — the arrow on the map points the wrong way
      'conflict' signs disagree but the fit is too weak to act on; record it
      'review'   hand says sign:0 ("no stable sign") yet the data shows one.
                 A human decides; this pass does not rewrite conditional links.

    An insignificant fit is NOT evidence the relationship is false — most of
    these claims are structural and simply have no daily-frequency signal — so
    it returns 'directional', never 'unverified'. The tier floor for an
    unsourced claim is applied in the map's own validateProvenance().
    """
    if 'error' in fit or fit.get('x_span', 0) == 0:
        return 'directional', '', 'regressor did not vary'
    n = fit.get('n', 0)
    if n < MIN_LINK_N:
        return 'directional', '', (
            f'only n={n} usable daily changes (< {MIN_LINK_N}) — the series is '
            'too coarse for a daily fit')
    t = fit.get('t')
    undefined = t is None or (isinstance(t, float) and math.isnan(t))
    strong = (not undefined) and abs(t) > 2
    fit_sign = 1 if fit['slope'] > 0 else -1

    if hand_sign == 0:
        if strong:
            return 'directional', 'review', (
                'hand says conditional (sign:0) but the data shows a stable '
                f"{'positive' if fit_sign > 0 else 'negative'} daily sign, |t|={abs(t):.1f}")
        return 'directional', '', 'conditional by hand; no significant daily signal'

    if not strong:
        why = 't-stat undefined (NaN)' if undefined else f'|t|={abs(t):.1f} not significant'
        if fit_sign != hand_sign:
            return 'directional', 'conflict', f'fitted sign disagrees but {why}'
        return 'directional', '', f'tested, {why}'

    if fit_sign != hand_sign:
        return 'measured', 'flip', (
            f'data contradicts the hand sign at |t|={abs(t):.1f}: '
            f"fitted slope={fit['slope']:+.4g}")
    return 'measured', '', f'sign matches, |t|={abs(t):.1f}'


def link_report(hist, train, links):
    """Fit every candidate link and return (lines, rows) for the report."""
    cands = link_candidates(links)
    lines = [f'\n=== LINKS === {len(links)} links; {len(cands)} with both endpoints '
             f'in data.json (same-field pairs excluded); |t| > 2 = measured\n']
    rows = []
    for l in cands:
        fit = fit_cell(hist, train, l['s_field'], l['t_field'], l['kind'])
        if 'error' in fit:
            lines.append(f"{l['s']:9s}-> {l['t']:11s} FIT FAILED: {fit['error']}")
            continue
        tier, action, why = link_verdict(l['sign'], fit)
        rows.append(dict(l, fit=fit, tier=tier, action=action, why=why))
        flag = f'  [{action.upper()}]' if action else ''
        lines.append(
            f"{l['s']:9s}-> {l['t']:11s} {l['s_field']:>12s}->{l['t_field']:<13s} "
            f"n={fit['n']:3d} slope={fit['slope']:+.5g} t={fit['t']:+.1f} "
            f"hand={l['sign']:+d} was={l['conf'] or '-':11s} => {tier.upper()}"
            f" ({why}){flag}")

    acts = {}
    for r in rows:
        acts[r['action'] or 'clean'] = acts.get(r['action'] or 'clean', 0) + 1
    tiers = {}
    for r in rows:
        tiers[r['tier']] = tiers.get(r['tier'], 0) + 1
    lines.append(f"\nfitted: {dict(sorted(tiers.items()))}   actions: {dict(sorted(acts.items()))}")
    return lines, rows


def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    html_path = sys.argv[2] if len(sys.argv) > 2 else 'bullion_mkultra.html'
    doc = json.load(open(path))
    hist = doc['history'] if isinstance(doc, dict) and 'history' in doc else doc
    train = train_split(list(hist.keys()))
    lines = [f"Bullion calibration — train split {len(train)} days "
             f"(first 80% of {len(hist)}); first-difference OLS.\n"
             "=== ELASTICITY CELLS ===\n"]
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

    try:
        links = parse_links(open(html_path).read())
    except (IOError, OSError, ValueError) as e:
        lines.append(f"\n=== LINKS === skipped: could not read {html_path} ({e})")
    else:
        lines.extend(link_report(hist, train, links)[0])

    report = "\n".join(lines) + "\n"
    print(report)
    open('calibration_report.txt', 'w').write(report)


if __name__ == '__main__':
    main()
