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

SCHEMA_VERSION = 2

# Provenance metadata per field. Every field written to data.json must appear
# here or it ships without provenance — which is the exact defect this schema
# exists to remove, so build_envelope raises rather than emitting a bare value.
FIELD_META = {
    "us2y":    {"class": "measured", "cadence": "daily",   "source": "FRED DGS2"},
    "us10y":   {"class": "measured", "cadence": "daily",   "source": "FRED DGS10"},
    "vix":     {"class": "measured", "cadence": "daily",   "source": "FRED VIXCLS"},
    "ffr":     {"class": "measured", "cadence": "daily",   "source": "FRED DFF"},
    "wti_px":  {"class": "measured", "cadence": "daily",   "source": "FRED DCOILWTICO"},
    "cpi_yoy": {"class": "measured", "cadence": "monthly", "source": "FRED CPILFESL"},
    "nfp_mom": {"class": "measured", "cadence": "monthly", "source": "FRED PAYEMS"},
    "gold_px": {"class": "measured", "cadence": "daily",   "source": "Yahoo GC=F"},
    "dxy":     {"class": "measured", "cadence": "daily",   "source": "Yahoo DX-Y.NYB"},
    "spx":     {"class": "measured", "cadence": "daily",   "source": "Yahoo ^GSPC"},
}


def build_envelope(latest_out, history_by_date, generated_at):
    """Assemble the schema v2 data.json envelope.

    `history` passes through untouched — the map's date picker reads it and its
    shape must not drift.
    """
    fields = {}
    for name, rec in latest_out.items():
        meta = FIELD_META.get(name)
        if meta is None:
            raise KeyError(
                f"field {name!r} has no FIELD_META entry; add one rather than "
                f"shipping a value with no provenance")
        fields[name] = {
            "class":     meta["class"],
            "cadence":   meta["cadence"],
            "source":    meta["source"],
            "ref_date":  rec["ref_date"],
            "published": rec["published"],
            "value":     rec["value"],
        }
    return {
        "schema": SCHEMA_VERSION,
        "generated_at": generated_at,
        "fields": fields,
        "history": history_by_date,
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


def parse_fred_observations(data, decimals):
    """Pure parse of a FRED observations payload.

    Returns (latest_value, ref_date, published, history). `published` comes
    from the observation's realtime_start, which is the date the reading
    became available — this is what freshness is judged on.

    A realtime RANGE request (see fetch_fred_series) makes FRED return one
    row PER VINTAGE per observation date, in undocumented server-side order.
    For each observation date we keep the row with the greatest
    realtime_start — the current, most-revised value — regardless of the
    order rows arrive in. A row with no realtime_start sorts as oldest, so
    any row that HAS one always wins over one that doesn't for the same date.
    """
    best_realtime_start_by_ref = {}
    history = {}
    published_by_ref = {}
    for obs in data.get("observations", []):
        val = obs.get("value")
        if val is None or val == ".":
            continue
        ref_date = obs.get("date")
        try:
            parsed_val = round(float(val), decimals)
        except (ValueError, TypeError):
            continue
        if ref_date is None:
            continue

        realtime_start = obs.get("realtime_start") or ""
        current_best = best_realtime_start_by_ref.get(ref_date)
        if current_best is not None and realtime_start <= current_best:
            continue  # an earlier (or equal) vintage than the one we already kept

        best_realtime_start_by_ref[ref_date] = realtime_start
        history[ref_date] = parsed_val
        published_by_ref[ref_date] = obs.get("realtime_start")

    if not history:
        return (None, None, None, {})
    latest_ref = max(history)
    return (history[latest_ref], latest_ref, published_by_ref.get(latest_ref), history)


def fred_url(params):
    return "https://api.stlouisfed.org/fred/series/observations?" + "&".join(
        f"{k}={urllib.request.quote(str(v))}" for k, v in params.items()
    )


def fred_observation_params(series_id, key, units, start, end):
    """Pure construction of the params dict for a values request.

    FRED returns HTTP 400 when a realtime RANGE (realtime_start/realtime_end)
    is combined with any `units` transform other than 'lin' — see
    fetch_fred_publication_date's docstring. So: `units` set means NO
    realtime keys; `units` unset means BOTH realtime keys, no `units` key.
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
    else:
        # Safe only without a units transform — see fetch_fred_publication_date.
        params["realtime_start"] = start
        params["realtime_end"] = "9999-12-31"
    return params


def fetch_fred_publication_date(series_id, key, start, end):
    """Publication date of a series' latest observation, as its own request.

    Verified against the live API 2026-07-21: FRED rejects a realtime RANGE
    combined with any `units` transform other than 'lin' —

      400: "If output_type is '1' and units is not 'lin', then realtime_start
            must equal realtime_end..."

    CPILFESL uses units=pc1 and PAYEMS uses units=chg, so the two monthly
    series this whole feature exists for cannot carry realtime parameters on
    their values request. Publication date is a property of the observation and
    not of the transform, so the untransformed series answers the question and
    the observation dates join exactly.

    Note the trap: omitting realtime parameters entirely does NOT work either.
    FRED then returns realtime_start = today (a current-vintage marker), which
    would silently read as "published today" for every series.

    Returns (ref_date, published), or (None, None) if unavailable.
    """
    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
        "observation_start": start,
        "observation_end": end,
        "realtime_start": start,
        "realtime_end": "9999-12-31",
    }
    try:
        data = http_get_json(fred_url(params))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  FRED {series_id}: publication-date lookup failed ({e})", file=sys.stderr)
        return (None, None)
    obs = data.get("observations") or []
    if not obs:
        return (None, None)
    return (obs[0].get("date"), obs[0].get("realtime_start"))


def fetch_fred_series(series_id, key, units, decimals, start, end):
    """Network wrapper around parse_fred_observations."""
    params = fred_observation_params(series_id, key, units, start, end)

    try:
        data = http_get_json(fred_url(params))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  FRED {series_id}: fetch failed ({e})", file=sys.stderr)
        return (None, None, None, {})

    value, ref, pub, hist = parse_fred_observations(data, decimals)
    if value is None:
        print(f"  FRED {series_id}: no usable observations in range", file=sys.stderr)
        return (None, None, None, {})

    if units:
        # The values request could not carry realtime parameters, so the
        # publication date comes from a second, untransformed lookup.
        pub_ref, pub = fetch_fred_publication_date(series_id, key, start, end)
        if pub_ref and pub_ref != ref:
            print(f"  FRED {series_id}: publication lookup returned {pub_ref}, "
                  f"values latest is {ref}; leaving published unset", file=sys.stderr)
            pub = None

    return (value, ref, pub, hist)


def parse_yahoo_chart(data, decimals):
    """Pure parse of a Yahoo chart payload.

    Returns (latest_value, ref_date, published, history). For a daily close the
    reference date and publication date are the same day — the close IS the
    moment the number exists.
    """
    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        latest = result["meta"].get("regularMarketPrice")
    except (KeyError, IndexError, TypeError):
        return (None, None, None, {})

    history = {}
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        history[date_str] = round(float(close), decimals)

    if not history:
        return (None, None, None, {})
    latest_ref = max(history)
    latest = round(float(latest), decimals) if latest is not None else history[latest_ref]
    return (latest, latest_ref, latest_ref, history)


def fetch_yahoo_symbol(symbol, decimals, range_="1y"):
    """Network wrapper around parse_yahoo_chart."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(symbol)}"
           f"?range={range_}&interval=1d")
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  Yahoo {symbol}: fetch failed ({e})", file=sys.stderr)
        return (None, None, None, {})

    value, ref, pub, hist = parse_yahoo_chart(data, decimals)
    if value is None:
        print(f"  Yahoo {symbol}: unexpected response shape or no usable data", file=sys.stderr)
    return (value, ref, pub, hist)


