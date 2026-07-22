# Bullion Mk12 — Calibrate & Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fit the fittable `ELASTICITY` coefficients against the accrued `data.json` history, adopt the good fits with sourced provenance, and add a live in-page backtest panel that grades the model out-of-sample — plus three folded-in fixes.

**Architecture:** An offline stdlib Python calibration script (`calibrate.py`) fits driver→field cells on first-differences over a training window and emits a report; fits that pass a rubric are hand-adopted into the HTML with sourced comments. A new client-side backtest function replays the held-out tail of the loaded history through the model and renders a per-field accuracy table inside the existing Audit Log. Everything else in the single HTML file is untouched except three scoped fixes.

**Tech Stack:** Python 3.9 stdlib only (hand-rolled OLS — no numpy/scipy/pandas; `statistics.linear_regression` is 3.10+). Vanilla ES for the in-page backtest. `unittest` for Python tests; headless Chrome (`--dump-dom` / console assertions) for page verification — the project has no JS test runner.

## Global Constraints

- **Single openable file, no build step.** `bullion_mk11_constellation.html` must still open from `file://`. `calibrate.py` is offline and is NOT wired into the daily `run_daily_update.sh` / GitHub Actions pipeline.
- **Preserve the public URL.** Keep the filename `bullion_mk11_constellation.html` (it is the shared GitHub Pages link). Version bumps are cosmetic (H1 / title text only).
- **Python stdlib only, Python 3.9.** Reuse the hand-rolled OLS in `audit_fit_elasticities.py`. No third-party imports.
- **First differences for every fit.** Levels regressions on persistent series are spurious (the Mk11 `ffr→vix` failure). Fit consecutive-day changes only.
- **Train/test split rule, identical on both sides.** `dates = sorted(history keys)`, `cutIdx = floor(0.8 * len(dates))`. `calibrate.py` trains on `dates[:cutIdx]`; the in-page backtest scores on `dates[cutIdx:]`. Same rule, same `data.json` ⇒ same boundary.
- **No coefficient silently changed.** Every adopted fit is edited into source by hand with a comment naming the script, n, regressor span, slope, r, and t. Cells that fail the rubric keep their hand value; the fit is added only as a caveat.
- **Adoption rubric:** promote a cell to `CONF.MEASURED` only if fitted sign == hand sign AND `|t| > 2` AND the regressor actually varied over the window. Otherwise keep the value at `CONF.DIRECTIONAL` (or its current tier) and append the fit result to `src` as a caveat.
- **`validateProvenance()` must stay green** at load after every task (no new sign conflicts between `ELASTICITY`, `NODE_ELASTICITY`, `LINKS`).
- **Out of scope (do not touch):** `NODE_ELASTICITY` magnitudes (no time series), `cpi_yoy`/`nfp_mom`-driven cells (data-starved), feedback loops / lags / multi-pass dynamics, new nodes or layers.

---

## File Structure

- `bullion-live-map/calibrate.py` — **Create.** Offline calibration harness: load history, fit the 14 fittable cells on the training split, apply the rubric, print + write a report.
- `bullion-live-map/test_calibrate.py` — **Create.** `unittest` for the pure functions (OLS, first-diff, split, target extraction, verdict).
- `bullion-live-map/calibration_report.txt` — **Create (generated).** Committed output of `calibrate.py`, the provenance trail for the adopted numbers.
- `bullion-live-map/bullion_mk11_constellation.html` — **Modify.** Adopt fits (Task 3); add backtest engine (Task 4) + Audit Log panel (Task 5); fix `runManual` (Task 6); relative threshold (Task 7); weak scenarios (Task 8); version bump (Task 9).

The 14 fittable cells (driver field → target cell, and how the target is differenced):

