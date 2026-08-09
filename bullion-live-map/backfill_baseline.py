#!/usr/bin/env python3
"""Backfill a long-run statistical baseline for the Mk Ultra macro engine.

Pulls 15 years of history per FRED/Yahoo series (reusing fetch_bullion_data's
fetchers), computes per-field mean/std for z-scoring, fits a PCA-derived
composite weighting (see build_pca in the next task), and splices the result
as a BASELINE_STATS JS constant into bullion_mkultra.html.

Rerunnable: rerun periodically (e.g. yearly) to keep the baseline current.
Not part of the daily-data cron — this is a slow, occasional, manual/dev-time
script, same category as calibrate.py.

See docs/superpowers/specs/2026-08-09-bullion-mkultra-macro-engine-design.md
"""
import math
import os
import random
import statistics
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_bullion_data import FRED_SERIES, YAHOO_SYMBOLS, KEY_PATH, fetch_fred_series, fetch_yahoo_symbol

FULL_WINDOW_YEARS = 15
RECENT_WINDOW_YEARS = 2

# Mean-reverting: z-score against the full 15yr window. Trending (secular
# growth/decline, e.g. an equity index or a balance sheet that grows via QE):
# z-score against a shorter recent window instead, since a 15yr mean of a
# trending series is not a meaningful "normal" — see Global Constraints in
# the plan for why.
MEAN_REVERTING_FIELDS = ["hy_oas", "ig_oas", "sofr", "tbill_3m", "us10y", "us2y", "vix",
                          "ffr", "cpi_yoy", "dxy", "wti_px"]
TRENDING_FIELDS = ["spx", "fed_bs", "rrp"]
# Fields whose native cadence has gaps a same-day PCA row matrix can't tolerate.
FORWARD_FILL_FIELDS = ["fed_bs"]

COMPOSITE_FIELDS = ["hy_oas", "ig_oas", "sofr", "tbill_3m", "us10y", "us2y",
                     "curve_slope", "vix", "spx", "fed_bs", "rrp"]


def _read_fred_key():
    with open(KEY_PATH) as f:
        return f.read().strip()


def fetch_all_history(key, start, end):
    """Fetch full history for every tracked FRED + Yahoo field.

    Returns {field: {date_str: value}}. Yahoo uses range_="max" (no
    arbitrary-length range token is guaranteed valid) and results are
    filtered to [start, end] here.
    """
    out = {}
    for series_id, (field, units, decimals) in FRED_SERIES.items():
        _, _, _, hist = fetch_fred_series(series_id, key, units, decimals, start, end)
        out[field] = hist
    for symbol, (field, decimals) in YAHOO_SYMBOLS.items():
        _, _, _, hist = fetch_yahoo_symbol(symbol, decimals, range_="max")
        out[field] = {d: v for d, v in hist.items() if start <= d <= end}
    return out


def forward_fill(history, all_dates):
    """Carry the last known value forward across every date in all_dates.

    all_dates must be sorted ascending. Dates before the first observation
    are left absent (nothing to carry forward yet).
    """
    filled = {}
    last = None
    for d in all_dates:
        if d in history:
            last = history[d]
        if last is not None:
            filled[d] = last
    return filled


def field_stats(values):
    if not values:
        raise ValueError("field_stats: empty values")
    return {"mean": statistics.mean(values), "std": statistics.pstdev(values), "n": len(values)}


def add_curve_slope(history):
    """Returns a new history dict with a derived 'curve_slope' = us10y - us2y field."""
    out = dict(history)
    us10y, us2y = history.get("us10y", {}), history.get("us2y", {})
    out["curve_slope"] = {d: us10y[d] - us2y[d] for d in us10y if d in us2y}
    return out


def build_zscore_rows(history, stats_by_field, fields):
    """Dates (sorted) and z-scored rows where every field in `fields` is present.

    Each row is clipped to +/-3 per field, matching the client-side engine's
    clipping so the historical composite distribution used for percentile
    lookup is built the same way the live score will be computed.
    """
    date_sets = [set(history[f].keys()) for f in fields]
    common = sorted(set.intersection(*date_sets)) if date_sets else []
    rows = []
    for d in common:
        row = []
        for f in fields:
            s = stats_by_field[f]
            z = (history[f][d] - s["mean"]) / s["std"] if s["std"] else 0.0
            row.append(max(-3.0, min(3.0, z)))
        rows.append(row)
    return common, rows


def pca_first_component(rows, n_iter=500, seed=1):
    """First principal component via power iteration on X^T X / n (rows are
    already z-scored, i.e. approximately mean-zero per column, so this is
    power iteration on the covariance matrix without building it explicitly).
    """
    n_fields = len(rows[0])
    n_rows = len(rows)
    rnd = random.Random(seed)
    v = [rnd.random() - 0.5 for _ in range(n_fields)]

    def normalize(vec):
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    v = normalize(v)
    for _ in range(n_iter):
        xv = [sum(row[j] * v[j] for j in range(n_fields)) for row in rows]
        w = [sum(xv[i] * rows[i][j] for i in range(n_rows)) / n_rows for j in range(n_fields)]
        v = normalize(w)
    return v


def orient_loadings(loadings, fields, anchor_field="vix"):
    idx = fields.index(anchor_field)
    if loadings[idx] < 0:
        return [-x for x in loadings]
    return list(loadings)


def percentile_table(values, n_points=101):
    ordered = sorted(values)
    last = len(ordered) - 1
    return [ordered[round(p / (n_points - 1) * last)] for p in range(n_points)]


if __name__ == "__main__":
    key = _read_fred_key()
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_full = (datetime.now(timezone.utc) - timedelta(days=365 * FULL_WINDOW_YEARS)).strftime("%Y-%m-%d")
    history = fetch_all_history(key, start_full, end)
    print(f"Fetched history for {len(history)} fields, window {start_full}..{end}", file=sys.stderr)
