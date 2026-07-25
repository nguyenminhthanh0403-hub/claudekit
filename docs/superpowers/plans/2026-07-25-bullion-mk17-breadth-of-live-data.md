# Bullion Mk17 — Breadth of Live Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 13 new free live-data fields to the durable pipeline and wire them into a new `bullion_mk17.html`, promoting every calibratable link to a MEASURED badge.

**Architecture:** Extend the headless GitHub Action pipeline (`fetch_bullion_data.py` → `data.json`) with 9 FRED + 4 Yahoo series (no MCP, no new runtime dependency). Regenerate `data.json`, calibrate the new field→node links offline with `calibrate.py`, then cut `bullion_mk17.html` from mk16 via `release.sh` and surface the new fields in the Live-metrics grid, the node detail panel, and the client elasticity/backtest maps.

**Tech Stack:** Python 3 stdlib (urllib, json, `unittest`); single-file HTML + vanilla JS + D3 (already vendored, minified, inline); GitHub Actions cron; GitHub Pages.

## Global Constraints

- **No MCP, no new dependency.** All data via free REST (FRED official API + Yahoo chart API). Pipeline must keep degrading gracefully to the simulated baseline on any fetch failure (`file://` or 404).
- **Node count stays 39.** NFCI attaches to the existing `vix` node; the Overview board layout `perCol [3,3,6,3,8,10,6]` must not change.
- **Freeze prior versions.** `release.sh 17` only creates `bullion_mk17.html` and edits `index.html`. Verify `bullion_mk16.html` and `bullion_mk15.html` (frozen `ebfaaaf6…`) stay byte-identical.
- **Provenance is mandatory.** Every field written to `data.json` MUST have a `FIELD_META` entry — `build_envelope` raises otherwise. This is the honesty guarantee, not optional.
- **FOMC odds stay simulated.** No free durable source; out of scope.
- **Mk Ultra wiring is out of scope.** It still receives the new `data.json` values automatically (all versions fetch the same file); its link set is not touched here.
- **Cadence buckets:** daily=7d (existing), **weekly=10d (new)**, monthly=45d (existing). Assignment — daily: hy_oas, ig_oas, sofr, rrp, tbill_3m, xlk, xlf, xle, xlp; weekly: nfci, mortgage_30y, fed_bs; monthly: m2.
- **Working dir for all commands:** `bullion-live-map/` inside the `claudekit` repo.
- **Field name ↔ FRED/Yahoo id map (authoritative):**
  `nfci`←`NFCI`, `m2`←`M2SL`, `mortgage_30y`←`MORTGAGE30US`, `hy_oas`←`BAMLH0A0HYM2`, `ig_oas`←`BAMLC0A0CM`, `sofr`←`SOFR`, `tbill_3m`←`DTB3`, `fed_bs`←`WALCL`, `rrp`←`RRPONTSYD`, `xlk`←`XLK`, `xlf`←`XLF`, `xle`←`XLE`, `xlp`←`XLP`.

---

### Task 1: Pipeline — add the weekly cadence bucket + 13 new series

**Files:**
- Modify: `bullion-live-map/fetch_bullion_data.py` — `CADENCE_TOLERANCE_DAYS`, `FRED_SERIES`, `YAHOO_SYMBOLS`, `FIELD_META`, `SOURCE_NOTE`.
- Create: `bullion-live-map/test_fetch_bullion_data.py` — invariant + freshness tests.

**Interfaces:**
- Consumes: existing `freshness_verdict(cadence, published, today, override_days=None)`, `build_envelope`, `FIELD_META`, `FRED_SERIES`, `YAHOO_SYMBOLS`.
- Produces: `data.json` will (after Task 2) carry 13 new field keys, each with a `FIELD_META`-backed provenance envelope and correct freshness cadence.

- [ ] **Step 1: Write the failing test**

Create `bullion-live-map/test_fetch_bullion_data.py`:

```python
import datetime as dt
import unittest
import fetch_bullion_data as f

NEW_FRED = {"NFCI","M2SL","MORTGAGE30US","BAMLH0A0HYM2","BAMLC0A0CM",
            "SOFR","DTB3","WALCL","RRPONTSYD"}
NEW_YAHOO = {"XLK","XLF","XLE","XLP"}

class TestWeeklyCadence(unittest.TestCase):
    def test_weekly_bucket_exists(self):
        self.assertEqual(f.CADENCE_TOLERANCE_DAYS.get("weekly"), 10)

    def test_weekly_fresh_at_8_days(self):
        pub = dt.date(2026, 7, 17)
        today = dt.date(2026, 7, 25)  # 8 days later
        state, age = f.freshness_verdict("weekly", pub, today)
        self.assertEqual(state, "fresh")
        self.assertEqual(age, 8)

    def test_weekly_flagged_past_10_days(self):
        pub = dt.date(2026, 7, 12)
        today = dt.date(2026, 7, 25)  # 13 days later
        state, _ = f.freshness_verdict("weekly", pub, today)
        self.assertEqual(state, "flagged")

class TestProvenanceCoverage(unittest.TestCase):
    def test_every_series_has_field_meta(self):
        # Mirrors build_envelope's guarantee: no field ships without provenance.
        fred_fields = {out for (out, _units, _dec) in f.FRED_SERIES.values()}
        yahoo_fields = {out for (out, _dec) in f.YAHOO_SYMBOLS.values()}
        for name in fred_fields | yahoo_fields:
            self.assertIn(name, f.FIELD_META, f"{name} missing FIELD_META")

    def test_new_series_present(self):
        self.assertTrue(NEW_FRED.issubset(set(f.FRED_SERIES.keys())))
        self.assertTrue(NEW_YAHOO.issubset(set(f.YAHOO_SYMBOLS.keys())))

    def test_new_field_cadences(self):
        want = {"nfci":"weekly","fed_bs":"weekly","mortgage_30y":"weekly",
                "m2":"monthly","sofr":"daily","rrp":"daily","tbill_3m":"daily",
                "hy_oas":"daily","ig_oas":"daily",
                "xlk":"daily","xlf":"daily","xle":"daily","xlp":"daily"}
        for field, cad in want.items():
            self.assertEqual(f.FIELD_META[field]["cadence"], cad, field)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd bullion-live-map && python3 -m unittest test_fetch_bullion_data -v`
Expected: FAIL — `weekly` bucket missing / new series not in `FRED_SERIES` / `KeyError` on `FIELD_META`.

- [ ] **Step 3: Add the weekly cadence bucket**

In `fetch_bullion_data.py`, edit `CADENCE_TOLERANCE_DAYS`:

```python
CADENCE_TOLERANCE_DAYS = {
    "daily":   7,    # observed 3-4d; absorbs a three-day weekend plus a holiday
    "weekly":  10,   # NFCI (Wed), WALCL/H.4.1 (Thu), Freddie PMMS (Thu) post ~7d
                     # apart; 10 = 7 + slack for a holiday or a one-week slip.
    "monthly": 45,   # observed 6d and 18d; silent for 45d means genuinely broken
    "fomc":    None, # simulated, never judged
}
```

- [ ] **Step 4: Add the 9 FRED + 4 Yahoo series**

Edit `FRED_SERIES` (append after `PAYEMS`):

```python
FRED_SERIES = {
    "DGS2":       ("us2y",    None,  2),
    "DGS10":      ("us10y",   None,  2),
    "CPILFESL":   ("cpi_yoy", "pc1", 1),
    "VIXCLS":     ("vix",     None,  1),
    "DFF":        ("ffr",     None,  2),
    "DCOILWTICO": ("wti_px",  None,  2),
    "PAYEMS":     ("nfp_mom", "chg", 0),
    # Mk17 breadth
    "NFCI":         ("nfci",         None, 2),
    "M2SL":         ("m2",           None, 1),
    "MORTGAGE30US": ("mortgage_30y", None, 2),
    "BAMLH0A0HYM2": ("hy_oas",       None, 2),
    "BAMLC0A0CM":   ("ig_oas",       None, 2),
    "SOFR":         ("sofr",         None, 2),
    "DTB3":         ("tbill_3m",     None, 2),
    "WALCL":        ("fed_bs",       None, 1),
    "RRPONTSYD":    ("rrp",          None, 1),
}
```

Edit `YAHOO_SYMBOLS` (append after `^GSPC`):

```python
YAHOO_SYMBOLS = {
    "GC=F":      ("gold_px", 2),
    "DX-Y.NYB":  ("dxy",     2),
    "^GSPC":     ("spx",     2),
    # Mk17 sector ETFs
    "XLK":       ("xlk", 2),
    "XLF":       ("xlf", 2),
    "XLE":       ("xle", 2),
    "XLP":       ("xlp", 2),
}
```

- [ ] **Step 5: Add FIELD_META entries for all 13 fields**

Append inside `FIELD_META` (before the closing `}`):

```python
    # Mk17 breadth
    "nfci":         {"class": "measured", "cadence": "weekly",  "source": "FRED NFCI"},
    "m2":           {"class": "measured", "cadence": "monthly", "source": "FRED M2SL"},
    "mortgage_30y": {"class": "measured", "cadence": "weekly",  "source": "FRED MORTGAGE30US"},
    "hy_oas":       {"class": "measured", "cadence": "daily",   "source": "FRED BAMLH0A0HYM2"},
    "ig_oas":       {"class": "measured", "cadence": "daily",   "source": "FRED BAMLC0A0CM"},
    "sofr":         {"class": "measured", "cadence": "daily",   "source": "FRED SOFR"},
    "tbill_3m":     {"class": "measured", "cadence": "daily",   "source": "FRED DTB3"},
    "fed_bs":       {"class": "measured", "cadence": "weekly",  "source": "FRED WALCL"},
    "rrp":          {"class": "measured", "cadence": "daily",   "source": "FRED RRPONTSYD"},
    "xlk":          {"class": "measured", "cadence": "daily",   "source": "Yahoo XLK"},
    "xlf":          {"class": "measured", "cadence": "daily",   "source": "Yahoo XLF"},
    "xle":          {"class": "measured", "cadence": "daily",   "source": "Yahoo XLE"},
    "xlp":          {"class": "measured", "cadence": "daily",   "source": "Yahoo XLP"},
```