```
ffr    -> us2y      (level Δ)
ffr    -> us10y     (level Δ)
ffr    -> spx_pct   (pct Δ of spx)
ffr    -> gold_pct  (pct Δ of gold_px)
ffr    -> dxy_add   (level Δ of dxy)
vix    -> spx_pct   (pct Δ of spx)
vix    -> us10y     (level Δ)
vix    -> gold_pct  (pct Δ of gold_px)
vix    -> dxy_add   (level Δ of dxy)
dxy    -> gold_pct  (pct Δ of gold_px)
dxy    -> wti_pct   (pct Δ of wti_px)
dxy    -> spx_pct   (pct Δ of spx)
wti_px -> spx_pct   (pct Δ of spx)   [already fitted in Mk11 — re-fit for consistency]
wti_px -> us10y     (level Δ)
```

Driver field names: `ffr, vix, dxy, wti_px`. Target field names for differencing: `us2y, us10y` (level), `spx, gold_px, wti_px` (pct), `dxy` (level, for `dxy_add`).

---

### Task 1: Calibration pure core + tests

Build the testable, side-effect-free functions `calibrate.py` needs, TDD-first. Port `ols` and `first_diff` from `audit_fit_elasticities.py` unchanged; add `train_split`, `target_series`, and `verdict`.

**Files:**
- Create: `bullion-live-map/calibrate.py`
- Test: `bullion-live-map/test_calibrate.py`

**Interfaces:**
- Produces (used by Task 2):
  - `ols(xs, ys) -> dict` with keys `n, slope, intercept, r, r2, t, x_span, se_slope` (or `error`). (Verbatim from `audit_fit_elasticities.py`.)
  - `first_diff(dates, xs, ys) -> (dxs, dys)`. (Verbatim.)
  - `train_split(dates) -> (train_dates_set)` where `cut = floor(0.8*len(sorted(dates)))`, train = `sorted(dates)[:cut]`.
  - `target_series(hist, dates, field, kind) -> (dates2, driver_or_target_values)` — for `kind='level'` returns the field values; for `kind='pct'` returns values and the caller differences as pct. (See Step 3.)
  - `verdict(hand_sign, fit) -> ('measured'|'directional', reason_str)` applying the rubric.

- [ ] **Step 1: Write failing tests for `train_split` and `verdict`**

```python
# test_calibrate.py
import unittest
import calibrate as c

class TestSplit(unittest.TestCase):
    def test_split_80_20(self):
        dates = [f'2025-01-{d:02d}' for d in range(1, 11)]  # 10 dates
        train = c.train_split(dates)
        self.assertEqual(len(train), 8)                 # floor(0.8*10)=8
        self.assertIn('2025-01-08', train)
        self.assertNotIn('2025-01-09', train)           # held out
    def test_split_is_prefix(self):
        dates = ['2025-01-03','2025-01-01','2025-01-02','2025-01-05','2025-01-04']
        train = c.train_split(dates)                    # must sort first
        self.assertEqual(train, {'2025-01-01','2025-01-02','2025-01-03','2025-01-04'})

class TestVerdict(unittest.TestCase):
    def test_promote_when_sign_matches_and_significant(self):
        fit = {'slope': -0.9, 't': -5.3, 'x_span': 0.7}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'measured')
    def test_keep_when_sign_flips(self):
        fit = {'slope': +0.4, 't': 5.0, 'x_span': 0.7}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'directional')
    def test_keep_when_insignificant(self):
        fit = {'slope': -0.9, 't': 0.4, 'x_span': 0.7}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'directional')
    def test_keep_when_regressor_flat(self):
        fit = {'slope': -0.9, 't': 5.0, 'x_span': 0.0}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'directional')

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `cd bullion-live-map && python3 -m unittest test_calibrate -v`
Expected: FAIL — `AttributeError: module 'calibrate' has no attribute 'train_split'`.

- [ ] **Step 3: Implement `calibrate.py` pure core**

Port `ols` and `first_diff` verbatim from `audit_fit_elasticities.py`, then add:

```python
import json, math

# ... paste ols(xs, ys) and first_diff(dates, xs, ys) verbatim from
#     audit_fit_elasticities.py (do not modify them) ...

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
    if abs(fit.get('t', 0)) <= 2:
        return 'directional', f"|t|={abs(fit['t']):.1f} not significant"
    return 'measured', f"sign matches, |t|={abs(fit['t']):.1f}, span={fit['x_span']:.3g}"
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `cd bullion-live-map && python3 -m unittest test_calibrate -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add bullion-live-map/calibrate.py bullion-live-map/test_calibrate.py
git commit -m "Mk12: calibration pure core (split, target-series, verdict) + tests"
```

