# Mk Ultra — IMF Central-Bank Gold Reserves Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live `cb_gold_reserves` field (central-bank gold reserves, in tonnes, summed across the largest public holders) sourced from the IMF's free SDMX 3.0 API, and use it to replace the `gold` node's stale static World Gold Council flow figure in `bullion_mkultra.html`.

**Architecture:** `fetch_bullion_data.py` gains a new fetcher that queries IMF's IRFCL dataflow for 11 countries, sums their reported troy-ounce holdings into a single tonnes figure, and folds it into the existing all-or-nothing `latest_out`/`history_by_date` pipeline exactly like any FRED/Yahoo field. `backfill_baseline.py` reuses that same fetcher for its 15-year window and classifies the field as trending (not mean-reverting). `bullion_mkultra.html`'s `gold` node and its three live-field maps pick up the new field.

**Tech Stack:** Python 3 stdlib only (`json`, `urllib.request`, `calendar`, `datetime`) — no new pip dependency, matching this project's existing zero-third-party-dependency convention. No new GitHub secret (IMF's API is keyless).

## Global Constraints

- No new pip dependency — stdlib only, matching `fetch_bullion_data.py`'s existing imports.
- No change to `bullion_mk11.html` through `bullion_mk18.html` (frozen files) — verified via `sha256sum` before and after.
- No new GitHub Actions secret and no `.github/workflows/*.yml` change — IMF's SDMX API needs no key.
- `fetch_imf_country_series()` and `fetch_imf_gold_reserves_basket()` must **return an empty/None-tuple result on any failure, never raise** — this matches `fetch_fred_series()`/`fetch_yahoo_symbol()`'s actual established convention in this file (both catch their own exceptions and return `(None, None, None, {})`), which the approved design doc's prose description ("raises... same as `fetch_fred_series()` does today") did not literally match against the real code. The real code's convention wins.
- Every new field must appear in `FIELD_META` or `build_envelope()` raises by design — do not skip this.
- A partial fetch must never write a truncated `data.json` or `BASELINE_STATS` — both existing completeness gates (`missing` list in `fetch_bullion_data.main()`, `missing_baseline_fields()` in `backfill_baseline.py`) already enforce this generically once the new field is registered in `FIELD_META`/`EXPECTED_BASELINE_FIELDS`; no new gate logic is needed, only correct registration.

## Research findings (resolves the design doc's open item — verified against the live API 2026-08-11)

These facts were confirmed by querying `https://api.imf.org/external/sdmx/3.0/...` directly (no mock, no assumption) and are the basis for every constant below:

1. **No world aggregate exists.** `COUNTRY=G001` ("World") returns zero series for any indicator in the `IRFCL` dataflow (`.../IRFCL/12.0.0/G001` → dataset has no `series` key at all). The design doc's anticipated fallback — summing named top holders — is required, not optional.
2. **Dataflow / indicator / sector:** `IMF.STA:IRFCL(12.0.0)`, indicator `IRFCLDT1_IRFCL56V_FTO` ("Official reserve assets, gold volume", raw troy ounces — the codelist name says "millions" but the raw `OBS_VALUE` is already unscaled, confirmed by USA's value of `261499000` oz ≈ 8,133.5 t, matching the USA's well-known reserve level), sector `S1XS1311` ("Monetary Authorities and Central Government excl. Social Security" — the narrower `S1X` sector omits the USA, whose gold is held by the Treasury, not the Fed).
3. **Basket of 11 countries**, each individually verified to have real `S1XS1311` monthly data: `USA, DEU, ITA, FRA, CHN, RUS, CHE, IND, JPN, TUR, NLD`. Latest values (2026-08-11 spot check, troy oz → tonnes): USA 8,133.5t, DEU 3,349.3t, ITA 2,451.8t, FRA 2,437.0t, CHN 2,346.4t, RUS 2,283.0t, CHE 1,039.9t, IND 880.5t, JPN 846.0t, TUR 729.8t, NLD 612.5t — basket total ≈ 25,110t. (Global official reserves are ~36,000t across ~100 countries — this basket is the largest holders, not a true world total, and the HTML label must say so.)
4. **Real cadence is monthly, not quarterly.** The design doc's "quarterly" was an unconfirmed starting guess. The `FREQUENCY` dimension offers `A/D/M/Q`; `M` (monthly) has the freshest, densest data (e.g. USA and NLD already at 2026-M07 as of this research). **No new `"quarterly"` tier is needed in `CADENCE_TOLERANCE_DAYS`** — reuse the existing `"monthly"` tier (45 days).
5. **Observed lag requires a `FIELD_TOLERANCE_OVERRIDE`.** Countries report at different lags; the *slowest* of the 11 basket members was still on 2026-M06 (end-of-month ref `2026-06-30`) while 3 others were already at M07, as of a fetch on 2026-08-11 — a 43-day age under normal, healthy operation. That is within the existing 45-day monthly default, but by a margin too thin to survive a single day's routine reporting slip (the same problem `wti_px`'s override exists to solve). Set `FIELD_TOLERANCE_OVERRIDE["cb_gold_reserves"] = 60`.
6. **The field is trending, not mean-reverting.** A 2011–2025 pull of the basket's annual total shows a monotonic rise every single year (20,470t → 25,196t, +23%) — central banks have been structural net buyers for over a decade. A 15-year mean/std z-score against this would be meaningless (the same reason `fed_bs`/`spx` are `TRENDING_FIELDS` rather than mean-reverting). Classify `cb_gold_reserves` as `TRENDING`, using the existing `RECENT_WINDOW_YEARS=2` window, and add it to `FORWARD_FILL_FIELDS` (its monthly cadence is even sparser than `fed_bs`'s weekly one, which already needed forward-fill for a dense-enough recent-window sample).
7. **No separate publication/vintage date is exposed** by this IMF endpoint (the SDMX response's `meta` block is empty; only a reference period, no realtime/vintage marker). `ref_date` and `published` are therefore set equal to each other — the same situation `parse_yahoo_chart()` already documents and handles for daily closes — using the **last day of the latest month common to all 11 countries** (summing past that point would mix a stale country's old figure into an otherwise-current total).
8. **No custom `Accept` header is required** — `http_get_json()`'s existing `User-Agent`-only request works against this endpoint unchanged (verified via a bare `curl` with no `Accept` header, HTTP 200, well-formed JSON).

