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
import json
import math
import os
import random
import statistics
import sys
import urllib.error
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_bullion_data import (
    FRED_SERIES, YAHOO_SYMBOLS, KEY_PATH, fetch_yahoo_symbol,
    http_get_json, fred_url, parse_fred_observations,
)

FULL_WINDOW_YEARS = 15
RECENT_WINDOW_YEARS = 2

# Mean-reverting: z-score against the full 15yr window. Trending (secular
# growth/decline, e.g. an equity index or a balance sheet that grows via QE):
# z-score against a shorter recent window instead, since a 15yr mean of a
# trending series is not a meaningful "normal" — see Global Constraints in
# the plan for why.
MEAN_REVERTING_FIELDS = ["hy_oas", "ig_oas", "sofr", "tbill_3m", "us10y", "us2y", "vix",
                          "ffr", "cpi_yoy", "dxy", "wti_px", "nfp_mom"]
TRENDING_FIELDS = ["spx", "fed_bs", "rrp"]
# Fields whose native cadence has gaps a same-day PCA row matrix can't tolerate.
FORWARD_FILL_FIELDS = ["fed_bs"]

COMPOSITE_FIELDS = ["hy_oas", "ig_oas", "vix", "spx", "fed_bs", "rrp", "curve_slope"]

# +1: higher raw value means MORE stress. -1: higher raw value means LESS
# stress. Fixed conceptual judgment calls, not statistically discovered —
# see docs/superpowers/specs/2026-08-11-bullion-mkultra-composite-score-fix-design.md
# for the reasoning behind each sign and why the 4 raw rate-level fields
# (sofr, tbill_3m, us10y, us2y) that used to be in COMPOSITE_FIELDS were
# dropped rather than signed (their stress direction depends on Fed policy
# stance, not a stable convention -- the same ambiguity PCA got wrong).
EXPECTED_STRESS_SIGN = {
    "hy_oas": 1, "ig_oas": 1, "vix": 1,
    "spx": -1, "fed_bs": -1, "rrp": -1, "curve_slope": -1,
}

COMPOSITE_CATEGORY = {
    "hy_oas": "Credit", "ig_oas": "Credit",
    "vix": "Volatility",
    "spx": "Equity valuation",
    "fed_bs": "Funding", "rrp": "Funding",
    "curve_slope": "Safe assets",
}


def _read_fred_key():
    with open(KEY_PATH) as f:
        return f.read().strip()


def _fetch_fred_history_only(series_id, key, units, decimals, start, end):
    """Full observation history for a series, current vintage only.

    fetch_bullion_data.fetch_fred_series requests a realtime RANGE
    (realtime_start=start, realtime_end=9999-12-31) for series with no
    `units` transform, to recover each observation's publication date for
    freshness checks. Over a 15yr backfill window that range spans
    thousands of revision vintages for a daily series like DGS2 (2Y
    yield), and FRED rejects any realtime-range request once the vintage
    count exceeds 2000: "Bad Request. There are N vintage dates in the
    specified real-time period ... This exceeds the maximum number of
    vintage dates allowed for this file type (2000)." (verified against
    the live API 2026-08-09).

    The baseline only needs historical VALUES, not publication dates, so
    this issues a plain observation_start/observation_end request with no
    realtime keys at all -- FRED then returns exactly one (current) row
    per observation date, which sidesteps the cap entirely and gives
    today's best-known value for every historical date. That is also the
    right input for a stats/PCA baseline: it should reflect currently-known
    history, not each value's as-first-published vintage.
    """
    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "sort_order": "asc",
        "observation_start": start,
        "observation_end": end,
    }
    if units:
        params["units"] = units
    try:
        data = http_get_json(fred_url(params))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  FRED {series_id}: fetch failed ({e})", file=sys.stderr)
        return {}
    _, _, _, hist = parse_fred_observations(data, decimals)
    return hist