---

### Task 2: Calibration report generator

Wire the 14 cells, load `data.json`, fit each on the training split (first differences; pct targets fit % change, level/add targets fit level change), classify with `verdict`, and print + write `calibration_report.txt`.

**Files:**
- Modify: `bullion-live-map/calibrate.py`
- Create (generated): `bullion-live-map/calibration_report.txt`

**Interfaces:**
- Consumes: `ols, first_diff, train_split, target_series, verdict` (Task 1).
- Produces: a `main()` that, run as `python3 calibrate.py [data.json]`, prints one block per cell and writes the same to `calibration_report.txt`. Each block reports: driver, target, n (train days), regressor span, fitted slope, hand value, r, t, and the verdict + reason.

- [ ] **Step 1: Add the cell table and per-cell fit**

```python
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
```

- [ ] **Step 2: Add `main()` that fits all cells, classifies, and writes the report**

```python
def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    doc = json.load(open(path))
    hist = doc['history'] if isinstance(doc, dict) and 'history' in doc else doc
    train = train_split(list(hist.keys()))
    lines = [f"Bullion Mk12 calibration — train split {len(train)} days "
             f"(first 80% of {len(hist)}); first-difference OLS.\n"]
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
    report = "\n".join(lines) + "\n"
    print(report)
    open('calibration_report.txt', 'w').write(report)

if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Run and eyeball the report**

Run: `cd bullion-live-map && python3 calibrate.py`
Expected: 14 lines, each ending in `MEASURED (...)` or `DIRECTIONAL (...)`, and `calibration_report.txt` written. Confirm `wti_px-> spx_pct` reproduces roughly the Mk11 fit (slope ≈ −0.0009, negative sign) as a sanity anchor. It is an acceptable, honest outcome for most cells to come back DIRECTIONAL.

- [ ] **Step 4: Commit**

```bash
git add bullion-live-map/calibrate.py bullion-live-map/calibration_report.txt
git commit -m "Mk12: calibration report generator over the 14 fittable cells"
```

---

### Task 3: Adopt fits into the ELASTICITY table

Apply the rubric to the report from Task 2. This task is **data-driven**: the exact edits depend on which cells passed. Do not invent numbers — use the report.

**Files:**
- Modify: `bullion-live-map/bullion_mk11_constellation.html` (the `ELASTICITY` object, lines ~2268–2307)

**Interfaces:**
- Consumes: `calibration_report.txt` (Task 2).

- [ ] **Step 1: For each cell the report marks MEASURED**, set that cell's `conf:` to `CONF.MEASURED`, replace `v:` with the fitted slope rounded to the cell's existing precision, and rewrite `src:` to name the fit, e.g.:

```
spx_pct: { v:-0.0088, conf:CONF.MEASURED, src:'Fitted to data.json (calibrate.py, train split): N daily first-difference days, <target> change on <driver> change, slope <slope>, r <r>, t <t>. Out-of-sample accuracy in the Audit Log backtest. 1-year contemporaneous fit, not a structural beta.' },
```

- [ ] **Step 2: For each cell the report marks DIRECTIONAL**, leave `v:` and `conf:` unchanged; append one sentence to `src:` recording the fit and why it was not adopted, e.g. `... Fit check (calibrate.py): slope <slope>, t <t> — <reason>, so the hand magnitude is kept.`

- [ ] **Step 3: Verify `validateProvenance()` stays green and no sign flipped**

Run (headless dump of the load-time provenance state):
```bash
SP=/tmp; CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cp bullion-live-map/bullion_mk11_constellation.html "$SP/pv.html"
printf '\n<script>window.addEventListener("load",()=>setTimeout(()=>{console.log("PROV "+JSON.stringify({conflicts:PROV_CONFLICTS.length,demotions:PROV_DEMOTIONS.length}));},1200));</script>\n' >> "$SP/pv.html"
"$CHROME" --headless=new --disable-gpu --virtual-time-budget=3000 --enable-logging=stderr --v=0 "file://$SP/pv.html" 2>&1 | grep -oE 'PROV .*' | head -1
```
Expected: `PROV {"conflicts":0,"demotions":0}`. If a fitted sign disagreed with `LINKS`, that is a conflict to resolve explicitly (keep the hand sign, log it) — never adopt a sign flip blindly.

- [ ] **Step 4: Commit**

```bash
git add bullion-live-map/bullion_mk11_constellation.html
git commit -m "Mk12: adopt calibrated coefficients (measured) / annotate the rest"
```

---

### Task 4: In-page backtest engine

Add a client-side function that replays the held-out tail of the loaded history through the model's own elasticities and returns per-target-field accuracy. Per **field** (not per cell): predicted Δfield = Σ over fittable drivers present both days of `ELASTICITY[driver][cellKey].v × Δdriver`.

**Files:**
- Modify: `bullion-live-map/bullion_mk11_constellation.html` (add near `openAuditLog`, module scope)

**Interfaces:**
- Consumes: `window.BULLION_LIVE_HISTORY`, `ELASTICITY`.
- Produces: `backtestModel() -> { split, fields: [ { field, label, n, hitRate, r2 } ], asOf } | null`.

- [ ] **Step 1: Add the field/driver map and the backtest function**

```javascript
// ── Mk12 backtest ────────────────────────────────────────────────────────
// Per target field, predicted daily change = sum over fittable drivers (present
// both days) of ELASTICITY[driver][cell].v * driver change. Compared to the
// realised change on the held-out tail (last 20% of loaded history — same split
// as calibrate.py). CONTEMPORANEOUS same-day test: measures co-movement, NOT
// forecasting. Node colours are not in scope here (their targets have no series).
// Driver→cell map per target field, built explicitly from the 14 fittable cells:
const BACKTEST_MAP = {
  us2y:    { kind:'level', cells:{ ffr:'us2y' } },
  us10y:   { kind:'level', cells:{ ffr:'us10y', vix:'us10y', wti_px:'us10y' } },
  spx:     { kind:'pct',   cells:{ ffr:'spx_pct', vix:'spx_pct', dxy:'spx_pct', wti_px:'spx_pct' } },
  gold_px: { kind:'pct',   cells:{ ffr:'gold_pct', vix:'gold_pct', dxy:'gold_pct' } },
  wti_px:  { kind:'pct',   cells:{ dxy:'wti_pct' } },
  dxy:     { kind:'level', cells:{ ffr:'dxy_add', vix:'dxy_add' } },
};
const BACKTEST_LABEL = { us2y:'2Y yield', us10y:'10Y yield', spx:'S&P 500',
                         gold_px:'Gold', wti_px:'WTI oil', dxy:'Dollar (DXY)' };
