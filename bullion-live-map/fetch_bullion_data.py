#!/usr/bin/env python3
"""Fetch live market data for Bullion Mk11 and write a date-keyed data.json.

FRED (official, requires a free key) covers us2y, us10y, cpi_yoy, vix, ffr,
wti_px, nfp_mom. Yahoo Finance's chart API (unofficial, undocumented, no key
needed) covers gold_px, dxy, spx. A field that fails to fetch is simply
omitted; bullion_mk11_constellation.html falls back to its own hardcoded
baseline for anything missing.

Get a free FRED key at https://fred.stlouisfed.org/docs/api/api_key.html
then save it with:
  mkdir -p ~/.config/bullion && echo YOUR_KEY_HERE > ~/.config/bullion/fred_api_key
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

KEY_PATH = os.path.expanduser("~/.config/bullion/fred_api_key")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_OUT_PATH = os.path.join(OUT_DIR, "data.json")
HISTORY_DAYS = 365

# FRED series -> (output field, optional FRED `units` transform, decimals to round to)
FRED_SERIES = {
    "DGS2":       ("us2y",    None,  2),
    "DGS10":      ("us10y",   None,  2),
    "CPILFESL":   ("cpi_yoy", "pc1", 1),
    "VIXCLS":     ("vix",     None,  1),
    "DFF":        ("ffr",     None,  2),
    "DCOILWTICO": ("wti_px",  None,  2),
    "PAYEMS":     ("nfp_mom", "chg", 0),
}

# Yahoo Finance chart API. Unofficial/undocumented — no key, but could change
# or rate-limit without notice, unlike FRED's supported public API.
YAHOO_SYMBOLS = {
    "GC=F":      ("gold_px", 2),
    "DX-Y.NYB":  ("dxy",     2),
    "^GSPC":     ("spx",     2),
}

# Cadence tolerances, in days, applied to a field's PUBLICATION date — never
# its reference date. June CPI references 2026-06-01 but publishes 2026-07-14;
# judged on reference date it looks broken, judged on publication it is on
# time. Calibrated 2026-07-20 against observed publication lags: daily FRED
# series ran 3-4 days, wti_px 5, CPI 6, PAYEMS 18.
CADENCE_TOLERANCE_DAYS = {
    "daily":   7,    # observed 3-4d; absorbs a three-day weekend plus a holiday
    "monthly": 45,   # observed 6d and 18d; silent for 45d means genuinely broken
    "fomc":    None, # simulated, never judged
}

# wti_px publishes on a structurally longer lag than the other dailies — it sat
# at 5 days while perfectly healthy, so the 7-day default would have produced a
# false alarm immediately.
FIELD_TOLERANCE_OVERRIDE = {
    "wti_px": 10,
}


def freshness_verdict(cadence, published, today, override_days=None):
    """Decide whether a field's latest value is fresh, judged on publication.

    Returns (state, age_days) where state is 'fresh', 'flagged' or 'unknown'.
    'unknown' means the question does not apply (simulated data) or cannot be
    answered (no publication date, unrecognised cadence) — callers must render
    nothing rather than guess.
    """
    if published is None or cadence == "fomc":
        return ("unknown", None)
    tolerance = override_days if override_days is not None else CADENCE_TOLERANCE_DAYS.get(cadence)
    if tolerance is None:
        return ("unknown", None)
    age_days = (today - published).days
    return ("flagged" if age_days > tolerance else "fresh", age_days)

SOURCE_NOTE = (
    "us2y/us10y/vix/ffr/wti_px: FRED daily series (DGS2, DGS10, VIXCLS, DFF, "
    "DCOILWTICO), official supported API. cpi_yoy: FRED CPILFESL, percent "
    "change from year ago. nfp_mom: FRED PAYEMS, month-over-month change "
    "(thousands). gold_px/dxy/spx: Yahoo Finance chart API (GC=F, DX-Y.NYB, "
    "^GSPC) — unofficial and undocumented, unlike FRED; could change or "
    "rate-limit without notice. FOMC hike/cut odds have no free source and "
    "remain simulated."
)


def load_key():
    try:
        with open(KEY_PATH, "r") as f:
            key = f.read().strip()
    except FileNotFoundError:
        print(f"No FRED API key found at {KEY_PATH}.", file=sys.stderr)
        print("Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html", file=sys.stderr)
        print(f"then run: mkdir -p {os.path.dirname(KEY_PATH)} && echo YOUR_KEY > {KEY_PATH}", file=sys.stderr)
        sys.exit(1)
    if not key:
        print(f"{KEY_PATH} is empty.", file=sys.stderr)
        sys.exit(1)
    return key


def http_get_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_fred_series(series_id, key, units, decimals, start, end):
    """Returns (latest_value, {date_str: value}) for one FRED series."""
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
    url = "https://api.stlouisfed.org/fred/series/observations?" + "&".join(
        f"{k}={urllib.request.quote(str(v))}" for k, v in params.items()
    )
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  FRED {series_id}: fetch failed ({e})", file=sys.stderr)
        return None, {}

    history = {}
    for obs in data.get("observations", []):
        val = obs.get("value")
        if val is None or val == ".":
            continue
        try:
            history[obs["date"]] = round(float(val), decimals)
        except ValueError:
            continue

    if not history:
        print(f"  FRED {series_id}: no usable observations in range", file=sys.stderr)
        return None, {}
    latest_date = max(history)
    return history[latest_date], history


def fetch_yahoo_symbol(symbol, decimals, range_="1y"):
    """Returns (latest_value, {date_str: value}) for one Yahoo chart symbol."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(symbol)}"
           f"?range={range_}&interval=1d")
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  Yahoo {symbol}: fetch failed ({e})", file=sys.stderr)
        return None, {}

    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        latest = result["meta"].get("regularMarketPrice")
    except (KeyError, IndexError, TypeError):
        print(f"  Yahoo {symbol}: unexpected response shape", file=sys.stderr)
        return None, {}

    history = {}
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        history[date_str] = round(float(close), decimals)

    if latest is not None:
        latest = round(float(latest), decimals)
    elif history:
        latest = history[max(history)]
    else:
        print(f"  Yahoo {symbol}: no usable data", file=sys.stderr)
        return None, {}

    return latest, history


