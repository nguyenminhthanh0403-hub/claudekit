# Mk Ultra — IMF COFER (USD Reserve-Currency Share) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live `usd_reserve_share` field (percent of allocated global official FX reserves held in USD) sourced from IMF's free COFER API, and use it to replace the reserve-share half of the `usd` node's stale citation in `bullion_mkultra.html`, keeping the trade-invoicing half as its own honestly-dated static sentence.

**Architecture:** `fetch_bullion_data.py` gains a single-series fetcher (`fetch_usd_reserve_share`) that reuses the existing `parse_imf_sdmx` pure parser unchanged — confirmed against the live API that COFER's response shape is identical to IRFCL's — after generalizing the period-to-date converter to also understand COFER's `"YYYY-Qn"` quarterly periods (IRFCL only ever produces `"YYYY-Mmm"`). Unlike gold reserves, IMF publishes a genuine `COUNTRY=G001` ("World") series for COFER, so this is a single fetch, not a basket-and-sum.

**Tech Stack:** Python 3 stdlib only, no new dependency. No new GitHub secret — COFER is keyless like IRFCL.

## Global Constraints

- No new pip dependency — stdlib only.
- No change to `bullion_mk11.html` through `bullion_mk17.html` (truly frozen — verified via `sha256sum`). `bullion_mk18.html` is NOT frozen but per the user's standing choice (made during the gold-reserves work) gets only the minimal `CADENCE_TOLERANCE_DAYS` sync needed to keep `tests/test_freshness_parity.py` green — not the full node-text/live-field-map treatment.
- No new GitHub Actions secret, no `.github/workflows/*.yml` change.
- `fetch_usd_reserve_share()` must return the all-None/empty tuple on any failure, never raise — same established convention as every other fetcher in this file.
- A partial fetch must never write a truncated `data.json` or `BASELINE_STATS` — the existing completeness gates handle this automatically once the field is registered in `FIELD_META`/`EXPECTED_BASELINE_FIELDS`.

## Research findings (resolves the spec's Alternative #1 — verified against the live API 2026-08-12)