const DRIVER_FIELD = { ffr:'ffr', vix:'vix', dxy:'dxy', wti_px:'wti_px' };

function backtestModel() {
  const H = window.BULLION_LIVE_HISTORY;
  if (!H) return null;
  const dates = Object.keys(H).sort();
  const cut = Math.floor(0.8 * dates.length);
  const testDates = dates.slice(cut);
  const fields = [];
  Object.entries(BACKTEST_MAP).forEach(([field, spec]) => {
    let n = 0, hits = 0, ssRes = 0, ssTot = 0, sy = 0, sy2 = 0;
    const preds = [], acts = [];
    for (let i = 1; i < testDates.length; i++) {
      const d0 = testDates[i-1], d1 = testDates[i];
      const r0 = H[d0], r1 = H[d1];
      if (!(field in r0) || !(field in r1)) continue;
      let pred = 0, haveDriver = false;
      Object.entries(spec.cells).forEach(([drv, cellKey]) => {
        const f = DRIVER_FIELD[drv];
        if (f in r0 && f in r1 && ELASTICITY[drv] && ELASTICITY[drv][cellKey]) {
          pred += ELASTICITY[drv][cellKey].v * (r1[f] - r0[f]);
          haveDriver = true;
        }
      });
      if (!haveDriver) continue;
      const act = spec.kind === 'pct'
        ? (r0[field] ? (r1[field] - r0[field]) / r0[field] : 0)
        : (r1[field] - r0[field]);
      preds.push(pred); acts.push(act); n++;
      if ((pred > 0 && act > 0) || (pred < 0 && act < 0) || (pred === 0 && act === 0)) hits++;
      sy += act; sy2 += act * act;
    }
    if (n >= 3) {
      const my = sy / n;
      ssTot = sy2 - n * my * my;
      for (let j = 0; j < preds.length; j++) ssRes += (acts[j] - preds[j]) ** 2;
      const r2 = ssTot > 0 ? Math.max(0, 1 - ssRes / ssTot) : 0;
      fields.push({ field, label: BACKTEST_LABEL[field], n, hitRate: hits / n, r2 });
    }
  });
  return { split: cut, testLen: testDates.length, fields };
}
```

- [ ] **Step 2: Verify it computes sane numbers on the loaded history**

```bash
SP=/tmp; CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cp bullion-live-map/bullion_mk11_constellation.html bullion-live-map/data.json "$SP/" 2>/dev/null; cp bullion-live-map/bullion_mk11_constellation.html "$SP/bt.html"
printf '\n<script>window.addEventListener("load",()=>setTimeout(()=>{console.log("BT "+JSON.stringify(backtestModel()));},1500));</script>\n' >> "$SP/bt.html"
"$CHROME" --headless=new --disable-gpu --virtual-time-budget=4000 --enable-logging=stderr --v=0 "file://$SP/bt.html" 2>&1 | grep -oE 'BT .*' | sed 's/, source:.*//' | head -1
```
Expected: a JSON object with `fields` array; each `hitRate` in [0,1], `r2` in [0,1], `n` > 0. `spx` should hit-rate well above 0.5 (the vix→spx link is near-identity); `us2y` should track `ffr` strongly.

- [ ] **Step 3: Commit**

```bash
git add bullion-live-map/bullion_mk11_constellation.html
git commit -m "Mk12: client-side per-field backtest engine over held-out history"
```

---

### Task 5: Audit Log "Model accuracy" panel

Render `backtestModel()` output as a table in the Audit Log, above the coefficient tables, with the three honesty caveats.

**Files:**
- Modify: `bullion-live-map/bullion_mk11_constellation.html` (`openAuditLog`, ~lines 2980–3046, and the audit CSS string ~3050–3071)

**Interfaces:**
- Consumes: `backtestModel()` (Task 4).

- [ ] **Step 1: Build the accuracy section HTML inside `openAuditLog`**, before the `bar` variable is used in the concatenation:

```javascript
const bt = backtestModel();
const btPct = x => (100 * x).toFixed(0) + '%';
const btRows = bt && bt.fields.length
  ? bt.fields.map(f =>
      '<tr><td>' + f.label + '</td><td>' + f.n + '</td><td>' + btPct(f.hitRate) +
      '</td><td>' + f.r2.toFixed(2) + '</td></tr>').join('')
  : '<tr><td colspan="4"><i>Not enough held-out history yet.</i></td></tr>';