- [ ] **Step 6: Update SOURCE_NOTE**

Replace the `SOURCE_NOTE` string's final sentence area so it documents the new sources. Set `SOURCE_NOTE` to:

```python
SOURCE_NOTE = (
    "us2y/us10y/vix/ffr/wti_px: FRED daily series (DGS2, DGS10, VIXCLS, DFF, "
    "DCOILWTICO), official supported API. cpi_yoy: FRED CPILFESL, percent "
    "change from year ago. nfp_mom: FRED PAYEMS, month-over-month change "
    "(thousands). Mk17 adds FRED NFCI (financial conditions, weekly), M2SL "
    "(money supply, monthly), MORTGAGE30US (30Y mortgage, weekly), "
    "BAMLH0A0HYM2/BAMLC0A0CM (HY/IG credit OAS), SOFR, DTB3 (3M bill), WALCL "
    "(Fed balance sheet, weekly) and RRPONTSYD (overnight RRP). "
    "gold_px/dxy/spx and the Mk17 sector ETFs XLK/XLF/XLE/XLP: Yahoo Finance "
    "chart API — unofficial and undocumented, unlike FRED; could change or "
    "rate-limit without notice. FOMC hike/cut odds have no free source and "
    "remain simulated."
)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd bullion-live-map && python3 -m unittest test_fetch_bullion_data -v`
Expected: PASS (all tests green).

- [ ] **Step 8: Commit**

```bash
cd bullion-live-map
git add fetch_bullion_data.py test_fetch_bullion_data.py
git commit -m "Mk17: add weekly cadence bucket + 13 new FRED/Yahoo series"
```

---

### Task 2: Regenerate data.json with the new fields

**Files:**
- Modify (generated): `bullion-live-map/data.json`

**Interfaces:**
- Consumes: Task 1's `FRED_SERIES`/`YAHOO_SYMBOLS`/`FIELD_META`; FRED API key at `~/.config/bullion/fred_api_key`.
- Produces: a `data.json` whose `history` object and `fields` snapshot contain the 13 new field keys — required input for Task 3's calibration.

- [ ] **Step 1: Run the fetch**

Run: `cd bullion-live-map && python3 fetch_bullion_data.py`
Expected: exits 0, prints a written-fields summary; no `KeyError` (which would mean a missing `FIELD_META`).

Note: needs network + the FRED key. If the key is absent, the script prints the setup hint and exits non-zero — stop and report to the user; do not fabricate data.

- [ ] **Step 2: Verify the new fields landed**

Run:
```bash
cd bullion-live-map && python3 -c "import json; d=json.load(open('data.json')); \
print(sorted(d['fields'].keys())); \
print('nfci in fields:', 'nfci' in d['fields']); \
print('xlk in some history row:', any('xlk' in v for v in d['history'].values()))"
```
Expected: field list includes `nfci, m2, mortgage_30y, hy_oas, ig_oas, sofr, tbill_3m, fed_bs, rrp, xlk, xlf, xle, xlp`; both booleans `True`.

- [ ] **Step 3: Commit**

```bash
cd bullion-live-map
git add data.json
git commit -m "Mk17: regenerate data.json with 13 new live fields"
```

---

### Task 3: Calibrate the new field→node candidate links

**Files:**
- Modify: `bullion-live-map/calibrate.py` — append to `CELLS`.
- Modify: `bullion-live-map/test_calibrate.py` — add a well-formedness test for the new cells.
- Modify (generated): `bullion-live-map/calibration_report.txt`

**Interfaces:**
- Consumes: `fit_cell`, `verdict`, `CELLS`, the regenerated `data.json` from Task 2.
- Produces: a printed MEASURED/DIRECTIONAL verdict per new cell in `calibration_report.txt`, consumed by Task 7 to decide which client links get a fitted beta.

- [ ] **Step 1: Write the failing test**

Add to `bullion-live-map/test_calibrate.py` (new class near the end, before the `unittest.main()` guard):

```python
class TestMk17Cells(unittest.TestCase):
    MK17_TARGETS = {'mortgage_30y','xlk','xlf','xle','xlp','hy_oas','sofr','tbill_3m'}
    def test_mk17_cells_present_and_wellformed(self):
        tgt_fields = {tgtfield for (_d, _k, tgtfield, _kind, _hand) in c.CELLS}
        self.assertTrue(self.MK17_TARGETS.issubset(tgt_fields),
                        f"missing Mk17 target cells: {self.MK17_TARGETS - tgt_fields}")
        for (drv, key, tgtfield, kind, hand) in c.CELLS:
            self.assertIn(kind, ('level','pct','add'), f"{key} bad kind {kind}")
            self.assertIsInstance(hand, (int, float))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd bullion-live-map && python3 -m unittest test_calibrate -v`