def fetch_all_history(key, start, end):
    """Fetch full history for every tracked FRED + Yahoo field.

    Returns {field: {date_str: value}}. Yahoo's range_ is bounded to
    FULL_WINDOW_YEARS rather than "max": Yahoo's chart API silently
    downgrades interval=1d to a coarse 3-month bucket once a symbol's full
    history (e.g. ^GSPC back to 1927) is requested with range=max, which
    would leave spx with ~170 quarterly points instead of ~3800 daily ones
    (verified against the live API 2026-08-09). A bounded range token like
    "15y" keeps 1d granularity; results are then filtered to [start, end]
    here as before.
    """
    out = {}
    for series_id, (field, units, decimals) in FRED_SERIES.items():
        out[field] = _fetch_fred_history_only(series_id, key, units, decimals, start, end)
    for symbol, (field, decimals) in YAHOO_SYMBOLS.items():
        _, _, _, hist = fetch_yahoo_symbol(symbol, decimals, range_=f"{FULL_WINDOW_YEARS}y")
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


def build_baseline(history):
    history = add_curve_slope(history)
    # The forward-fill target grid must come from the OTHER (dense/daily)
    # fields, not from FORWARD_FILL_FIELDS' own dates: a field's own date
    # set trivially already contains itself, so building the grid from
    # FORWARD_FILL_FIELDS alone makes forward_fill() a no-op and leaves
    # fed_bs on its native weekly cadence. That silently shrinks the
    # z-scored row intersection in build_zscore_rows down to only the
    # weekly dates every other field happens to also have a value on
    # (observed: ~154 rows instead of ~750+ over the fields' overlap
    # window) -- verified 2026-08-09 against live-fetched history.
    all_dates_sorted = sorted({d for f, h in history.items() if f not in FORWARD_FILL_FIELDS for d in h})
    for f in FORWARD_FILL_FIELDS:
        if f in history:
            history[f] = forward_fill(history[f], all_dates_sorted)

    fields_out = {}
    for f in MEAN_REVERTING_FIELDS + ["curve_slope"]:
        if f not in history or not history[f]:
            continue
        stats = field_stats(list(history[f].values()))
        stats["window_years"] = FULL_WINDOW_YEARS
        fields_out[f] = stats
    for f in TRENDING_FIELDS:
        if f not in history or not history[f]:
            continue
        cutoff = (datetime.now(timezone.utc) - timedelta(days=365 * RECENT_WINDOW_YEARS)).strftime("%Y-%m-%d")
        recent_values = [v for d, v in history[f].items() if d >= cutoff]
        stats = field_stats(recent_values)
        stats["window_years"] = RECENT_WINDOW_YEARS
        fields_out[f] = stats

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "fields": fields_out,
        "stress_sign": dict(EXPECTED_STRESS_SIGN),
        "category": dict(COMPOSITE_CATEGORY),
    }


def render_js_block(baseline):
    return "const BASELINE_STATS = " + json.dumps(baseline, indent=2) + ";"


def splice_into_html(html_text, js_block):
    # Search on the bare marker TEXT, not a full decorative comment line --
    # matching on exact dash-run length would be fragile (the line's dash
    # padding has no functional meaning and could reflow without this
    # function needing to change).
    start_token = "BASELINE-STATS-START"
    end_token = "BASELINE-STATS-END"
    start_idx = html_text.find(start_token)
    end_idx = html_text.find(end_token)
    if start_idx == -1 or end_idx == -1:
        raise ValueError("BASELINE-STATS markers not found in HTML")
    # Splice after the START marker's own line, and before the END marker's line.
    start = html_text.index("\n", start_idx) + 1
    end = html_text.rfind("\n", 0, end_idx)
    before = html_text[:start]
    after = html_text[end:]
    return before + js_block + after


if __name__ == "__main__":
    key = _read_fred_key()
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=365 * FULL_WINDOW_YEARS)).strftime("%Y-%m-%d")
    history = fetch_all_history(key, start_date, end_date)
    baseline = build_baseline(history)
    js_block = render_js_block(baseline)
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bullion_mkultra.html")
    with open(html_path) as f:
        html_text = f.read()
    with open(html_path, "w") as f:
        f.write(splice_into_html(html_text, js_block))
    print(f"BASELINE_STATS refreshed: {len(baseline['fields'])} fields, "
          f"{len(baseline['stress_sign'])} composite fields", file=sys.stderr)