## File Structure

- **`bullion-live-map/fetch_bullion_data.py`** (modify) — new IMF basket fetcher (constants, pure parser, network wrapper, composing function), `FIELD_META`/`FIELD_TOLERANCE_OVERRIDE`/`SOURCE_NOTE` entries, `main()` wiring. This is the only place that talks to the IMF API.
- **`bullion-live-map/tests/test_fetch_bullion_data.py`** (modify) — unit tests for the new pure parser and composing function; updates to the two existing `TestMainRefusesIncompleteWrites` tests so they mock the new fetch call instead of hitting the network.
- **`bullion-live-map/backfill_baseline.py`** (modify) — import and call the new composing function inside `fetch_all_history()`; classify the field in `TRENDING_FIELDS`/`FORWARD_FILL_FIELDS`.
- **`bullion-live-map/tests/test_backfill_baseline.py`** (modify) — extend the full-field fixture; add a regression test proving the trending/forward-fill classification.
- **`bullion-live-map/bullion_mkultra.html`** (modify) — `gold` node's `expert` array text, `LIVE_FIELD_LABEL`, `LIVE_FMT`, `NODE_LIVE_FIELD`.

---

### Task 1: IMF gold-reserves basket fetcher in `fetch_bullion_data.py`

**Files:**
- Modify: `bullion-live-map/fetch_bullion_data.py`
- Test: `bullion-live-map/tests/test_fetch_bullion_data.py`

**Interfaces:**
- Produces: `fetch_imf_gold_reserves_basket(start, end) -> (value, ref_date, published, history)` — same 4-tuple shape as `fetch_fred_series`/`fetch_yahoo_symbol`, consumed directly by `main()` in this task and by `backfill_baseline.fetch_all_history()` in Task 2.
- Produces: `parse_imf_sdmx(data) -> {date_iso: troy_oz}` — pure parser, the unit-test target.
- Produces: `IMF_GOLD_COUNTRIES` (list of 11 ISO-3 country codes) — read by Task 2, not modified there.

- [ ] **Step 1: Add the IMF basket constants**

In `fetch_bullion_data.py`, add `import calendar` to the top import block (alongside the existing `import json` etc.), then add this block after `YAHOO_SYMBOLS` (before the `CADENCE_TOLERANCE_DAYS` comment):

```python
# IMF SDMX 3.0 IRFCL dataflow has no world-aggregate entity for gold
# reserves (COUNTRY=G001 returns zero series for this indicator, confirmed
# against the live API 2026-08-11) -- this basket of the largest verified
# public holders is the closest available approximation to a global total.
# IRFCLDT1_IRFCL56V_FTO is "Official reserve assets, gold volume" in troy
# ounces; S1XS1311 ("Monetary Authorities and Central Government excl.
# Social Security") is the sector code with data for every country below --
# the narrower S1X ("Monetary authorities" alone) misses the USA, whose
# gold is held by the Treasury rather than the Fed.
IMF_GOLD_BASE_URL = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/IRFCL/12.0.0"
IMF_GOLD_INDICATOR = "IRFCLDT1_IRFCL56V_FTO"
IMF_GOLD_SECTOR = "S1XS1311"
IMF_GOLD_COUNTRIES = ["USA", "DEU", "ITA", "FRA", "CHN", "RUS", "CHE", "IND", "JPN", "TUR", "NLD"]
TROY_OZ_PER_TONNE = 32150.7466
```