Expected: FAIL — `missing Mk17 target cells: {...}`.

- [ ] **Step 3: Add candidate cells to CELLS**

Append to the `CELLS` list in `calibrate.py` (hand signs are the mechanism's expected direction; `verdict()` keeps only those the fit agrees with):

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd bullion-live-map && python3 -m unittest test_calibrate -v`
Expected: PASS.

- [ ] **Step 5: Run the calibration report**

Run: `cd bullion-live-map && python3 calibrate.py data.json`
Expected: prints one line per cell ending in `MEASURED (...)` or `DIRECTIONAL (...)`. Record which of the 9 Mk17 cells are MEASURED and their fitted `slope`/`t`/`r` — Task 7 consumes these. Several MEASURED (e.g. sector-ETF-on-SPX and mortgage-on-10Y are strong contemporaneous fits); some may land DIRECTIONAL — that is the honest outcome.

- [ ] **Step 6: Commit**

```bash
cd bullion-live-map
git add calibrate.py test_calibrate.py calibration_report.txt
git commit -m "Mk17: calibrate new field->node candidate links"
```

---

### Task 4: Cut bullion_mk17.html from mk16

**Files:**
- Create: `bullion-live-map/bullion_mk17.html` (via `release.sh`)
- Modify: `bullion-live-map/index.html` (repointed by `release.sh`)

**Interfaces:**
- Consumes: `release.sh`, current `bullion_mk16.html`.
- Produces: `bullion_mk17.html` (byte-copy of mk16 with title/og/h1 bumped) — the surface all later tasks edit.

- [ ] **Step 1: Record prior-version hashes**

Run: `cd bullion-live-map && shasum -a 256 bullion_mk16.html bullion_mk15.html`
Expected: prints two hashes; note them (mk15 should start `ebfaaaf6`).

- [ ] **Step 2: Cut the release**

Run: `cd bullion-live-map && ./release.sh 17`
Expected: creates `bullion_mk17.html`, bumps `<title>`/`og:title`/`<h1>` to Mk17, repoints `index.html` → `bullion_mk17.html`.

- [ ] **Step 3: Verify prior versions unchanged + index repointed**

Run:
```bash
cd bullion-live-map
shasum -a 256 bullion_mk16.html bullion_mk15.html   # must match Step 1
grep -o "bullion_mk17.html" index.html | head -1     # index now points at mk17
grep -c "Mk17" bullion_mk17.html                     # title/og/h1 bumped
```
Expected: mk16/mk15 hashes identical to Step 1; `index.html` references `bullion_mk17.html`; `Mk17` count ≥ 3.

- [ ] **Step 4: Commit**

```bash
cd bullion-live-map
git add bullion_mk17.html index.html
git commit -m "Mk17: cut bullion_mk17.html from mk16 via release.sh"
```

---

### Task 5: Surface the new fields in the Live-metrics grid (mk17)

**Files:**
- Modify: `bullion-live-map/bullion_mk17.html` — metrics grid markup, `updateMetrics()`, `METRIC_CELL_FIELD`, `LIVE_FIELD_LABEL`, `LIVE_OVERRIDABLE`, and the simulated baseline object in `buildBaseState`.

**Interfaces:**
- Consumes: existing `updateMetrics()`, `renderMetricProvenance()` (auto-renders any `p-<suffix>` whose suffix is a `METRIC_CELL_FIELD` key), `applyTransmission(state)` returning `s` (already copies every live field into `s` via `buildBaseState`).
- Produces: 13 new metric cells (`m-<field>`/`p-<field>`) that populate from live data with a provenance sub-line and amber-dot staleness, matching the existing 9.

- [ ] **Step 1: Add the 13 metric cells to the grid**

In `bullion_mk17.html`, inside `<div class="metrics-grid">` (after the WTI Oil cell), add:

```html
        <div class="metric-cell"><div class="metric-label">NFCI</div><div class="metric-val" id="m-nfci">&mdash;</div><div class="metric-sub">Fin. conditions</div><div class="prov-sub" id="p-nfci"></div></div>
        <div class="metric-cell"><div class="metric-label">HY OAS</div><div class="metric-val" id="m-hy_oas">&mdash;</div><div class="metric-sub">High-yield spread %</div><div class="prov-sub" id="p-hy_oas"></div></div>
        <div class="metric-cell"><div class="metric-label">IG OAS</div><div class="metric-val" id="m-ig_oas">&mdash;</div><div class="metric-sub">Inv-grade spread %</div><div class="prov-sub" id="p-ig_oas"></div></div>
        <div class="metric-cell"><div class="metric-label">SOFR</div><div class="metric-val" id="m-sofr">&mdash;</div><div class="metric-sub">Repo rate %</div><div class="prov-sub" id="p-sofr"></div></div>
        <div class="metric-cell"><div class="metric-label">RRP</div><div class="metric-val" id="m-rrp">&mdash;</div><div class="metric-sub">O/N reverse repo $bn</div><div class="prov-sub" id="p-rrp"></div></div>
        <div class="metric-cell"><div class="metric-label">3M Bill</div><div class="metric-val" id="m-tbill_3m">&mdash;</div><div class="metric-sub">Secondary %</div><div class="prov-sub" id="p-tbill_3m"></div></div>
        <div class="metric-cell"><div class="metric-label">30Y Mortgage</div><div class="metric-val" id="m-mortgage_30y">&mdash;</div><div class="metric-sub">Freddie PMMS %</div><div class="prov-sub" id="p-mortgage_30y"></div></div>
        <div class="metric-cell"><div class="metric-label">M2</div><div class="metric-val" id="m-m2">&mdash;</div><div class="metric-sub">Money supply $bn</div><div class="prov-sub" id="p-m2"></div></div>
        <div class="metric-cell"><div class="metric-label">Fed B/S</div><div class="metric-val" id="m-fed_bs">&mdash;</div><div class="metric-sub">Total assets $bn</div><div class="prov-sub" id="p-fed_bs"></div></div>
        <div class="metric-cell"><div class="metric-label">Tech (XLK)</div><div class="metric-val" id="m-xlk">&mdash;</div><div class="metric-sub">Sector ETF $</div><div class="prov-sub" id="p-xlk"></div></div>
        <div class="metric-cell"><div class="metric-label">Financials (XLF)</div><div class="metric-val" id="m-xlf">&mdash;</div><div class="metric-sub">Sector ETF $</div><div class="prov-sub" id="p-xlf"></div></div>
        <div class="metric-cell"><div class="metric-label">Energy (XLE)</div><div class="metric-val" id="m-xle">&mdash;</div><div class="metric-sub">Sector ETF $</div><div class="prov-sub" id="p-xle"></div></div>
        <div class="metric-cell"><div class="metric-label">Staples (XLP)</div><div class="metric-val" id="m-xlp">&mdash;</div><div class="metric-sub">Sector ETF $</div><div class="prov-sub" id="p-xlp"></div></div>
```

- [ ] **Step 2: Register the cells in METRIC_CELL_FIELD**

Extend `METRIC_CELL_FIELD` so provenance sub-lines auto-render (cell-suffix → data.json field). The suffix equals the field name for all Mk17 cells:

```javascript
const METRIC_CELL_FIELD = {
  'us2y': 'us2y', 'us10y': 'us10y', 'vix': 'vix', 'spx': 'spx',
  'cpi': 'cpi_yoy', 'gold': 'gold_px', 'dxy': 'dxy', 'wti': 'wti_px',
  // Mk17
  'nfci':'nfci', 'hy_oas':'hy_oas', 'ig_oas':'ig_oas', 'sofr':'sofr',
  'rrp':'rrp', 'tbill_3m':'tbill_3m', 'mortgage_30y':'mortgage_30y',
  'm2':'m2', 'fed_bs':'fed_bs', 'xlk':'xlk', 'xlf':'xlf', 'xle':'xle', 'xlp':'xlp',
};
```

- [ ] **Step 3: Extend LIVE_FIELD_LABEL and LIVE_OVERRIDABLE**

Replace `LIVE_FIELD_LABEL` with:

```javascript
const LIVE_FIELD_LABEL = { us2y:'US2Y', us10y:'US10Y', vix:'VIX', cpi_yoy:'Core CPI', wti_px:'WTI Oil', ffr:'Fed Funds Rate', nfp_mom:'NFP', gold_px:'Gold', dxy:'Dollar (DXY)', spx:'S&P 500', nfci:'NFCI', hy_oas:'HY OAS', ig_oas:'IG OAS', sofr:'SOFR', rrp:'RRP', tbill_3m:'3M Bill', mortgage_30y:'30Y Mortgage', m2:'M2', fed_bs:'Fed B/S', xlk:'Tech (XLK)', xlf:'Financials (XLF)', xle:'Energy (XLE)', xlp:'Staples (XLP)' };
```

Replace `LIVE_OVERRIDABLE` with (adds the fields that participate as calibrated drivers/targets so live values override the slider baseline):

```javascript
const LIVE_OVERRIDABLE = ['us2y', 'us10y', 'vix', 'cpi_yoy', 'wti_px', 'nfp_mom', 'gold_px', 'dxy', 'spx', 'nfci', 'hy_oas', 'ig_oas', 'sofr', 'rrp', 'tbill_3m', 'mortgage_30y', 'm2', 'fed_bs', 'xlk', 'xlf', 'xle', 'xlp'];
```

- [ ] **Step 4: Add simulated baseline defaults + render the cells in updateMetrics**

In `buildBaseState`, the simulated baseline object (the one that sets `us2y:4.42, us10y:4.28, …`) must gain defaults for the new fields so the grid is populated when Live Data is off. Add to that object literal:

```javascript
    nfci:-0.35, hy_oas:3.20, ig_oas:0.90, sofr:5.30, rrp:450, tbill_3m:5.20,
    mortgage_30y:6.80, m2:20900, fed_bs:7200, xlk:210, xlf:42, xle:92, xlp:78,
```

At the end of `updateMetrics()` (just before the `state-alert` block), add a DRY loop that formats each new cell, showing `—` when a value is absent:

```javascript
  // Mk17 live cells. `s` carries every live/baseline field (see buildBaseState).
  const MK17_FMT = {
    nfci:        v => (v>=0?'+':'') + (+v).toFixed(2),
    hy_oas:      v => (+v).toFixed(2)+'%',
    ig_oas:      v => (+v).toFixed(2)+'%',
    sofr:        v => (+v).toFixed(2)+'%',
    rrp:         v => '$'+Math.round(+v).toLocaleString()+'bn',
    tbill_3m:    v => (+v).toFixed(2)+'%',
    mortgage_30y:v => (+v).toFixed(2)+'%',
    m2:          v => '$'+Math.round(+v).toLocaleString()+'bn',
    fed_bs:      v => '$'+Math.round(+v).toLocaleString()+'bn',
    xlk: v=>'$'+(+v).toFixed(2), xlf: v=>'$'+(+v).toFixed(2),
    xle: v=>'$'+(+v).toFixed(2), xlp: v=>'$'+(+v).toFixed(2),
  };
  for (const [field, fmt] of Object.entries(MK17_FMT)) {
    const el = document.getElementById('m-' + field);
    if (el) el.textContent = (typeof s[field] === 'number') ? fmt(s[field]) : '—';
  }
```

- [ ] **Step 5: Verify in a headless probe**

Run a headless-Chrome render of `bullion_mk17.html` (inject the probe before the **last** `</body>`; never call `openAuditLog()`). Confirm via console log:
- `document.querySelectorAll('.metrics-grid .metric-cell').length === 22`
- `m-nfci`, `m-xlk`, `m-hy_oas` textContent are non-empty and not `—` when live data is present.
- 0 console errors.

If headless is unavailable, verify in Chrome via MCP instead (Task 8 does a full pass regardless).

- [ ] **Step 6: Commit**

```bash
cd bullion-live-map
git add bullion_mk17.html
git commit -m "Mk17: surface 13 new fields in the Live-metrics grid"
```

---

### Task 6: Node detail-panel live readouts (incl. NFCI on the vix node)

**Files:**
- Modify: `bullion-live-map/bullion_mk17.html` — add `NODE_LIVE_FIELD` map + a live-readout line rendered inside `openDetail(d)`, plus a small CSS rule.

**Interfaces:**
- Consumes: `openDetail(d)` (`d.id` is the node id), `applyTransmission(state)`, `LIVE_FIELD_LABEL`, the `MK17_FMT` formatters from Task 5 (promote them to a module-level const so both call sites share them — see Step 1).
- Produces: a "Live reading" line in the detail panel for every node bound to one or more live fields.

- [ ] **Step 1: Promote MK17_FMT to module scope**

Move the `MK17_FMT` object literal from inside `updateMetrics()` (Task 5 Step 4) to a top-level `const MK17_FMT = { … };` declared just above `updateMetrics`, and add formatters for the pre-existing driver fields so detail lines can render them too:

```javascript
const MK17_FMT = {
  us2y:v=>(+v).toFixed(2)+'%', us10y:v=>(+v).toFixed(2)+'%', vix:v=>(+v).toFixed(1),
  spx:v=>'$'+Math.round(+v).toLocaleString(), cpi_yoy:v=>(+v).toFixed(1)+'%',
  gold_px:v=>'$'+Math.round(+v).toLocaleString(), dxy:v=>(+v).toFixed(1),
  wti_px:v=>'$'+(+v).toFixed(1), ffr:v=>(+v).toFixed(2)+'%', nfp_mom:v=>Math.round(+v)+'k',
  nfci:v=>(v>=0?'+':'')+(+v).toFixed(2), hy_oas:v=>(+v).toFixed(2)+'%',
  ig_oas:v=>(+v).toFixed(2)+'%', sofr:v=>(+v).toFixed(2)+'%',
  rrp:v=>'$'+Math.round(+v).toLocaleString()+'bn', tbill_3m:v=>(+v).toFixed(2)+'%',
  mortgage_30y:v=>(+v).toFixed(2)+'%', m2:v=>'$'+Math.round(+v).toLocaleString()+'bn',
  fed_bs:v=>'$'+Math.round(+v).toLocaleString()+'bn',
  xlk:v=>'$'+(+v).toFixed(2), xlf:v=>'$'+(+v).toFixed(2),
  xle:v=>'$'+(+v).toFixed(2), xlp:v=>'$'+(+v).toFixed(2),
};
```

Then in `updateMetrics()` delete the now-duplicate local `MK17_FMT` declaration, keeping the `for` loop that consumes it.

- [ ] **Step 2: Add the node→field binding map**

Declare next to `MK17_FMT` (a node may bind multiple fields; NFCI rides the `vix` node as a secondary reading):

```javascript
// Node id -> live data.json field(s) shown in the detail panel. NFCI attaches to
// the vix node (both are market-stress readings) — it does NOT add a graph edge.
const NODE_LIVE_FIELD = {
  vix: ['vix', 'nfci'], credit: ['hy_oas', 'ig_oas'], repo: ['sofr', 'rrp'],
  mortgage: ['mortgage_30y'], m2: ['m2'], fed: ['fed_bs'], tbills: ['tbill_3m'],
  tech: ['xlk'], fins: ['xlf'], energy: ['xle'], defn: ['xlp'],
  yield: ['us10y', 'us2y'], equit: ['spx'], gold: ['gold_px'], usd: ['dxy'], oil: ['wti_px'],
};
```

- [ ] **Step 3: Add the CSS rule**

Near the `.prov-sub` rule, add:

```css
  .detail-live { margin:8px 0 2px; font-size:12px; color:var(--text-dim); }
  .detail-live b { color:var(--text); font-weight:600; }
```

- [ ] **Step 4: Render the live line in openDetail**

In `openDetail(d)`, after the `buildRelationships(d);` call, insert:

```javascript
  // Live reading(s) for this node, if any (Mk17). Uses the current transmission
  // state so it tracks the active scenario/live data, and shows nothing when the
  // node has no bound field or the value is absent.
  const liveHost = document.getElementById('detail-live');
  if (liveHost) {
    const fields = NODE_LIVE_FIELD[d.id] || [];
    const s = applyTransmission(state);
    const parts = fields
      .filter(f => typeof s[f] === 'number' && MK17_FMT[f])
      .map(f => `${LIVE_FIELD_LABEL[f] || f}: <b>${MK17_FMT[f](s[f])}</b>`);
    liveHost.innerHTML = parts.length ? ('Live reading &mdash; ' + parts.join(' &nbsp;·&nbsp; ')) : '';
  }
```

Add the host element once in the detail-panel markup, immediately after the `<ul id="detail-bullets">` element:

```html
      <div class="detail-live" id="detail-live"></div>
```

- [ ] **Step 5: Verify in a headless probe**

Render `bullion_mk17.html` headless; in the probe call `openDetail(nodeById('vix'))` (NOT the audit modal) and log `document.getElementById('detail-live').textContent`. Expected: contains both `VIX:` and `NFCI:`. Repeat for `openDetail(nodeById('credit'))` → contains `HY OAS:` and `IG OAS:`. 0 console errors.

- [ ] **Step 6: Commit**

```bash
cd bullion-live-map
git add bullion_mk17.html
git commit -m "Mk17: live readouts in node detail panel (NFCI on vix node)"
```

---

### Task 7: Promote calibrated links into the client elasticity + backtest maps

**Files:**
- Modify: `bullion-live-map/bullion_mk17.html` — `ELASTICITY`, `NODE_ELASTICITY`, `BACKTEST_MAP`.

**Interfaces:**
- Consumes: the MEASURED/DIRECTIONAL verdicts + fitted `slope`/`t`/`r` from Task 3's `calibration_report.txt`; existing `CONF.MEASURED`/`CONF.DIRECTIONAL`, `NE(...)` helper, integrity guards (`demote`, the NODE_ELASTICITY↔LINKS sign cross-check), `backtestModel()`.
- Produces: new elasticity cells whose confidence tier matches the fit, so the Audit-Log backtest grades the new links and scenario recolor reflects them.

- [ ] **Step 1: Add MEASURED cells with fitted values**

For each Mk17 cell that Task 3 reported **MEASURED**, add an `ELASTICITY[driver][target]` entry using the fitted slope, with a `src` that cites the fit (mirror the existing `dxy.us10y` MEASURED entry's wording — quote the actual `n`, `slope`, `r`, `t` from the report). Example shape (fill in real numbers from the report; do not invent them):

```javascript
  // inside ELASTICITY.spx (add the row object if spx is not yet a driver key)
    xlk: { v: <fitted_slope>, conf: CONF.MEASURED, src: 'Tech sector ETF beta to the S&P. Fitted to data.json (train split): <n> daily first-difference days, XLK % change on SPX % change, slope <slope>, r <r>, t <t>. Out-of-sample accuracy in the Audit Log backtest. 1-year contemporaneous fit, not a structural beta.' },
```

- [ ] **Step 2: Add DIRECTIONAL cells for the rest**

For each Mk17 cell Task 3 reported **DIRECTIONAL**, add the entry with the hand value and `conf: CONF.DIRECTIONAL`, and a `src` stating the sign is reliable but the magnitude is hand-set (mirror existing DIRECTIONAL entries). Do NOT claim a fitted beta for these.

- [ ] **Step 3: Wire NODE_ELASTICITY for the affected nodes**

For sector/credit/mortgage/repo/tbills nodes that now have a driver relationship, add matching `NODE_ELASTICITY[driver]` entries via the `NE(coef, conf, src)` helper, keyed by the NODE_MAP label, so scenario recolor colours them. Keep signs consistent with the `LINKS` graph — the built-in cross-check will flag a mismatch (see Step 5).

- [ ] **Step 4: Register MEASURED cells in BACKTEST_MAP**

For each MEASURED cell, add a `BACKTEST_MAP[driverField] = { cells: { <targetField>: {...} } }` entry following the existing shape (the existing `us10y`/`dxy` entries are the template) so `backtestModel()` grades the new link out-of-sample.

- [ ] **Step 5: Run the in-page integrity guards headless**

Render `bullion_mk17.html` headless and log the integrity results the boot sequence already computes (the `demote(...)` provenance guard and the NODE_ELASTICITY↔LINKS sign cross-check). Expected: no `sign:0` contradictions, no "colours nothing" warnings, 0 console errors. Fix any flagged cell (usually a sign disagreement) before continuing.

- [ ] **Step 6: Commit**

```bash
cd bullion-live-map
git add bullion_mk17.html
git commit -m "Mk17: promote calibrated links into elasticity + backtest maps"
```

---

### Task 8: Full verification + release

**Files:**
- Modify (verify only): `bullion-live-map/bullion_mk17.html`, `index.html`

**Interfaces:**
- Consumes: everything above.
- Produces: a pushed, live-on-Pages Mk17 that is the current shared map.

- [ ] **Step 1: Run the Python test suites**

Run: `cd bullion-live-map && python3 -m unittest test_fetch_bullion_data test_calibrate -v`
Expected: all PASS.

- [ ] **Step 2: Full Chrome-MCP verification of mk17**

Open `bullion_mk17.html` in Chrome (MCP). Confirm:
- 0 console errors on load.
- Live-metrics grid shows 22 cells, new ones populated from live data with provenance sub-lines.
- Click a `credit`, `tech`, and `vix` node → detail panel shows the "Live reading" line (vix shows VIX + NFCI).
- Open the Audit Log → Model-accuracy panel still renders and now grades the new MEASURED links (verify via the `BACKTEST_MAP`/`backtestModel()` predicate, per the headless idiom — do not rely on the animated modal in headless).
- Switch to the **▦ Overview** tab → still 7 columns / 39 cards / 9 bold hubs (node count unchanged).
- Narrow the viewport → horizontal scroll inside the grid/board, no page-body overflow.

- [ ] **Step 3: Confirm prior versions still frozen**

Run: `cd bullion-live-map && shasum -a 256 bullion_mk16.html bullion_mk15.html`
Expected: identical to Task 4 Step 1.

- [ ] **Step 4: Push and confirm live**

```bash
cd /path/to/claudekit
GIT_TERMINAL_PROMPT=0 git push origin main
```
Then confirm the pushed content:
```bash
git show origin/main:bullion-live-map/index.html | grep -o "bullion_mk17.html" | head -1
```
Expected: `bullion_mk17.html`. Note: the Pages CDN caches ~5 min, so a stale live URL immediately after push is normal — trust `git show origin/main`.

- [ ] **Step 5: Final commit if any verification fixes were made**

```bash
cd bullion-live-map
git add -A && git commit -m "Mk17: verification fixes" || echo "nothing to commit"
```

---

## Self-Review

**Spec coverage:**
- 13 new fields (9 FRED + 4 Yahoo) → Task 1. ✓
- Weekly cadence bucket (~10d) with M2→monthly, RRP→daily correction → Task 1 (`CADENCE_TOLERANCE_DAYS`, tests). ✓
- FIELD_META for every field / provenance guarantee → Task 1 Step 5 + coverage test. ✓
- SOURCE_NOTE update → Task 1 Step 6. ✓
- Regenerate data.json → Task 2. ✓
- Calibrate all fittable now (MEASURED else DIRECTIONAL) → Tasks 3 + 7. ✓
- NFCI on vix node, no new node, board unchanged → Task 6 (`NODE_LIVE_FIELD.vix`) + Task 8 board check. ✓
- Cut mk17 via release.sh, freeze mk15/mk16 → Task 4 + Task 8 Step 3. ✓
- Metric cells + provenance sub → Task 5. ✓
- Live bindings (LIVE_OVERRIDABLE + auto snapshot) → Task 5 Step 3. ✓
- Node detail readouts → Task 6. ✓
- Verification idioms (probe before last `</body>`, never openAuditLog, backtest via predicate) → Tasks 5/6/7/8. ✓
- Push + confirm live via git show → Task 8. ✓
- Non-goals (no MCP, FOMC simulated, Mk Ultra untouched) → Global Constraints. ✓

**Placeholder scan:** The only intentional fill-in-from-output values are Task 7's fitted `slope`/`t`/`r`/`n` — these MUST come from Task 3's real `calibration_report.txt`, and the plan explicitly says "do not invent them." That is a data-dependency, not a placeholder; every other step carries complete code.

**Type consistency:** `MK17_FMT` is declared local in Task 5 then promoted to module scope in Task 6 Step 1 (with the duplicate removed) — call sites in both `updateMetrics` and `openDetail` reference the same const. `METRIC_CELL_FIELD` suffixes equal field names, matching the `m-<field>`/`p-<field>` ids in Task 5 Step 1. `NODE_LIVE_FIELD` keys are real node ids (verified against the 39-node roster). `CELLS` tuples match `calibrate.py`'s `(driver, key, field, kind, hand)` shape.
