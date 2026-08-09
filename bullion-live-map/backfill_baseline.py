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
import os
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


if __name__ == "__main__":
    key = _read_fred_key()
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_full = (datetime.now(timezone.utc) - timedelta(days=365 * FULL_WINDOW_YEARS)).strftime("%Y-%m-%d")
    history = fetch_all_history(key, start_full, end)
    print(f"Fetched history for {len(history)} fields, window {start_full}..{end}", file=sys.stderr)