- [ ] **Step 2: Add `FIELD_TOLERANCE_OVERRIDE` entry**

Change:
```python
FIELD_TOLERANCE_OVERRIDE = {
    "wti_px": 10,
}
```
to:
```python
# cb_gold_reserves sums 11 countries with independent national reporting
# lags. Observed 2026-08-11: the slowest of the 11 sat at 43 days (still
# on end-of-June data, fetched mid-August) while every country was
# reporting normally -- the 45-day monthly default would false-alarm on a
# single day's routine slip. 60 gives roughly the same cushion ratio
# wti_px's override gives over ITS observed lag.
FIELD_TOLERANCE_OVERRIDE = {
    "wti_px": 10,
    "cb_gold_reserves": 60,
}
```

- [ ] **Step 3: Add `FIELD_META` entry**

In the `FIELD_META` dict, after the `rrp` entry (end of the "Mk17 breadth" block), add:

```python
    "cb_gold_reserves": {"class": "measured", "cadence": "monthly",
                          "source": "IMF IRFCL (top-11 public holders, summed)"},
```

- [ ] **Step 4: Write the failing parser tests**

In `tests/test_fetch_bullion_data.py`, add near the bottom (before the `if __name__` guard):

```python
from fetch_bullion_data import parse_imf_sdmx, imf_period_to_month_end


class TestImfPeriodToMonthEnd(unittest.TestCase):
    def test_converts_month_period_to_last_day_of_month(self):
        self.assertEqual(imf_period_to_month_end("2026-M07"), "2026-07-31")

    def test_handles_february_in_a_leap_year(self):
        self.assertEqual(imf_period_to_month_end("2024-M02"), "2024-02-29")

    def test_unrecognised_shape_returns_none(self):
        self.assertIsNone(imf_period_to_month_end("2026"))
        self.assertIsNone(imf_period_to_month_end("2026-Q3"))
        self.assertIsNone(imf_period_to_month_end(""))


class TestParseImfSdmx(unittest.TestCase):
    PAYLOAD = {
        "data": {
            "dataSets": [{
                "series": {
                    "0:0:0:0": {
                        "observations": {
                            "0": ["261499000", None, 0, None],
                            "1": ["261499000.5", None, 0, None],
                        }
                    }
                }
            }],
            "structures": [{
                "dimensions": {
                    "observation": [{
                        "id": "TIME_PERIOD",
                        "values": [{"value": "2026-M06"}, {"value": "2026-M07"}],
                    }]
                }
            }],
        }
    }

    def test_returns_troy_oz_keyed_by_month_end_date(self):
        history = parse_imf_sdmx(self.PAYLOAD)
        self.assertEqual(history, {
            "2026-06-30": 261499000.0,
            "2026-07-31": 261499000.5,
        })

    def test_missing_series_key_returns_empty(self):
        payload = {"data": {"dataSets": [{}], "structures": [{"dimensions": {"observation": [{"values": []}]}}]}}
        self.assertEqual(parse_imf_sdmx(payload), {})

    def test_null_observation_value_is_skipped(self):
        payload = {
            "data": {
                "dataSets": [{"series": {"0:0:0:0": {"observations": {
                    "0": [None, None, 0, None],
                    "1": ["100.0", None, 0, None],
                }}}}],
                "structures": [{"dimensions": {"observation": [{
                    "values": [{"value": "2026-M06"}, {"value": "2026-M07"}],
                }]}}],
            }
        }
        self.assertEqual(parse_imf_sdmx(payload), {"2026-07-31": 100.0})

    def test_completely_malformed_payload_returns_empty(self):
        self.assertEqual(parse_imf_sdmx({}), {})
        self.assertEqual(parse_imf_sdmx({"data": {}}), {})
```