const backtestSection =
  '<h3>Model accuracy — backtested on the held-out tail' +
  (bt ? ' (' + (bt.testLen - 1) + ' most-recent days)' : '') + '</h3>' +
  '<p class="audit-note">Each field’s predicted daily change (all fittable drivers, ' +
  'summed through the elasticity matrix) vs. what actually happened, on the last 20% of ' +
  'history the calibration never saw. <b>This is a same-day co-movement test, not a forecast</b> ' +
  '(no lag modelled). Node colours are NOT graded here — concept nodes have no time series.</p>' +
  '<table class="audit-table"><tr><th>Field</th><th>Days</th><th>Direction hit-rate</th><th>R² of change</th></tr>' +
  btRows + '</table>';
```

- [ ] **Step 2: Insert `backtestSection` into the `html` concatenation**, right after the intro `<p>` and before `bar`:

```javascript
      'A polished render makes a guess look exactly like a measured coefficient. This page exists to break that illusion.</p>' +
      backtestSection +
      bar + conflicts + demotions + superseded + scenNote +
```

- [ ] **Step 3: Verify the section renders**

Reuse the Task 4 harness but assert the audit HTML contains the header. Since the audit log opens via `window.open`, expose the built string for the test by temporarily assigning `window.__auditHtml = html;` before `w.document.write(...)` — OR verify by checking `backtestModel()` is truthy and the concatenation includes `backtestSection` via a string check:

```bash
SP=/tmp; CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; cp bullion-live-map/bullion_mk11_constellation.html "$SP/al.html"
printf '\n<script>window.addEventListener("load",()=>setTimeout(()=>{const b=backtestModel();console.log("AL "+JSON.stringify({has:!!b,fields:b?b.fields.length:0}));},1500));</script>\n' >> "$SP/al.html"
"$CHROME" --headless=new --disable-gpu --virtual-time-budget=4000 --enable-logging=stderr --v=0 "file://$SP/al.html" 2>&1 | grep -oE 'AL .*' | sed 's/, source:.*//' | head -1
```
Expected: `AL {"has":true,"fields":N}` with N ≥ 4. (Full visual check of the opened audit window is a manual confirmation.)

- [ ] **Step 4: Commit**

```bash
git add bullion-live-map/bullion_mk11_constellation.html
git commit -m "Mk12: Model-accuracy backtest panel in the Audit Log"
```

---

### Task 6: Fix the `runManual` boot-only logic bug

`runManual` (~lines 3389–3402) calls `validateProvenance()` and binds the Audit Log click listener on every slider move. Move both to run once at boot.

**Files:**
- Modify: `bullion-live-map/bullion_mk11_constellation.html`

- [ ] **Step 1: Remove the misplaced lines from `runManual`**

Delete these three lines from inside `runManual`:
```javascript
  validateProvenance();

  document.getElementById('audit-log-btn').addEventListener('click', openAuditLog);