def main():
    key = load_key()
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=HISTORY_DAYS)).isoformat()
    end = today.isoformat()

    latest_out = {}
    history_by_date = {}  # date_str -> {field: value}

    for series_id, (field, units, decimals) in FRED_SERIES.items():
        value, ref, pub, hist = fetch_fred_series(series_id, key, units, decimals, start, end)
        if value is not None:
            latest_out[field] = {"value": value, "ref_date": ref, "published": pub}
        for date_str, val in hist.items():
            history_by_date.setdefault(date_str, {})[field] = val

    for symbol, (field, decimals) in YAHOO_SYMBOLS.items():
        value, ref, pub, hist = fetch_yahoo_symbol(symbol, decimals)
        if value is not None:
            latest_out[field] = {"value": value, "ref_date": ref, "published": pub}
        for date_str, val in hist.items():
            history_by_date.setdefault(date_str, {})[field] = val

    if not history_by_date:
        print("No fields fetched successfully; leaving existing data.json untouched.", file=sys.stderr)
        sys.exit(1)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = build_envelope(latest_out, history_by_date, generated_at)

    with open(DATA_OUT_PATH, "w") as f:
        json.dump(envelope, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {DATA_OUT_PATH} (schema {SCHEMA_VERSION}) with "
          f"{len(history_by_date)} dated entries and {len(envelope['fields'])} fields.")

    # Log every field's publication age so the tolerances above can be revised
    # against observed behaviour instead of re-guessed.
    today = datetime.now(timezone.utc).date()
    print("\nPublication ages (freshness is judged on these, not ref_date):")
    for name in sorted(envelope["fields"]):
        fld = envelope["fields"][name]
        pub = fld["published"]
        pub_date = datetime.strptime(pub, "%Y-%m-%d").date() if pub else None
        state, age = freshness_verdict(
            fld["cadence"], pub_date, today,
            override_days=FIELD_TOLERANCE_OVERRIDE.get(name))
        marker = "  FLAGGED" if state == "flagged" else ""
        age_str = f"{age}d" if age is not None else "n/a"
        print(f"  {name:10s} ref={fld['ref_date']} pub={pub} age={age_str:>5s} {state}{marker}")

    missing = [f for f in FIELD_META if f not in envelope["fields"]]
    if missing:
        print(f"\nFailed to fetch (map falls back to simulated baseline): {', '.join(missing)}")
    print()
    print(SOURCE_NOTE)


if __name__ == "__main__":
    main()