- [ ] **Step 5: Run the new tests to verify they fail**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data.TestParseImfSdmx tests.test_fetch_bullion_data.TestImfPeriodToMonthEnd -v`
Expected: `ImportError: cannot import name 'parse_imf_sdmx'` (neither function exists yet).

- [ ] **Step 6: Implement `imf_period_to_month_end` and `parse_imf_sdmx`**

Add after `parse_yahoo_chart` in `fetch_bullion_data.py`:

```python
def imf_period_to_month_end(period):
    """Convert an SDMX 'YYYY-Mmm' monthly period to its ISO month-end date.

    Returns None for anything not in this exact shape -- FREQUENCY is
    pinned to M in the query this feeds, but a future API/DSD change
    should fail the parse rather than silently mis-date a value.
    """
    if len(period) != 8 or period[4] != "-" or period[5] != "M":
        return None
    try:
        year = int(period[:4])
        month = int(period[6:8])
    except ValueError:
        return None
    if not 1 <= month <= 12:
        return None
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{last_day:02d}"


def parse_imf_sdmx(data):
    """Pure parse of one country's IMF SDMX 3.0 gold-reserves response.

    Returns {date_iso: troy_oz} keyed by the LAST day of each reported
    month (a stock figure is naturally "as of period end"), or {} for any
    missing/unrecognised shape or null value -- mirrors
    parse_fred_observations/parse_yahoo_chart's pure-parse-returns-empty-
    on-failure convention. No exception is raised here.
    """
    try:
        structures = data["data"]["structures"][0]
        period_values = structures["dimensions"]["observation"][0]["values"]
        series = data["data"]["dataSets"][0].get("series")
    except (KeyError, IndexError, TypeError):
        return {}
    if not series:
        return {}

    history = {}
    for s in series.values():
        for idx, obs in s.get("observations", {}).items():
            if not obs or obs[0] is None:
                continue
            try:
                oz = float(obs[0])
                period = period_values[int(idx)]["value"]
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            date_iso = imf_period_to_month_end(period)
            if date_iso is not None:
                history[date_iso] = oz
    return history
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data.TestParseImfSdmx tests.test_fetch_bullion_data.TestImfPeriodToMonthEnd -v`
Expected: all PASS.

- [ ] **Step 8: Write the failing basket-composition tests**

Add to `tests/test_fetch_bullion_data.py`:

```python
import fetch_bullion_data as fbd_module
from fetch_bullion_data import fetch_imf_gold_reserves_basket, IMF_GOLD_COUNTRIES


class TestFetchImfGoldReservesBasket(unittest.TestCase):
    def setUp(self):
        self._orig = fbd_module.fetch_imf_country_series

    def tearDown(self):
        fbd_module.fetch_imf_country_series = self._orig

    def test_sums_all_countries_for_their_common_latest_date(self):
        def fake(country, start, end):
            # every country reports through 2026-07-31; two also have a
            # stale August partial that must NOT be included since not
            # every country has it yet
            hist = {"2026-06-30": 100.0, "2026-07-31": 200.0}
            if country in ("USA", "DEU"):
                hist["2026-08-15"] = 999.0
            return hist
        fbd_module.fetch_imf_country_series = fake

        value, ref, pub, history = fetch_imf_gold_reserves_basket("2026-01-01", "2026-08-20")

        n = len(IMF_GOLD_COUNTRIES)
        self.assertEqual(ref, "2026-07-31")
        self.assertEqual(pub, ref, "IMF exposes no separate publication date")
        self.assertAlmostEqual(value, round(200.0 * n / fbd_module.TROY_OZ_PER_TONNE, 1))
        self.assertNotIn("2026-08-15", history)
        self.assertAlmostEqual(history["2026-06-30"], round(100.0 * n / fbd_module.TROY_OZ_PER_TONNE, 1))

    def test_any_single_country_failure_fails_the_whole_basket(self):
        def fake(country, start, end):
            if country == "RUS":
                return {}
            return {"2026-06-30": 100.0}
        fbd_module.fetch_imf_country_series = fake

        value, ref, pub, history = fetch_imf_gold_reserves_basket("2026-01-01", "2026-08-20")
        self.assertIsNone(value)
        self.assertIsNone(ref)
        self.assertIsNone(pub)
        self.assertEqual(history, {})

    def test_no_common_date_across_countries_fails_closed(self):
        def fake(country, start, end):
            # every country has data, but no two dates overlap
            return {f"2026-0{IMF_GOLD_COUNTRIES.index(country) % 9 + 1}-28": 100.0}
        fbd_module.fetch_imf_country_series = fake

        value, ref, pub, history = fetch_imf_gold_reserves_basket("2026-01-01", "2026-08-20")
        self.assertIsNone(value)
        self.assertEqual(history, {})
```

- [ ] **Step 9: Run to verify failure**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data.TestFetchImfGoldReservesBasket -v`
Expected: `ImportError: cannot import name 'fetch_imf_gold_reserves_basket'`.

- [ ] **Step 10: Implement `fetch_imf_country_series` and `fetch_imf_gold_reserves_basket`**