def main():
    key = load_key()
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=HISTORY_DAYS)).isoformat()
    end = today.isoformat()

    latest_out = {}
    history_by_date = {}  # date_str -> {field: value}

    for series_id, (field, units, decimals) in FRED_SERIES.items():
        latest, hist = fetch_fred_series(series_id, key, units, decimals, start, end)
        if latest is not None:
            latest_out[field] = latest
        for date_str, val in hist.items():
            history_by_date.setdefault(date_str, {})[field] = val

    for symbol, (field, decimals) in YAHOO_SYMBOLS.items():
        latest, hist = fetch_yahoo_symbol(symbol, decimals)
        if latest is not None:
            latest_out[field] = latest
        for date_str, val in hist.items():
            history_by_date.setdefault(date_str, {})[field] = val

    if not history_by_date:
        print("No fields fetched successfully; leaving existing data.json untouched.", file=sys.stderr)
        sys.exit(1)

    with open(DATA_OUT_PATH, "w") as f:
        json.dump(history_by_date, f, indent=2, sort_keys=True)
        f.write("\n")

    all_fields = [f for _, (f, _, _) in FRED_SERIES.items()] + [f for _, (f, _) in YAHOO_SYMBOLS.items()]
    latest_date = max(history_by_date)
    latest_fields = history_by_date[latest_date]
    missing = [f for f in all_fields if f not in latest_fields]
    print(f"Wrote {DATA_OUT_PATH} with {len(history_by_date)} dated entries.")
    print(f"Latest date {latest_date} has {len(latest_fields)} of {len(all_fields)} fields.")
    if missing:
        print(f"Missing from {latest_date} (map will fall back to simulated baseline for these): {', '.join(missing)}")
    print()
    print(SOURCE_NOTE)


if __name__ == "__main__":
    main()
