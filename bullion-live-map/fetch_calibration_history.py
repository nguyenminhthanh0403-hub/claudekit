#!/usr/bin/env python3
"""Fetch a multi-year FRED+Yahoo+IMF history for offline calibration.

calibrate.py fits every ELASTICITY cell and LINKS row against data.json's history, but
data.json only carries ~365 days (deliberately -- data.json is what bullion_mkultra.html
fetches on every page load, so its size is a live-payload concern, not just a data
concern). The 3 monthly-cadence FRED series (cpi_yoy, m2, nfp_mom) publish ~12 points a
year, yielding only 3-9 daily first-differences in a year -- short of calibrate.py's
MIN_LINK_N=30 floor, so every link touching them is correctly left DIRECTIONAL for lack
of a fittable sample, not because the relationship is false.

This script produces a SEPARATE, wider-window history file -- calibration_history.json,
gitignored, never fetched by the live page -- so calibrate.py can be pointed at it
(`python3 calibrate.py calibration_history.json bullion_mkultra.html
calibration_report_multiyear.txt`) to test those links without touching data.json or the
daily cron.

Reuses backfill_baseline.fetch_all_history(), the same wide-window fetcher the annual
BASELINE_STATS refresh already relies on -- it already works around FRED's 2000-vintage-
per-request cap that a naive multi-year pull through fetch_bullion_data.fetch_fred_series
would hit (see _fetch_fred_history_only's docstring in backfill_baseline.py).

Usage: python3 fetch_calibration_history.py
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backfill_baseline import fetch_all_history
from fetch_bullion_data import load_key, FRED_SERIES, YAHOO_SYMBOLS

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(OUT_DIR, "calibration_history.json")

# 6 years clears calibrate.py's MIN_LINK_N=30 floor for monthly-cadence links with real
# margin (~72 monthly observations vs. the ~39 needed for a 31-point 80%-training
# split), without reaching back into pre-2020 rate regimes (ZIRP, the 2008 GFC) that may
# not represent how these series relate today.
CALIBRATION_WINDOW_YEARS = 6

EXPECTED_FIELDS = (
    [field for _, (field, _, _) in FRED_SERIES.items()]
    + [field for _, (field, _) in YAHOO_SYMBOLS.items()]
    + ["cb_gold_reserves", "usd_reserve_share"]
)


def transpose_to_date_major(field_major):
    """{field: {date: value}} -> {date: {field: value}}, calibrate.py's expected shape."""
    out = {}
    for field, by_date in field_major.items():
        for date_str, value in by_date.items():
            out.setdefault(date_str, {})[field] = value
    return out


def missing_fields(field_major):
    """Which EXPECTED_FIELDS came back with no history at all."""
    return [f for f in EXPECTED_FIELDS if not field_major.get(f)]


def main():
    key = load_key()
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc)
             - timedelta(days=365 * CALIBRATION_WINDOW_YEARS)).strftime("%Y-%m-%d")

    field_major = fetch_all_history(key, start, end)

    missing = missing_fields(field_major)
    if missing:
        print(f"Failed to fetch: {', '.join(missing)}", file=sys.stderr)
        print("Refusing to write a truncated calibration_history.json; leaving any "
              "previous file untouched.", file=sys.stderr)
        sys.exit(1)

    history = transpose_to_date_major(field_major)
    with open(OUT_PATH, "w") as f:
        json.dump({"history": history}, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {OUT_PATH}: {len(history)} dated entries, "
          f"{CALIBRATION_WINDOW_YEARS}yr window ({start}..{end}).")


if __name__ == "__main__":
    main()