Add after `fetch_yahoo_symbol` in `fetch_bullion_data.py`:

```python
def fetch_imf_country_series(country, start, end):
    """Network wrapper: one country's monthly gold-reserves history, in troy oz.

    Returns {date_iso: troy_oz}, or {} on any HTTP error or unparseable
    response -- same non-raising convention as fetch_fred_series/
    fetch_yahoo_symbol, so one bad country fails the basket closed (see
    fetch_imf_gold_reserves_basket) instead of crashing the whole run.
    """
    start_period = start[:7]  # "YYYY-MM-DD" -> "YYYY-MM"
    url = (f"{IMF_GOLD_BASE_URL}/{country}.{IMF_GOLD_INDICATOR}.{IMF_GOLD_SECTOR}.M"
           f"?startPeriod={start_period}")
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  IMF {country}: fetch failed ({e})", file=sys.stderr)
        return {}
    hist = parse_imf_sdmx(data)
    if not hist:
        print(f"  IMF {country}: unexpected response shape or no usable data", file=sys.stderr)
    return hist


def fetch_imf_gold_reserves_basket(start, end):
    """Sum central-bank gold reserves (tonnes) across IMF_GOLD_COUNTRIES.

    IMF's IRFCL dataflow has no world-aggregate entity for gold reserves
    (confirmed against the live API 2026-08-11) -- this basket of the
    largest public holders is the closest available approximation to a
    global total. Any single country's fetch failing fails the whole
    field closed (returns the all-None tuple) rather than silently
    shipping an under-counted sum with no indication a holder is missing.

    Returns (latest_tonnes, ref_date, published, history) in the same
    shape fetch_fred_series/fetch_yahoo_symbol produce. ref_date and
    published are identical -- IMF's SDMX response carries no separate
    publication/vintage date, only a reference period, the same situation
    parse_yahoo_chart documents for a daily close -- and are set to the
    LATEST month every basket country has reported through: summing past
    that point would mix a stale country's old figure into an otherwise-
    current total.
    """
    per_country = {}
    for country in IMF_GOLD_COUNTRIES:
        hist = fetch_imf_country_series(country, start, end)
        if not hist:
            print(f"  IMF gold-reserves basket: {country} missing, "
                  f"failing the whole field", file=sys.stderr)
            return (None, None, None, {})
        per_country[country] = hist

    common_dates = set.intersection(*(set(h) for h in per_country.values()))
    if not common_dates:
        print("  IMF gold-reserves basket: no common reporting date across "
              "all countries", file=sys.stderr)
        return (None, None, None, {})

    history = {}
    for date_iso in common_dates:
        total_oz = sum(per_country[c][date_iso] for c in IMF_GOLD_COUNTRIES)
        history[date_iso] = round(total_oz / TROY_OZ_PER_TONNE, 1)

    latest_ref = max(history)
    return (history[latest_ref], latest_ref, latest_ref, history)
```

- [ ] **Step 11: Run to verify the basket tests pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data.TestFetchImfGoldReservesBasket -v`
Expected: all PASS.

- [ ] **Step 12: Wire the basket into `main()`**

In `main()`, after the Yahoo loop (`for symbol, (field, decimals) in YAHOO_SYMBOLS.items(): ...`) and before `if not history_by_date:`, add:

```python
    imf_value, imf_ref, imf_pub, imf_hist = fetch_imf_gold_reserves_basket(start, end)
    if imf_value is not None:
        latest_out["cb_gold_reserves"] = {"value": imf_value, "ref_date": imf_ref, "published": imf_pub}
    for date_str, val in imf_hist.items():
        history_by_date.setdefault(date_str, {})["cb_gold_reserves"] = val
```

- [ ] **Step 13: Extend `SOURCE_NOTE`**

Append a sentence to `SOURCE_NOTE` (before the closing `)`):

```python
    "cb_gold_reserves: IMF IRFCL (International Reserves and Foreign "
    "Currency Liquidity), summed across the 11 largest public holders "
    "(USA, Germany, Italy, France, China, Russia, Switzerland, India, "
    "Japan, Turkiye, Netherlands) -- IMF publishes no single world-"
    "aggregate entity for this indicator, so this is the largest holders, "
    "not a true global total."
```

- [ ] **Step 14: Update the two existing `TestMainRefusesIncompleteWrites` tests so they don't hit the live network**

`main()` now calls the real `fetch_imf_gold_reserves_basket` unless mocked, which both existing tests in `TestMainRefusesIncompleteWrites` would otherwise do for real over the network during a unit-test run. In `setUp`, add:

```python
        self._orig_fetch_imf_basket = self.mod.fetch_imf_gold_reserves_basket