1. **COFER's SDMX response shape is identical to IRFCL's** — same `data.dataSets[0].series[key].observations[idx] = [value_str, ...]` and `data.structures[0].dimensions.observation[0].values[idx].value` shape. **`parse_imf_sdmx` is fully reusable, no forked parser needed** — only the period-string format differs (`"2026-Q1"`, 7 chars, vs IRFCL's `"2026-M07"`, 8 chars), which the shared period converter must handle.
2. **IMF publishes a genuine `COUNTRY=G001` ("World") COFER series** — confirmed live (e.g. `2026-Q1 = 57.13`). No per-country basket is needed, unlike gold reserves.
3. **Exact key:** `IMF.STA:COFER(7.0.1)` / `G001.AFXRA.CI_USD.SHRO_PT.Q`. `SHRO_PT` ("Shares") already returns a plain percentage number (e.g. `58.38`, not `0.5838`) — no unit conversion needed.
4. **The `c[TIME_PERIOD]=ge:...` filter works the same way** as it did for IRFCL (confirmed live) — `startPeriod` is not used.
5. **No separate publication/vintage date** is exposed (the response's `meta` block is empty, same as IRFCL) — `ref_date` and `published` are both set to the quarter-end date.
6. **Real cadence is quarterly with a long lag.** Only `Q` (and derived `A`) frequencies exist for this indicator, no `M`. Latest available as of 2026-08-11 was `2026-Q1` (quarter ended 2026-03-31) — 134 days old under normal operation. No `"quarterly"` tier exists in `CADENCE_TOLERANCE_DAYS` yet; this plan adds one at `180` days (a ~40% cushion over the observed 134-day lag, matching this project's existing override cushion ratios). This is a first calibration from a single observation, flagged as such in the code comment for revisiting once more quarters have been observed in production.
7. **27 years of COFER history show a clear secular decline** (71.2% in 1999 → 57.1% now) — classify `usd_reserve_share` as `TRENDING` (2-year window), not mean-reverting, and add it to `FORWARD_FILL_FIELDS` (quarterly-native data is even sparser than `cb_gold_reserves`'s monthly).

## File Structure

- **`bullion-live-map/fetch_bullion_data.py`** (modify) — generalize `imf_period_to_month_end` → `imf_period_to_end_date` (handles both monthly and quarterly periods), add COFER constants, `fetch_usd_reserve_share()`, `FIELD_META`/new `"quarterly"` tier/`SOURCE_NOTE` entries, `main()` wiring.
- **`bullion-live-map/tests/test_fetch_bullion_data.py`** (modify) — rename/extend the period-converter tests, new `fetch_usd_reserve_share` tests, extend the `FIELD_META` completeness test, extend `TestMainRefusesIncompleteWrites` mocks.
- **`bullion-live-map/backfill_baseline.py`** (modify) — import and call `fetch_usd_reserve_share` in `fetch_all_history()`; classify in `TRENDING_FIELDS`/`FORWARD_FILL_FIELDS`.
- **`bullion-live-map/tests/test_backfill_baseline.py`** (modify) — extend the full-field fixture; new wiring test; new trending/forward-fill regression test.
- **`bullion-live-map/bullion_mkultra.html`** (modify) — `usd` node's `expert` array (split sentence + corrected source attribution), `LIVE_FIELD_LABEL`, `LIVE_FMT`, `NODE_LIVE_FIELD`.
- **`bullion-live-map/bullion_mk18.html`** (modify) — only the new `CADENCE_TOLERANCE_DAYS["quarterly"]` entry synced into its JS mirror.

---

### Task 1: COFER fetcher in `fetch_bullion_data.py`

**Files:**
- Modify: `bullion-live-map/fetch_bullion_data.py`
- Test: `bullion-live-map/tests/test_fetch_bullion_data.py`

**Interfaces:**
- Consumes: `parse_imf_sdmx(data)` from the gold-reserves work, unchanged in behavior (its internal period-conversion call site is retargeted to the renamed function, but its own signature and return shape are untouched).
- Produces: `fetch_usd_reserve_share(start, end) -> (value, ref_date, published, history)` — same 4-tuple shape as every other fetcher, consumed by `main()` here and by `backfill_baseline.fetch_all_history()` in Task 2.
- Produces: `imf_period_to_end_date(period) -> str | None` — replaces `imf_period_to_month_end` (renamed, behavior extended to also accept `"YYYY-Qn"`).

- [ ] **Step 1: Rename `imf_period_to_month_end` and extend it to handle quarterly periods**

In `fetch_bullion_data.py`, replace the existing function:

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
```

with:

```python
def imf_period_to_end_date(period):
    """Convert an SDMX 'YYYY-Mmm' or 'YYYY-Qn' period to its ISO period-end date.

    Handles both monthly (IRFCL gold reserves) and quarterly (COFER)
    periods -- the rest of the SDMX response shape is otherwise identical
    between these two IMF dataflows (confirmed against the live API
    2026-08-12), so a single period converter lets parse_imf_sdmx serve
    both rather than forking a near-duplicate parser. Returns None for
    anything not in one of these two exact shapes.
    """
    if len(period) == 8 and period[4] == "-" and period[5] == "M":
        try:
            year = int(period[:4])
            month = int(period[6:8])
        except ValueError:
            return None
        if not 1 <= month <= 12:
            return None
        last_day = calendar.monthrange(year, month)[1]
        return f"{year:04d}-{month:02d}-{last_day:02d}"
    if len(period) == 7 and period[4] == "-" and period[5] == "Q":
        try:
            year = int(period[:4])
            quarter = int(period[6])
        except ValueError:
            return None
        if not 1 <= quarter <= 4:
            return None
        month = quarter * 3
        last_day = calendar.monthrange(year, month)[1]
        return f"{year:04d}-{month:02d}-{last_day:02d}"
    return None
```

In `parse_imf_sdmx`, change the call site:
```python
            date_iso = imf_period_to_month_end(period)
```
to:
```python
            date_iso = imf_period_to_end_date(period)
```

- [ ] **Step 2: Update the renamed function's tests**

In `tests/test_fetch_bullion_data.py`, replace:
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
```
with:
```python
from fetch_bullion_data import parse_imf_sdmx, imf_period_to_end_date


class TestImfPeriodToEndDate(unittest.TestCase):
    def test_converts_month_period_to_last_day_of_month(self):
        self.assertEqual(imf_period_to_end_date("2026-M07"), "2026-07-31")

    def test_handles_february_in_a_leap_year(self):
        self.assertEqual(imf_period_to_end_date("2024-M02"), "2024-02-29")

    def test_converts_quarter_period_to_last_day_of_quarter(self):
        self.assertEqual(imf_period_to_end_date("2026-Q1"), "2026-03-31")
        self.assertEqual(imf_period_to_end_date("2026-Q2"), "2026-06-30")
        self.assertEqual(imf_period_to_end_date("2026-Q3"), "2026-09-30")
        self.assertEqual(imf_period_to_end_date("2026-Q4"), "2026-12-31")

    def test_unrecognised_shape_returns_none(self):
        self.assertIsNone(imf_period_to_end_date("2026"))
        self.assertIsNone(imf_period_to_end_date("2026-Q5"))
        self.assertIsNone(imf_period_to_end_date(""))
```

- [ ] **Step 3: Run to verify the renamed/extended tests pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data.TestImfPeriodToEndDate -v`
Expected: all PASS.

- [ ] **Step 4: Run the full existing test file to verify the rename didn't break `parse_imf_sdmx`'s own tests**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data.TestParseImfSdmx -v`
Expected: all PASS (these tests only exercise monthly periods, so behavior is unchanged).

- [ ] **Step 5: Add the COFER constants and the new `"quarterly"` tolerance tier**

Add after the `IMF_GOLD_*`/`TROY_OZ_PER_TONNE` block:

```python
# IMF COFER (Currency Composition of Official Foreign Exchange Reserves).
# Unlike IRFCL gold reserves, IMF DOES publish a genuine COUNTRY=G001
# ("World") series for COFER (confirmed against the live API 2026-08-12),
# so this is a single fetch, not a per-country basket. AFXRA = "Allocated
# foreign exchange reserves"; CI_USD = "Claims in US dollar";
# SHRO_PT = "Shares" -- already a plain percentage (e.g. 58.38, not
# 0.5838), no unit conversion needed.
IMF_COFER_BASE_URL = "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/COFER/7.0.1"
IMF_COFER_INDICATOR = "AFXRA"
IMF_COFER_CURRENCY = "CI_USD"
IMF_COFER_TRANSFORM = "SHRO_PT"
```

Change:
```python
CADENCE_TOLERANCE_DAYS = {
    "daily":   7,    # observed 3-4d; absorbs a three-day weekend plus a holiday
    "weekly":  10,   # NFCI (Wed), WALCL/H.4.1 (Thu), Freddie PMMS (Thu) post ~7d
                     # apart; 10 = 7 + slack for a holiday or a one-week slip.
    "monthly": 45,   # observed 6d and 18d; silent for 45d means genuinely broken
    "fomc":    None, # simulated, never judged
}
```
to:
```python
CADENCE_TOLERANCE_DAYS = {
    "daily":   7,    # observed 3-4d; absorbs a three-day weekend plus a holiday
    "weekly":  10,   # NFCI (Wed), WALCL/H.4.1 (Thu), Freddie PMMS (Thu) post ~7d
                     # apart; 10 = 7 + slack for a holiday or a one-week slip.
    "monthly": 45,   # observed 6d and 18d; silent for 45d means genuinely broken
    # First calibration from a single observation (2026-08-11: the latest
    # available COFER quarter was 134 days old under normal, healthy
    # operation) -- revisit once more quarters have been observed in
    # production, the same way monthly's 45d was calibrated from multiple
    # fields over time.
    "quarterly": 180,
    "fomc":    None, # simulated, never judged
}
```

- [ ] **Step 6: Add the `FIELD_META` entry**

After the `cb_gold_reserves` entry in `FIELD_META`, add:

```python
    "usd_reserve_share": {"class": "measured", "cadence": "quarterly",
                           "source": "IMF COFER (allocated reserves, USD share)"},
```

- [ ] **Step 7: Write the failing `fetch_usd_reserve_share` tests**

Add to `tests/test_fetch_bullion_data.py`:

```python
from fetch_bullion_data import fetch_usd_reserve_share


class TestFetchUsdReserveShare(unittest.TestCase):
    def setUp(self):
        self._orig = fbd_module.http_get_json

    def tearDown(self):
        fbd_module.http_get_json = self._orig

    PAYLOAD = {
        "data": {
            "dataSets": [{
                "series": {
                    "0:0:0:0:0": {
                        "observations": {
                            "0": ["58.3839225769043", None, 0, None],
                            "1": ["57.130786895752", None, 0, None],
                        }
                    }
                }
            }],
            "structures": [{
                "dimensions": {
                    "observation": [{
                        "values": [{"value": "2025-Q4"}, {"value": "2026-Q1"}],
                    }]
                }
            }],
        }
    }

    def test_returns_latest_rounded_percentage(self):
        fbd_module.http_get_json = lambda url: self.PAYLOAD

        value, ref, pub, history = fetch_usd_reserve_share("2025-01-01", "2026-08-12")

        self.assertEqual(value, 57.1)
        self.assertEqual(ref, "2026-03-31")
        self.assertEqual(pub, ref, "COFER exposes no separate publication date")
        self.assertEqual(history, {"2025-12-31": 58.4, "2026-03-31": 57.1})

    def test_http_error_returns_all_none(self):
        def raise_timeout(url):
            raise TimeoutError("boom")
        fbd_module.http_get_json = raise_timeout

        value, ref, pub, history = fetch_usd_reserve_share("2025-01-01", "2026-08-12")

        self.assertIsNone(value)
        self.assertIsNone(ref)
        self.assertIsNone(pub)
        self.assertEqual(history, {})

    def test_malformed_response_returns_all_none(self):
        fbd_module.http_get_json = lambda url: {}

        value, ref, pub, history = fetch_usd_reserve_share("2025-01-01", "2026-08-12")

        self.assertIsNone(value)
        self.assertEqual(history, {})
```

- [ ] **Step 8: Run to verify the tests fail**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data.TestFetchUsdReserveShare -v`
Expected: `ImportError: cannot import name 'fetch_usd_reserve_share'`.

- [ ] **Step 9: Implement `fetch_usd_reserve_share`**

Add after `fetch_imf_gold_reserves_basket` in `fetch_bullion_data.py`:

```python
def fetch_usd_reserve_share(start, end):
    """Network wrapper: USD share of allocated global FX reserves, in percent.

    Reuses parse_imf_sdmx directly -- COFER's SDMX response shape is
    identical to IRFCL's (confirmed against the live API 2026-08-12), and
    IMF publishes a genuine COUNTRY=G001 ("World") series for COFER, unlike
    IRFCL gold reserves, so no per-country basket/sum is needed here.

    Returns (latest_value, ref_date, published, history) in the same shape
    every other fetcher produces, or (None, None, None, {}) on any HTTP
    error or unparseable response -- same non-raising convention as the
    rest of this file. ref_date and published are identical: COFER exposes
    no separate publication/vintage date, same situation as IRFCL.
    """
    start_period = start[:7]  # "YYYY-MM-DD" -> "YYYY-MM"
    url = (f"{IMF_COFER_BASE_URL}/G001.{IMF_COFER_INDICATOR}.{IMF_COFER_CURRENCY}."
           f"{IMF_COFER_TRANSFORM}.Q?c%5BTIME_PERIOD%5D=ge:{start_period}")
    try:
        data = http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        print(f"  IMF COFER: fetch failed ({e})", file=sys.stderr)
        return (None, None, None, {})
    hist = parse_imf_sdmx(data)
    if not hist:
        print("  IMF COFER: unexpected response shape or no usable data", file=sys.stderr)
        return (None, None, None, {})
    rounded = {d: round(v, 1) for d, v in hist.items()}
    latest_ref = max(rounded)
    return (rounded[latest_ref], latest_ref, latest_ref, rounded)
```

- [ ] **Step 10: Run to verify the tests pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data.TestFetchUsdReserveShare -v`
Expected: all PASS.

- [ ] **Step 11: Wire into `main()` and extend `SOURCE_NOTE`**

In `main()`, after the `cb_gold_reserves` block and before `if not history_by_date:`, add:

```python
    cofer_value, cofer_ref, cofer_pub, cofer_hist = fetch_usd_reserve_share(start, end)
    if cofer_value is not None:
        latest_out["usd_reserve_share"] = {"value": cofer_value, "ref_date": cofer_ref, "published": cofer_pub}
    for date_str, val in cofer_hist.items():
        history_by_date.setdefault(date_str, {})["usd_reserve_share"] = val
```

Append to `SOURCE_NOTE` (before the closing `)`):
```python
    " usd_reserve_share: IMF COFER (Currency Composition of Official "
    "Foreign Exchange Reserves), share of allocated reserves held in USD, "
    "world aggregate."
```

- [ ] **Step 12: Extend `TestBuildEnvelope.test_every_known_field_has_metadata`**

In `tests/test_fetch_bullion_data.py`, change:
```python
        expected = {"us2y", "us10y", "vix", "ffr", "wti_px", "cpi_yoy",
                    "nfp_mom", "gold_px", "dxy", "spx",
                    "nfci", "m2", "mortgage_30y", "hy_oas", "ig_oas",
                    "sofr", "tbill_3m", "fed_bs", "rrp",
                    "xlk", "xlf", "xle", "xlp", "cb_gold_reserves"}
```
to:
```python
        expected = {"us2y", "us10y", "vix", "ffr", "wti_px", "cpi_yoy",
                    "nfp_mom", "gold_px", "dxy", "spx",
                    "nfci", "m2", "mortgage_30y", "hy_oas", "ig_oas",
                    "sofr", "tbill_3m", "fed_bs", "rrp",
                    "xlk", "xlf", "xle", "xlp", "cb_gold_reserves",
                    "usd_reserve_share"}
```

Also change the cadence set on the next lines from:
```python
            self.assertIn(meta["cadence"], {"daily", "weekly", "monthly", "fomc"})
```
to:
```python
            self.assertIn(meta["cadence"], {"daily", "weekly", "monthly", "quarterly", "fomc"})
```

- [ ] **Step 13: Update `TestMainRefusesIncompleteWrites` to mock the new fetch call**

In `setUp`, add:
```python
        self._orig_fetch_cofer = self.mod.fetch_usd_reserve_share
```
In `tearDown`, add:
```python
        self.mod.fetch_usd_reserve_share = self._orig_fetch_cofer
```
In `test_total_outage_exits_without_touching_existing_file`, add alongside the other mock assignments:
```python
        self.mod.fetch_usd_reserve_share = (
            lambda start, end: (1.0, "2026-07-17", "2026-07-17", {}))
```
In `test_partial_fetch_exits_without_writing_truncated_file`, add alongside the other mock assignments:
```python
        self.mod.fetch_usd_reserve_share = (
            lambda start, end: (57.0, "2026-07-17", "2026-07-17", {"2026-07-17": 57.0}))
```

- [ ] **Step 14: Run the full fetch_bullion_data test file**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_bullion_data -v`
Expected: all PASS.

- [ ] **Step 15: Live-fetch dry run against the real COFER endpoint**

Run:
```bash
cd bullion-live-map && python3 -c "
from datetime import datetime, timedelta, timezone
from fetch_bullion_data import fetch_usd_reserve_share
today = datetime.now(timezone.utc).date()
start = (today - timedelta(days=400)).isoformat()
end = today.isoformat()
print(fetch_usd_reserve_share(start, end))
"
```
Expected: a tuple with a non-None float value in the mid-to-high 50s (percent), a `YYYY-MM-DD` ref date on a quarter boundary, and a multi-entry history dict. If the value has drifted outside this range or the call fails closed, investigate before proceeding — do not assume the fixture-based tests above are sufficient proof the live integration works.

- [ ] **Step 16: Commit**

```bash
git add bullion-live-map/fetch_bullion_data.py bullion-live-map/tests/test_fetch_bullion_data.py
git commit -m "Mk Ultra: fetch IMF COFER USD reserve-currency share"
```

---

### Task 2: Wire COFER into `backfill_baseline.py`

**Files:**
- Modify: `bullion-live-map/backfill_baseline.py`
- Test: `bullion-live-map/tests/test_backfill_baseline.py`

**Interfaces:**
- Consumes: `fetch_usd_reserve_share(start, end)` from Task 1, same 4-tuple shape.
- Produces: `usd_reserve_share` present in `TRENDING_FIELDS`, `FORWARD_FILL_FIELDS`, and (transitively) `EXPECTED_BASELINE_FIELDS`.

- [ ] **Step 1: Import the new fetcher**

Change:
```python
from fetch_bullion_data import (
    FRED_SERIES, YAHOO_SYMBOLS, KEY_PATH, fetch_yahoo_symbol,
    http_get_json, fred_url, parse_fred_observations,
    fetch_imf_gold_reserves_basket,
)
```
to:
```python
from fetch_bullion_data import (
    FRED_SERIES, YAHOO_SYMBOLS, KEY_PATH, fetch_yahoo_symbol,
    http_get_json, fred_url, parse_fred_observations,
    fetch_imf_gold_reserves_basket, fetch_usd_reserve_share,
)
```

- [ ] **Step 2: Write the failing classification test**

Add a new test method inside `TestBuildBaseline` (alongside the `cb_gold_reserves` one):

```python
    def test_usd_reserve_share_is_trending_and_forward_filled(self):
        from datetime import datetime, timedelta, timezone
        base = datetime.now(timezone.utc)
        dense_dates = [(base - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(27, -1, -1)]
        history = self._synthetic_history()
        # usd_reserve_share only reports on every 10th dense date, mirroring
        # its real quarterly sparsity against the other fields' daily grid.
        sparse_dates = dense_dates[::10]
        history["usd_reserve_share"] = {d: 57.0 for d in sparse_dates}

        baseline = build_baseline(history)

        stats = baseline["fields"]["usd_reserve_share"]
        self.assertEqual(stats["window_years"], RECENT_WINDOW_YEARS)
        self.assertGreater(stats["n"], len(sparse_dates),
                            "forward-fill should carry usd_reserve_share onto the dense grid")
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline.TestBuildBaseline.test_usd_reserve_share_is_trending_and_forward_filled -v`
Expected: FAIL — `KeyError: 'usd_reserve_share'`.

- [ ] **Step 4: Add the classification**

Change:
```python
TRENDING_FIELDS = ["spx", "fed_bs", "rrp", "cb_gold_reserves"]
```
to:
```python
# usd_reserve_share: a 1999-2026 pull of COFER's USD allocated-reserve
# share shows a clear secular decline (71.2% -> 57.1%), the "de-
# dollarization" trend -- trending, not mean-reverting, same reasoning as
# cb_gold_reserves (verified 2026-08-12, see
# docs/superpowers/plans/2026-08-12-bullion-mkultra-imf-cofer.md).
TRENDING_FIELDS = ["spx", "fed_bs", "rrp", "cb_gold_reserves", "usd_reserve_share"]
```

Change:
```python
FORWARD_FILL_FIELDS = ["fed_bs", "cb_gold_reserves"]
```
to:
```python
# usd_reserve_share's native quarterly cadence is even sparser than
# cb_gold_reserves' monthly one.
FORWARD_FILL_FIELDS = ["fed_bs", "cb_gold_reserves", "usd_reserve_share"]
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline.TestBuildBaseline.test_usd_reserve_share_is_trending_and_forward_filled -v`
Expected: PASS.

- [ ] **Step 6: Write the failing `fetch_all_history` wiring test**

Add a new test class (alongside `TestFetchAllHistoryIncludesImfBasket`):

```python
class TestFetchAllHistoryIncludesCofer(unittest.TestCase):
    def test_fetch_all_history_calls_the_cofer_fetcher(self):
        # FRED_SERIES/YAHOO_SYMBOLS/fetch_imf_gold_reserves_basket are
        # stubbed so this makes no real network calls for those paths --
        # only the COFER wiring is under test here.
        import backfill_baseline as bb_module
        orig_cofer = bb_module.fetch_usd_reserve_share
        orig_gold = bb_module.fetch_imf_gold_reserves_basket
        orig_fred = bb_module.FRED_SERIES
        orig_yahoo = bb_module.YAHOO_SYMBOLS
        called = {}

        def fake_cofer(start, end):
            called["args"] = (start, end)
            return (57.1, "2026-03-31", "2026-03-31", {"2026-03-31": 57.1})

        bb_module.fetch_usd_reserve_share = fake_cofer
        bb_module.fetch_imf_gold_reserves_basket = lambda start, end: (25000.0, "2026-06-30", "2026-06-30", {})
        bb_module.FRED_SERIES = {}
        bb_module.YAHOO_SYMBOLS = {}
        try:
            out = bb_module.fetch_all_history("dummy-key", "2011-01-01", "2026-08-12")
        finally:
            bb_module.fetch_usd_reserve_share = orig_cofer
            bb_module.fetch_imf_gold_reserves_basket = orig_gold
            bb_module.FRED_SERIES = orig_fred
            bb_module.YAHOO_SYMBOLS = orig_yahoo

        self.assertEqual(called["args"], ("2011-01-01", "2026-08-12"))
        self.assertEqual(out["usd_reserve_share"], {"2026-03-31": 57.1})
```

- [ ] **Step 7: Run to verify it fails**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline.TestFetchAllHistoryIncludesCofer -v`
Expected: FAIL (`fetch_all_history` doesn't call `fetch_usd_reserve_share` yet).

- [ ] **Step 8: Wire the call into `fetch_all_history()`**

After the `fetch_imf_gold_reserves_basket` call and before `return out`, add:

```python
    _, _, _, cofer_hist = fetch_usd_reserve_share(start, end)
    out["usd_reserve_share"] = cofer_hist
```

- [ ] **Step 9: Run to verify it passes**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline.TestFetchAllHistoryIncludesCofer -v`
Expected: PASS.

- [ ] **Step 10: Extend the completeness-gate fixture**

In `TestMissingBaselineFields._full_synthetic_history()`, add `"usd_reserve_share"` to the field-name list:
```python
        for i, f in enumerate(["hy_oas", "ig_oas", "sofr", "tbill_3m", "us10y", "us2y",
                                "vix", "spx", "fed_bs", "rrp", "ffr", "cpi_yoy", "dxy", "wti_px",
                                "nfp_mom", "cb_gold_reserves", "usd_reserve_share"]):
```

- [ ] **Step 11: Run the full backfill_baseline test file**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline -v`
Expected: all PASS.

- [ ] **Step 12: Live-fetch dry run**

Run: `cd bullion-live-map && python3 backfill_baseline.py`
Expected: succeeds, prints `BASELINE_STATS refreshed: N fields, ...` with N now including `usd_reserve_share`, and `git diff bullion_mkultra.html` shows the `BASELINE_STATS` block gaining a `usd_reserve_share` entry with `"window_years": 2`.

- [ ] **Step 13: Commit**

```bash
git add bullion-live-map/backfill_baseline.py bullion-live-map/tests/test_backfill_baseline.py bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: classify usd_reserve_share as trending, wire into baseline backfill"
```

---

### Task 3: `bullion_mkultra.html` node text and live-field wiring, plus mk18 parity sync

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html`
- Modify: `bullion-live-map/bullion_mk18.html`

**Interfaces:**
- Consumes: `usd_reserve_share` field in `data.json`, written by Task 1's `main()` run.

- [ ] **Step 1: Replace the `usd` node's stale expert-text lines**

At `bullion_mkultra.html` (near the `usd` node, currently around line 1207-1211), change:

```javascript
    expert:[
      'DXY is trade-weighted against six currencies (EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD, SEK, CHF). The weights are fixed by the index rules, not re-estimated.',
      'A strong dollar tightens global financial conditions.',
      'Roughly 60% of FX reserves and 40 to 50% of trade invoices were in USD as of 2022.',
      'Source: ICE (DXY index weights); BIS and IMF COFER (reserve and invoicing shares, 2022).'] },
```

to:

```javascript
    expert:[
      'DXY is trade-weighted against six currencies (EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD, SEK, CHF). The weights are fixed by the index rules, not re-estimated.',
      'A strong dollar tightens global financial conditions.',
      'The dollar remains the dominant reserve currency, though its share of allocated global FX reserves has been on a slow structural decline for over two decades -- tracked live here.',
      'Source: ICE (DXY index weights); IMF COFER (allocated reserve currency shares).',
      'Roughly 40 to 50% of trade invoices were in USD as of 2022 (no live source for this figure).',
      'Source: BIS (trade invoicing currency shares, 2022).'] },
```

- [ ] **Step 2: Add the field to `LIVE_FIELD_LABEL`**

Change:
```javascript
const LIVE_FIELD_LABEL = { ..., cb_gold_reserves:'CB Gold (Top 11)' };
```
to (append before the closing `};`):
```javascript
, usd_reserve_share:'USD Reserve Share'
```

- [ ] **Step 3: Add the field to `LIVE_FMT`**

In the `LIVE_FMT` object, add:
```javascript
  usd_reserve_share:v=>(+v).toFixed(1)+'%',
```

- [ ] **Step 4: Add the field to `NODE_LIVE_FIELD`**

Change:
```javascript
  yield: ['us10y', 'us2y'], equit: ['spx'], gold: ['gold_px', 'cb_gold_reserves'], usd: ['dxy'], oil: ['wti_px'],
```
to:
```javascript
  yield: ['us10y', 'us2y'], equit: ['spx'], gold: ['gold_px', 'cb_gold_reserves'], usd: ['dxy', 'usd_reserve_share'], oil: ['wti_px'],
```

- [ ] **Step 5: Sync the new tolerance tier into `bullion_mk18.html`**

In `bullion_mk18.html`, find the `CADENCE_TOLERANCE_DAYS` JS constant and add the `quarterly` entry so it matches Task 1's Python table exactly (this file gets the minimal tolerance-table sync only, per the user's standing choice — not the node text or live-field maps above).

- [ ] **Step 6: Run the freshness-parity tests**

Run: `cd bullion-live-map && python3 -m unittest tests.test_freshness_parity -v`
Expected: all PASS (both `bullion_mkultra.html` and `bullion_mk18.html` now agree with Python's `CADENCE_TOLERANCE_DAYS`).

- [ ] **Step 7: sha256sum check on truly-frozen files**

Run:
```bash
cd bullion-live-map && sha256sum bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html > /tmp/frozen_before_cofer.txt
git diff --stat -- bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html
```
Expected: empty diff.

- [ ] **Step 8: Browser verification**

Use the `headless-chrome-verification` skill to serve `bullion-live-map/` over `http://localhost` and open the `usd` node's detail panel. Confirm:
- The live reading shows both `Dollar (DXY)` and `USD Reserve Share`, the latter formatted like `57.1%`.
- The expert-text panel shows the new split sentences with no reference to "60% of FX reserves" tied to a 2022 date, and the invoicing sentence still appears, now separately sourced to BIS.
- No console errors.

- [ ] **Step 9: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html bullion-live-map/bullion_mk18.html
git commit -m "Mk Ultra: replace usd node's stale COFER citation with live IMF reserve-share reading"
```

---

### Task 4: Whole-branch verification

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests -v`
Expected: all green. Baseline going into this plan was 97 tests; this plan adds roughly 10-12 (Task 1: 4 renamed/extended period-converter tests + 3 `TestFetchUsdReserveShare` tests; Task 2: 1 classification test + 1 wiring test), so expect somewhere around 107-109 tests, 0 failures.

- [ ] **Step 2: Live-fetch dry run of both scripts for real**

Run:
```bash
cd bullion-live-map
python3 fetch_bullion_data.py
python3 backfill_baseline.py
```
Expected: both exit 0. `fetch_bullion_data.py`'s printed "Publication ages" table includes a `usd_reserve_share` row; confirm its age is comfortably under 180 (the new tolerance tier) — if it is at or past 180, that is new information about the real-world lag and the tier in Task 1 Step 5 should be revisited, not silently ignored.

- [ ] **Step 3: Frozen-file check**

Run: `cd bullion-live-map && sha256sum bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html | diff - /tmp/frozen_before_cofer.txt`
Expected: no output (identical).

- [ ] **Step 4: git status check**

Run: `git status`
Expected: clean except `data.json`/`bullion_mkultra.html` (Step 2's live dry run legitimately updates them, same as the gold-reserves work) and this plan's own doc if not yet committed.

- [ ] **Step 5: Commit any residual dry-run artifacts and confirm push with the user**

If Step 2's dry run left `data.json`/`bullion_mkultra.html` modified beyond what Task 2/3 already committed, commit that refresh (mirroring how the gold-reserves plan's Task 4 handled the same situation). Then confirm with the user whether to push — do not push without asking, even though the prior gold-reserves session's commits are already on `origin/main`.