```
(Keep the surrounding `applyTransmission(state); expandAffected();` and `updateMetrics();`.)

- [ ] **Step 2: Ensure they run exactly once at boot**

Confirm `validateProvenance()` and the `audit-log-btn` listener are bound in the boot sequence (search for another `validateProvenance()` / `audit-log-btn` binding). If the only ones were inside `runManual`, add them once at module init near the other header-control bindings (~line 1631):
```javascript
validateProvenance();
document.getElementById('audit-log-btn').addEventListener('click', openAuditLog);
```

- [ ] **Step 3: Verify listener bound once and validation still green**

```bash
SP=/tmp; CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; cp bullion-live-map/bullion_mk11_constellation.html "$SP/rm.html"
printf '\n<script>window.addEventListener("load",()=>setTimeout(()=>{let c=0;const o=openAuditLog;window.openAuditLog=function(){c++};document.getElementById("audit-log-btn").click();runManual&&runManual();runManual&&runManual();document.getElementById("audit-log-btn").click();console.log("RM "+JSON.stringify({calls:c,conflicts:PROV_CONFLICTS.length}));},1400));</script>\n' >> "$SP/rm.html"
"$CHROME" --headless=new --disable-gpu --virtual-time-budget=4000 --enable-logging=stderr --v=0 "file://$SP/rm.html" 2>&1 | grep -oE 'RM .*' | sed 's/, source:.*//' | head -1
```
Expected: `RM {"calls":2,"conflicts":0}` — one click ⇒ one handler call even after two `runManual` runs (no duplicate listeners). If listeners still stacked, `calls` would exceed 2.

- [ ] **Step 4: Commit**

```bash
git add bullion-live-map/bullion_mk11_constellation.html
git commit -m "Mk12: fix runManual re-binding Audit Log listener + re-validating every slider move"
```

---

### Task 7: Relative color/expand threshold

Replace the fixed `0.05` node cutoff with a per-scenario relative one, so a scenario always surfaces its strongest effects while trivial moves stay dark. **Recommended (my call absent your veto): floor + fraction-of-max.**

**Files:**
- Modify: `bullion-live-map/bullion_mk11_constellation.html` (`expandAffected` ~line 2955 region, and `updateGraph` recolor thresholds ~lines 3187+)

**Interfaces:**
- Produces: `nodeCutoff() -> number` used by both `expandAffected` and `updateGraph` so they never disagree.

- [ ] **Step 1: Add a shared cutoff helper**

```javascript
// A node counts as "moved" if its multiplier clears this cutoff. Relative so a
// single-driver scenario still lights its top nodes: the larger of a small floor
// and 50% of the scenario's biggest effect.
function nodeCutoff() {
  const FLOOR = 0.02, REL = 0.5;
  let mx = 0;
  Object.values(nodeMultipliers).forEach(v => { if (Math.abs(v) > mx) mx = Math.abs(v); });
  return Math.max(FLOOR, REL * mx);
}
```

- [ ] **Step 2: Use it in `expandAffected`** — replace `const CUTOFF = 0.05;` with `const CUTOFF = nodeCutoff();`.

- [ ] **Step 3: Use it in `updateGraph`** — replace the hard-coded `0.05` comparisons in the `.core` fill / `.stroke` / `.stroke-width` logic with `const cut = nodeCutoff();` and compare `m > cut` / `m < -cut` (keep the `±` symmetry). Update the code comment that referenced the 0.05 constant.

- [ ] **Step 4: Verify no scenario regresses**

```bash
SP=/tmp; CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; cp bullion-live-map/bullion_mk11_constellation.html "$SP/th.html"
printf '\n<script>window.addEventListener("load",()=>setTimeout(()=>{const o={};Object.keys(SCENARIOS).forEach(t=>{triggerShock(t);const vis=visibleNodeIds();const cut=nodeCutoff();const aff=Object.keys(NODE_MAP).filter(k=>Math.abs(nodeMultipliers[k]||0)>cut).map(k=>NODE_MAP[k]);o[t]={cut:+cut.toFixed(3),colored:aff.length,hidden:aff.filter(id=>!vis.has(id)).length};});console.log("TH "+JSON.stringify(o));},1600));</script>\n' >> "$SP/th.html"
"$CHROME" --headless=new --disable-gpu --virtual-time-budget=5000 --enable-logging=stderr --v=0 "file://$SP/th.html" 2>&1 | grep -oE 'TH .*' | sed 's/, source:.*//' | head -1
```
Expected: every scenario has `hidden:0` (no affected node off-screen) and `colored ≥ 1` (each scenario now lights at least its top node, including `cpi_rise`); no scenario colors close to all ~20 mapped nodes.

- [ ] **Step 5: Commit**

```bash
git add bullion-live-map/bullion_mk11_constellation.html
git commit -m "Mk12: per-scenario relative node cutoff (floor + fraction-of-max)"
```

---

### Task 8: Defend or relabel the two weakest scenarios

`fiscal_tightening`'s asymmetry vs. stimulus is flagged "unjustified," and `deregulation`'s sign is 2006-vintage. Resolve both honestly.

**Files:**
- Modify: `bullion-live-map/bullion_mk11_constellation.html` (`SCENARIOS`, ~lines 2685–2704)

- [ ] **Step 1: Make `fiscal_tightening` the sign-mirror of `fiscal_stimulus`** (removing the unjustified asymmetry), and update its `note` to say it is now a deliberate mirror:

```javascript
  fiscal_tightening: {
    label:'Fiscal Tightening',
    drivers:{},
    exogenous:{ Treasury:-0.10, Yield_Curve:-0.10, Tech_Equities:-0.05, Financials:-0.06, SPX:-0.04, Credit_Markets:-0.03 },
    unmodelled:true,
    note:'Entirely asserted. Now a deliberate sign-mirror of Fiscal Stimulus — the Mk9 asymmetry was unjustified, so it is removed rather than dressed up. Real tightening is not perfectly symmetric, but an asserted asymmetry with no basis was worse.' },