```

In `tearDown`, add:

```python
        self.mod.fetch_imf_gold_reserves_basket = self._orig_fetch_imf_basket
```

In `test_total_outage_exits_without_touching_existing_file`, add a mock so the IMF call also "succeeds" with an empty history (matching the test's intent: every field succeeds with a real latest value but empty history, so ONLY the `history_by_date` guard trips):

```python
        self.mod.fetch_imf_gold_reserves_basket = (
            lambda start, end: (1.0, "2026-07-17", "2026-07-17", {}))
```

In `test_partial_fetch_exits_without_writing_truncated_file`, add:

```python
        self.mod.fetch_imf_gold_reserves_basket = (
            lambda start, end: (25000.0, "2026-07-17", "2026-07-17", {"2026-07-17": 25000.0}))
```

(Both assignments go in the test method body, before the `with self.assertRaises(SystemExit):` block, alongside the existing `self.mod.fetch_fred_series = ...` / `self.mod.fetch_yahoo_symbol = ...` lines.)

- [ ] **Step 15: Run the full fetch_bullion_data test file**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data -v`
Expected: all PASS, including the two updated `TestMainRefusesIncompleteWrites` tests (no network call made).

- [ ] **Step 16: Live-fetch dry run against the real IMF endpoint**

Run:
```bash
cd bullion-live-map && python3 -c "
from datetime import datetime, timedelta, timezone
from fetch_bullion_data import fetch_imf_gold_reserves_basket
today = datetime.now(timezone.utc).date()
start = (today - timedelta(days=400)).isoformat()
end = today.isoformat()
print(fetch_imf_gold_reserves_basket(start, end))
"
```
Expected: a tuple with a non-None float value in the 20,000–30,000 range (tonnes), a `YYYY-MM-DD` ref date, and a multi-entry history dict. If any country has stopped reporting since this plan's research (2026-08-11), this will fail closed (`None, None, None, {}`) with per-country stderr lines identifying which one — that is correct behavior, not a bug, and should be investigated before proceeding rather than worked around.

- [ ] **Step 17: Commit**

```bash
git add bullion-live-map/fetch_bullion_data.py bullion-live-map/tests/test_fetch_bullion_data.py
git commit -m "Mk Ultra: fetch IMF central-bank gold reserves (top-11 basket)"
```

---

### Task 2: Wire the basket into `backfill_baseline.py`

**Files:**
- Modify: `bullion-live-map/backfill_baseline.py`
- Test: `bullion-live-map/tests/test_backfill_baseline.py`

**Interfaces:**
- Consumes: `fetch_imf_gold_reserves_basket(start, end)` from Task 1, same 4-tuple shape.
- Produces: `cb_gold_reserves` present in `TRENDING_FIELDS`, `FORWARD_FILL_FIELDS`, and (transitively, via those lists) `EXPECTED_BASELINE_FIELDS`.

- [ ] **Step 1: Write the failing classification test**

In `tests/test_backfill_baseline.py`, add to the top-level imports:

```python
from backfill_baseline import RECENT_WINDOW_YEARS
```

Add a new test method inside `TestBuildBaseline`:

```python
    def test_cb_gold_reserves_is_trending_and_forward_filled(self):
        from datetime import datetime, timedelta, timezone
        base = datetime.now(timezone.utc)
        dense_dates = [(base - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(27, -1, -1)]
        history = self._synthetic_history()
        # cb_gold_reserves only reports on every 10th dense date, mirroring
        # its real monthly sparsity against the other fields' daily grid.
        sparse_dates = dense_dates[::10]
        history["cb_gold_reserves"] = {d: 25000.0 for d in sparse_dates}

        baseline = build_baseline(history)

        stats = baseline["fields"]["cb_gold_reserves"]
        self.assertEqual(stats["window_years"], RECENT_WINDOW_YEARS)
        self.assertGreater(stats["n"], len(sparse_dates),
                            "forward-fill should carry cb_gold_reserves onto the dense grid")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline.TestBuildBaseline.test_cb_gold_reserves_is_trending_and_forward_filled -v`
Expected: FAIL — `KeyError: 'cb_gold_reserves'` (not yet in `TRENDING_FIELDS`/`FORWARD_FILL_FIELDS`, so `build_baseline` never computes stats for it).

- [ ] **Step 3: Add the classification**

Change:
```python
TRENDING_FIELDS = ["spx", "fed_bs", "rrp"]
```
to:
```python
# cb_gold_reserves: a 2011-2025 pull of the basket total rose every single
# year (20,470t -> 25,196t) -- central banks have been structural net
# buyers for over a decade, the same reason spx/fed_bs are trending
# rather than mean-reverting (verified 2026-08-11, see the design plan's
# Research findings).
TRENDING_FIELDS = ["spx", "fed_bs", "rrp", "cb_gold_reserves"]
```