```

- [ ] **Step 2: Strengthen `deregulation`'s caveat** (keep the sign, label louder) — leave `exogenous` as-is, sharpen the `note` to name it the single weakest claim and tie it to 2006:

```javascript
    note:'Entirely asserted, and the SINGLE WEAKEST claim on the map: the positive sign assumes deregulation is good for banks — exactly the 2006 consensus that preceded 2008. Treat as a hypothesis to argue with, not a result.' },
```

- [ ] **Step 3: Verify provenance still green** (reuse the Task 3 Step 3 harness). Expected `PROV {"conflicts":0,"demotions":0}`.

- [ ] **Step 4: Commit**

```bash
git add bullion-live-map/bullion_mk11_constellation.html
git commit -m "Mk12: mirror fiscal_tightening, sharpen deregulation's weak-claim label"
```

---

### Task 9: Version bump + whole-map integration verification

Bump the visible version to Mk12 (filename unchanged) and run a full smoke test of the finished map.

**Files:**
- Modify: `bullion-live-map/bullion_mk11_constellation.html` (H1 ~line 391, `<title>`, and any visible "Mk11" copy)

- [ ] **Step 1: Update visible version strings** — change the H1 `US Financial System — Mk11 Column Constellation` to `... — Mk12 Column Constellation` and the `<title>`; do NOT rename the file (preserves the public URL). Leave internal identifiers like `window._mk5Node` untouched.

- [ ] **Step 2: Full smoke test in headless Chrome**

```bash
SP=/tmp; CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; cp bullion-live-map/bullion_mk11_constellation.html "$SP/final.html"
printf '\n<script>window.addEventListener("load",()=>setTimeout(()=>{const o={};o.prov={c:PROV_CONFLICTS.length,d:PROV_DEMOTIONS.length};o.bt=!!backtestModel();triggerShock("cpi_rise");o.cpi_colored=Object.values(nodeMultipliers).filter(v=>Math.abs(v)>nodeCutoff()).length;document.getElementById("mode-toggle-btn").click();o.full=document.getElementById("app").className;console.log("FIN "+JSON.stringify(o));},1600));</script>\n' >> "$SP/final.html"
"$CHROME" --headless=new --disable-gpu --virtual-time-budget=5000 --enable-logging=stderr --v=0 "file://$SP/final.html" 2>&1 | grep -oE 'FIN .*' | sed 's/, source:.*//' | head -1
```
Expected: `FIN {"prov":{"c":0,"d":0},"bt":true,"cpi_colored":N≥1,"full":""}` — provenance green, backtest live, CPI Rise lights ≥1 node, Tools toggle reveals full view.

- [ ] **Step 3: Visual confirmation** — screenshot the default (beginner) view and the Audit Log; confirm the H1 reads Mk12 and the Model-accuracy table renders. (Manual read of the two PNGs.)

- [ ] **Step 4: Commit and push**

```bash
git add bullion-live-map/bullion_mk11_constellation.html
git commit -m "Mk12: version bump + whole-map integration verification"
git push origin main
```

---

## Self-Review

- **Spec coverage:** calibration (T1–T2), adoption (T3), in-page backtest engine (T4) + panel (T5), the three folded fixes — runManual (T6), threshold (T7), weak scenarios (T8) — and version/integration (T9). Train/test split is a Global Constraint honored in T1/T2 (train) and T4 (test). The "contemporaneous, not forecasting" and "nodes not graded" caveats are in T5 Step 1. All spec success criteria map to a task.
- **Placeholder scan:** T3 is intentionally data-driven (adopt per report) — this is a procedure with a fully specified rubric, not a placeholder; exact numbers cannot precede the fit. The `BACKTEST_FIELDS` stub in T4 Step 1 is explicitly flagged for deletion in favor of `BACKTEST_MAP`.
- **Type consistency:** `nodeCutoff()` used by both `expandAffected` and `updateGraph` (T7); `backtestModel()` shape (`{split,testLen,fields:[{field,label,n,hitRate,r2}]}`) produced in T4 and consumed in T5; `train_split`/`verdict`/`ols`/`first_diff` signatures consistent across T1→T2.