Change:
```python
FORWARD_FILL_FIELDS = ["fed_bs"]
```
to:
```python
# cb_gold_reserves' native monthly cadence is even sparser than fed_bs's
# weekly one, so it needs the same forward-fill treatment for a
# reasonably dense RECENT_WINDOW_YEARS sample.
FORWARD_FILL_FIELDS = ["fed_bs", "cb_gold_reserves"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline.TestBuildBaseline.test_cb_gold_reserves_is_trending_and_forward_filled -v`
Expected: PASS.

- [ ] **Step 5: Write the failing `fetch_all_history` wiring test**

Add to `tests/test_backfill_baseline.py`, near `TestFieldStats` or as its own class:

```python
class TestFetchAllHistoryIncludesImfBasket(unittest.TestCase):
    def test_fetch_all_history_calls_the_imf_basket_fetcher(self):
        import backfill_baseline as bb_module
        orig = bb_module.fetch_imf_gold_reserves_basket
        called = {}

        def fake(start, end):
            called["args"] = (start, end)
            return (25000.0, "2026-06-30", "2026-06-30", {"2026-06-30": 25000.0})

        bb_module.fetch_imf_gold_reserves_basket = fake
        try:
            out = bb_module.fetch_all_history("dummy-key", "2011-01-01", "2026-08-12")
        finally:
            bb_module.fetch_imf_gold_reserves_basket = orig

        self.assertEqual(called["args"], ("2011-01-01", "2026-08-12"))
        self.assertEqual(out["cb_gold_reserves"], {"2026-06-30": 25000.0})
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline.TestFetchAllHistoryIncludesImfBasket -v`
Expected: FAIL — `KeyError: 'cb_gold_reserves'` (`fetch_all_history` doesn't call it yet) or the fake is never invoked.

- [ ] **Step 7: Wire the import and the call**

Change the import block at the top of `backfill_baseline.py`:
```python
from fetch_bullion_data import (
    FRED_SERIES, YAHOO_SYMBOLS, KEY_PATH, fetch_yahoo_symbol,
    http_get_json, fred_url, parse_fred_observations,
)
```
to:
```python
from fetch_bullion_data import (
    FRED_SERIES, YAHOO_SYMBOLS, KEY_PATH, fetch_yahoo_symbol,
    http_get_json, fred_url, parse_fred_observations,
    fetch_imf_gold_reserves_basket,
)
```

In `fetch_all_history()`, after the Yahoo loop and before `return out`, add:

```python
    _, _, _, imf_hist = fetch_imf_gold_reserves_basket(start, end)
    out["cb_gold_reserves"] = imf_hist
```

- [ ] **Step 8: Run to verify it passes**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline.TestFetchAllHistoryIncludesImfBasket -v`
Expected: PASS.

- [ ] **Step 9: Extend the completeness-gate fixture**

In `TestMissingBaselineFields._full_synthetic_history()`, add `"cb_gold_reserves"` to the field-name list passed to `enumerate(...)`:

```python
        for i, f in enumerate(["hy_oas", "ig_oas", "sofr", "tbill_3m", "us10y", "us2y",
                                "vix", "spx", "fed_bs", "rrp", "ffr", "cpi_yoy", "dxy", "wti_px",
                                "nfp_mom", "cb_gold_reserves"]):
```

- [ ] **Step 10: Run the full backfill_baseline test file**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline -v`
Expected: all PASS, including `test_complete_baseline_has_no_missing_fields`.

- [ ] **Step 11: Live-fetch dry run**

Run: `cd bullion-live-map && python3 backfill_baseline.py`
Expected: succeeds (needs a real FRED key at `~/.config/bullion/fred_api_key` for the other fields), prints `BASELINE_STATS refreshed: N fields, ...` where N now includes `cb_gold_reserves`, and `git diff bullion_mkultra.html` shows only the `BASELINE_STATS` block changing (the splice target), with a `cb_gold_reserves` entry whose `"window_years": 2`.

- [ ] **Step 12: Commit**

```bash
git add bullion-live-map/backfill_baseline.py bullion-live-map/tests/test_backfill_baseline.py bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: classify cb_gold_reserves as trending, wire into baseline backfill"
```

---

### Task 3: `bullion_mkultra.html` — node text and live-field wiring

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html`

**Interfaces:**
- Consumes: `cb_gold_reserves` field in `data.json`, written by Task 1's `main()` run.

- [ ] **Step 1: Replace the `gold` node's stale expert-text lines**

At `bullion_mkultra.html` (around line 1230), change:

```javascript
      'Central-bank gold demand hit 1,037 tonnes in 2023. Real rates (TIPS) dominate.',
      'Source: World Gold Council (correlation studies and demand trends); the dollar link on this map is fitted separately.'] },
```

to:

```javascript
      'Central banks have been structural net buyers of gold in most years for over a decade, a shift in reserve composition tracked live here across the largest public holders. Real rates (TIPS) still dominate day-to-day price moves.',
      'Source: IMF International Reserves and Foreign Currency Liquidity (IRFCL); the dollar link on this map is fitted separately.'] },
```

(No specific tonnage number is hardcoded in the static text, matching every other live-bound node on this map — e.g. `gold_px` itself never states a live price in its `expert` array; the actual current number is shown by the detail panel's live-reading row, wired in the next steps.)

- [ ] **Step 2: Add the field to `LIVE_FIELD_LABEL`**

Change:
```javascript
const LIVE_FIELD_LABEL = { us2y:'US2Y', ..., xlp:'Staples (XLP)' };
```
by inserting before the closing `};`:
```javascript
, cb_gold_reserves:'CB Gold (Top 11)'
```
(i.e. the label reads `CB Gold (Top 11)` — flagging up front that this is a basket of the largest holders, not a world total, matching the honesty standard the rest of this map holds itself to.)

- [ ] **Step 3: Add the field to `LIVE_FMT`**

In the `LIVE_FMT` object, add a new entry (formats as whole tonnes with a `t` suffix, e.g. `25,110t`):
```javascript
  cb_gold_reserves:v=>Math.round(+v).toLocaleString()+'t',
```

- [ ] **Step 4: Add the field to `NODE_LIVE_FIELD`**

Change:
```javascript
  yield: ['us10y', 'us2y'], equit: ['spx'], gold: ['gold_px'], usd: ['dxy'], oil: ['wti_px'],
```
to:
```javascript
  yield: ['us10y', 'us2y'], equit: ['spx'], gold: ['gold_px', 'cb_gold_reserves'], usd: ['dxy'], oil: ['wti_px'],
```

- [ ] **Step 5: sha256sum check on frozen files**

Run:
```bash
cd bullion-live-map && sha256sum bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html bullion_mk18.html > /tmp/frozen_before.txt
git diff --stat -- bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html bullion_mk18.html
```
Expected: empty diff (no output from the second command) — these files must never be touched by this work.

- [ ] **Step 6: Browser verification**

Use the `headless-chrome-verification` skill to serve `bullion-live-map/` over `http://localhost` (not `file://`, since the page fetches `data.json`), open the `gold` node's detail panel, and confirm:
- The `CB Gold (Top 11)` live reading renders next to the existing `Gold` (`gold_px`) reading, formatted like `25,110t`.
- The expert-text panel shows the new sentence, with no reference to "1,037 tonnes" or a bare "World Gold Council" source line remaining.
- No console errors.

- [ ] **Step 7: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: replace gold node's stale WGC flow figure with live IMF reserves reading"
```

---

### Task 4: Whole-branch verification

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests -v`
Expected: all green. The pre-existing baseline was 85 tests; this plan adds roughly 12-14 new tests (Task 1: `TestImfPeriodToMonthEnd` (3) + `TestParseImfSdmx` (4) + `TestFetchImfGoldReservesBasket` (3); Task 2: 1 + `TestFetchAllHistoryIncludesImfBasket` (1)), so expect somewhere around 97-99 tests total, 0 failures.

- [ ] **Step 2: Live-fetch dry run of both scripts for real**

Run:
```bash
cd bullion-live-map
python3 fetch_bullion_data.py
python3 backfill_baseline.py
```
Expected: both exit 0. `fetch_bullion_data.py`'s printed "Publication ages" table includes a `cb_gold_reserves` row; confirm its `age` is comfortably under 60 (the override) — if it is at or past 60, that is new information about the real-world lag and the override in Task 1 Step 2 should be revisited before considering this plan done, not silently ignored.

- [ ] **Step 3: Frozen-file check**

Run: `cd bullion-live-map && sha256sum bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html bullion_mk18.html | diff - /tmp/frozen_before.txt`
Expected: no output (identical).

- [ ] **Step 4: git status check**

Run: `git status`
Expected: clean except `data.json` (Step 2's live dry run legitimately updates it) and any untracked handoff docs. No unexpected files.

- [ ] **Step 5: Ask the user about `bd991d6`**

The prior session's commit `bd991d6` (the approved design doc) is still unpushed, per the handoff this plan was written from. Before pushing anything, confirm with the user whether to push it standalone or bundle it with this plan's new commits — do not assume either way.
