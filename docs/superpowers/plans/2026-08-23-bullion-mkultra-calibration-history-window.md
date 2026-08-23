# Mk Ultra — Multi-Year Calibration History — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `calibrate.py` a 6-year FRED/Yahoo/IMF history so the 6 links currently
stuck below `MIN_LINK_N=30` (`cpi→fomc`, `nfp→fomc`, `oil→cpi`, `ffr→m2`, `m2→cpi`,
`m2→gold`) become statistically testable, without touching the ~365-day `data.json`
the live map fetches on page load.

**Architecture:** A new offline script, `fetch_calibration_history.py`, reuses
`backfill_baseline.fetch_all_history()` (already proven for the annual 15-year
`BASELINE_STATS` refresh, and already immune to FRED's 2000-vintage-per-request cap)
to pull 6 years of history, transposes it into `calibrate.py`'s expected
`{date: {field: value}}` shape, and writes a separate gitignored file,
`calibration_history.json`. `calibrate.py` gains a small backward-compatible change
(optional 3rd CLI arg for its output report path) so this wider run doesn't overwrite
the tracked report that documents the production `data.json` window.

**Tech Stack:** Python 3.9, stdlib only (`json`, `unittest`) — matches the rest of
`bullion-live-map/`.

**Spec:** `docs/superpowers/specs/2026-08-23-bullion-mkultra-calibration-history-window-design.md`

## Global Constraints

- Python 3.9, stdlib only — no new dependencies.
- Never write a partial/truncated output file — if any expected field's fetch comes
  back empty, exit non-zero and leave any previous output untouched (matches
  `fetch_bullion_data.py` and `backfill_baseline.py`'s existing convention).
- `data.json` and its ~365-day window are NOT touched by this work.
- `mk11`–`mk18` frozen files must stay byte-unchanged (only `bullion_mkultra.html` may
  be touched, and only in Task 3, only if the data supports it).
- Any promotion from `directional` to `measured`, or any sign flip, must follow
  `calibrate.py`'s existing `link_verdict` rubric — sign match + `|t|>2` to promote; a
  `[FLIP]` is surfaced to the user, never auto-applied.

---

## Task 1: `fetch_calibration_history.py` + tests

**Files:**
- Create: `bullion-live-map/fetch_calibration_history.py`
- Create: `bullion-live-map/tests/test_fetch_calibration_history.py`
- Modify: `bullion-live-map/.gitignore`

**Interfaces:**
- Consumes: `backfill_baseline.fetch_all_history(key, start, end) -> {field: {date: value}}`
  (existing, unmodified); `fetch_bullion_data.load_key() -> str` (existing, unmodified);
  `fetch_bullion_data.FRED_SERIES`, `fetch_bullion_data.YAHOO_SYMBOLS` (existing dicts,
  read-only, used to build the expected-fields list).
- Produces: `transpose_to_date_major(field_major: dict) -> dict`,
  `missing_fields(field_major: dict) -> list[str]`, `EXPECTED_FIELDS: list[str]`,
  `OUT_PATH: str`, `CALIBRATION_WINDOW_YEARS: int` — all module-level, importable by
  Task 2 and by the test file.

- [ ] **Step 1: Write the failing tests**

Create `bullion-live-map/tests/test_fetch_calibration_history.py`:

```python
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_calibration_history import transpose_to_date_major, missing_fields, EXPECTED_FIELDS
import fetch_calibration_history as fetch_calibration_history_module


class TestTransposeToDateMajor(unittest.TestCase):
    def test_transposes_field_major_to_date_major(self):
        field_major = {
            "vix": {"2026-01-02": 14.5, "2026-01-03": 15.1},
            "spx": {"2026-01-02": 4800.0},
        }
        result = transpose_to_date_major(field_major)
        self.assertEqual(result, {
            "2026-01-02": {"vix": 14.5, "spx": 4800.0},
            "2026-01-03": {"vix": 15.1},
        })

    def test_empty_field_major_yields_empty_history(self):
        self.assertEqual(transpose_to_date_major({}), {})


class TestMissingFields(unittest.TestCase):
    def test_no_fields_missing_when_all_present(self):
        field_major = {f: {"2026-01-02": 1.0} for f in EXPECTED_FIELDS}
        self.assertEqual(missing_fields(field_major), [])

    def test_reports_fields_with_empty_history(self):
        field_major = {f: {"2026-01-02": 1.0} for f in EXPECTED_FIELDS}
        field_major["vix"] = {}  # simulate a failed fetch
        self.assertIn("vix", missing_fields(field_major))

    def test_reports_fields_entirely_absent(self):
        field_major = {f: {"2026-01-02": 1.0} for f in EXPECTED_FIELDS if f != "spx"}
        self.assertIn("spx", missing_fields(field_major))


class TestMainGuardsAgainstPartialFetch(unittest.TestCase):
    def setUp(self):
        self.mod = fetch_calibration_history_module
        self._orig_fetch_all_history = self.mod.fetch_all_history
        self._orig_load_key = self.mod.load_key
        self._orig_out_path = self.mod.OUT_PATH

        fd, self.tmp_path = tempfile.mkstemp(prefix="bullion_calib_test_", suffix=".json")
        os.close(fd)
        os.remove(self.tmp_path)

        self.mod.OUT_PATH = self.tmp_path
        self.mod.load_key = lambda: "dummy-key"

    def tearDown(self):
        self.mod.fetch_all_history = self._orig_fetch_all_history
        self.mod.load_key = self._orig_load_key
        self.mod.OUT_PATH = self._orig_out_path
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_partial_fetch_exits_without_writing(self):
        def fake_fetch_all_history(key, start, end):
            out = {f: {"2026-01-02": 1.0} for f in self.mod.EXPECTED_FIELDS}
            out["vix"] = {}
            return out
        self.mod.fetch_all_history = fake_fetch_all_history

        with self.assertRaises(SystemExit):
            self.mod.main()

        self.assertFalse(os.path.exists(self.tmp_path))

    def test_complete_fetch_writes_date_major_history(self):
        def fake_fetch_all_history(key, start, end):
            return {f: {"2026-01-02": 1.0, "2026-01-03": 2.0}
                    for f in self.mod.EXPECTED_FIELDS}
        self.mod.fetch_all_history = fake_fetch_all_history

        self.mod.main()

        with open(self.tmp_path) as f:
            written = json.load(f)
        self.assertIn("history", written)
        self.assertEqual(set(written["history"]["2026-01-02"]), set(self.mod.EXPECTED_FIELDS))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail with ImportError**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_calibration_history -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_calibration_history'`

- [ ] **Step 3: Write `fetch_calibration_history.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_fetch_calibration_history -v`
Expected: `Ran 7 tests ... OK`

- [ ] **Step 5: Gitignore the generated history file**

Add one line to `bullion-live-map/.gitignore`:

```
calibration_history.json
```

- [ ] **Step 6: Run the full existing suite to confirm nothing else broke**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests -v`
Expected: same pass count as before this task, plus the 7 new tests (no regressions).

- [ ] **Step 7: Commit**

```bash
cd bullion-live-map
git add fetch_calibration_history.py tests/test_fetch_calibration_history.py .gitignore
git commit -m "Mk Ultra: add multi-year calibration-history fetcher

Reuses backfill_baseline.fetch_all_history() to pull 6 years of FRED/Yahoo/IMF
history into a new, gitignored calibration_history.json -- separate from
data.json, which stays at its ~365-day live-page window. Lets calibrate.py
test the 6 links currently stuck below MIN_LINK_N=30 (cpi->fomc, nfp->fomc,
oil->cpi, ffr->m2, m2->cpi, m2->gold)."
```

---

## Task 2: Add `calibrate.py`'s optional report-path arg, run the real fetch, verify testability

**Files:**
- Modify: `bullion-live-map/calibrate.py:338-369` (`main()`)
- Create (generated by running the script, then committed): `bullion-live-map/calibration_history.json` (gitignored — NOT committed, just produced locally)
- Create (generated, then committed): `bullion-live-map/calibration_report_multiyear.txt`

**Interfaces:**
- Consumes: `fetch_calibration_history.py` from Task 1 (run as a subprocess/CLI, not
  imported).
- Produces: `calibrate.py main()` now accepts an optional 3rd `sys.argv` entry for the
  report output path, defaulting to `'calibration_report.txt'` — no change to its
  first two positional args or to any function signature other functions rely on.

- [ ] **Step 1: Modify `calibrate.py`'s `main()` to accept an optional report path**

In `bullion-live-map/calibrate.py`, inside `main()` (currently lines 338-369):

```python
def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    html_path = sys.argv[2] if len(sys.argv) > 2 else 'bullion_mkultra.html'
    report_path = sys.argv[3] if len(sys.argv) > 3 else 'calibration_report.txt'
    doc = json.load(open(path))
```

And at the bottom of the same function, change:

```python
    report = "\n".join(lines) + "\n"
    print(report)
    open(report_path, 'w').write(report)
```

(This is the only change to `calibrate.py` — no other line moves. Every existing
invocation with 0, 1, or 2 args is unaffected since `report_path` only changes from its
default when a 3rd arg is actually passed.)

- [ ] **Step 2: Verify existing behavior is unchanged**

Run: `cd bullion-live-map && python3 -m unittest test_calibrate -v`
Expected: `Ran 33 tests ... OK` (unchanged — no test exercises `main()`'s I/O, confirmed
during planning by reading `test_calibrate.py` in full).

- [ ] **Step 3: Run the real multi-year fetch**

Requires a working FRED key at `~/.config/bullion/fred_api_key` (already configured on
this machine per this project's standing setup).

Run: `cd bullion-live-map && python3 fetch_calibration_history.py`
Expected: exits 0, prints `Wrote .../calibration_history.json: N dated entries, 6yr
window (...)`. If it instead prints `Failed to fetch: <fields>` and exits 1, stop and
diagnose the named field's fetcher before continuing (do not proceed with a partial
file — none will have been written).

- [ ] **Step 4: Run calibrate.py against the wider window**

Run:
```bash
cd bullion-live-map
python3 calibrate.py calibration_history.json bullion_mkultra.html calibration_report_multiyear.txt
```
Expected: exits 0, writes `calibration_report_multiyear.txt`, and prints the same
report to stdout.

- [ ] **Step 5: Verify the 6 target links are now testable**

Open `bullion-live-map/calibration_report_multiyear.txt` and find these rows in the
`=== LINKS ===` section: `cpi -> fomc`, `nfp -> fomc`, `oil -> cpi`, `ffr -> m2`,
`m2 -> cpi`, `m2 -> gold`. Confirm each row's `n=` is now ≥30 (it will no longer say
`only n=X usable daily changes (< 30)`). The report will show each as either MEASURED
or DIRECTIONAL-for-insignificance — both are valid, honest outcomes; the goal of this
task is testability (n≥30), not a specific tier. If any of the 6 still shows n<30,
`CALIBRATION_WINDOW_YEARS` in `fetch_calibration_history.py` needs raising — stop and
do that before continuing to Task 3, re-running Steps 3-5.

- [ ] **Step 6: Commit**

```bash
cd bullion-live-map
git add calibrate.py calibration_report_multiyear.txt
git commit -m "Mk Ultra: calibrate.py accepts an optional report-path arg; run the 6yr window

Adds a 3rd, backward-compatible sys.argv slot to main() so a wider-window
calibration run doesn't overwrite calibration_report.txt (which documents
data.json's ~365-day window). calibration_report_multiyear.txt confirms the
6 previously n<30 links (cpi->fomc, nfp->fomc, oil->cpi, ffr->m2, m2->cpi,
m2->gold) are now fittable."
```

---

## Task 3: Adopt any newly-measured links or flag sign flips for review

**Files:**
- Modify (conditionally): `bullion-live-map/bullion_mkultra.html` — only the specific
  `LINKS`/`PLUMBING_LINKS` rows identified below, only if the report supports it.

**Interfaces:**
- Consumes: `bullion-live-map/calibration_report_multiyear.txt` from Task 2.

- [ ] **Step 1: Classify each of the 6 target rows from the report**

For each of `cpi→fomc`, `nfp→fomc`, `oil→cpi`, `ffr→m2`, `m2→cpi`, `m2→gold`, read its
line in `calibration_report_multiyear.txt` and sort into one of three buckets, using
`calibrate.py`'s own `link_verdict` rubric (already encoded in the report's tier +
bracketed action):

- **Clean promotion** — tier is `MEASURED` with no `[FLIP]`/`[CONFLICT]` tag (sign
  matches, `|t|>2`).
- **Flip** — tagged `[FLIP]` (data significantly contradicts the current hand-asserted
  sign).
- **Still directional** — insignificant (`|t|≤2`) or a `[CONFLICT]` (weak
  contradiction). No map change for these; they simply remain honestly labeled, now
  backed by a real (if inconclusive) test instead of an untestable sample.

- [ ] **Step 2: For each clean promotion, update the map's tier**

In `bullion_mkultra.html`, grep for the row's `s:'<source>'` / `t:'<target>'` pair
across both `LINKS` and `PLUMBING_LINKS` (per `calibrate.py`'s own `parse_links`
docstring, a `PLUMBING_LINKS` row with the same pair supersedes the `LINKS` one — edit
whichever array actually contains the live row). Change that row's `conf:'directional'`
to `conf:'measured'`, matching exactly how prior MEASURED promotions in this file were
written (see `git log --oneline -- bullion_mkultra.html` around the 2026-07-27 honesty
pass for the existing pattern of a `conf:` literal on a link row).

- [ ] **Step 3: For each flip, stop and ask before touching the map**

Do not edit `bullion_mkultra.html` for a `[FLIP]` row without explicit confirmation —
present the report's line (source, target, current hand sign, fitted sign, `n`, `t`) to
the user and let them decide, the same review gate that produced the 4 flips
(`credit→equit`, `usd→oil`, `vix→defn`, `mortgage_30y→credit`) in the original
2026-07-27 honesty pass. If confirmed, flip the row's `sign:` value and its `conf:` tier
together (a flip is definitionally `measured`, per `link_verdict`).

- [ ] **Step 4: Re-run the full suite and the frozen-file check**

```bash
cd bullion-live-map
python3 -m unittest discover -s tests -v
python3 -m unittest test_calibrate -v
sha256sum bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html \
  bullion_mk15.html bullion_mk16.html bullion_mk17.html bullion_mk18.html
```
Expected: both suites green; every frozen-file hash matches its value from before this
task (only `bullion_mkultra.html` may have changed, and only if Steps 2 or 3 found
something to adopt).

- [ ] **Step 5: Commit (skip if nothing was promoted or flipped)**

```bash
cd bullion-live-map
git add bullion_mkultra.html
git commit -m "Mk Ultra: adopt calibrated tiers for the 6yr-testable links

Per calibration_report_multiyear.txt: [fill in the actual rows promoted/
flipped here before committing -- this message must name them, not describe
the process]."
```

---

## Self-Review Notes (for whoever executes this plan)

- **Spec coverage:** Task 1 covers the new fetcher + tests + gitignore. Task 2 covers
  the `calibrate.py` arg change + the real run + the testability check. Task 3 covers
  the adoption policy. All three "Files touched" from the spec are addressed; the spec's
  one open question (window-years sizing) is handled by Task 2 Step 5's explicit
  re-check-and-raise instruction.
- **Non-goals respected:** no new equity tickers, no `HISTORY_DAYS` change, no
  `data.json` change — verify this stays true during execution, since it's easy for a
  "while I'm in here" edit to creep into `fetch_bullion_data.py`, which this plan never
  touches.
- **Task 3's outcome is genuinely data-dependent** (which rows get promoted, if any) —
  that's inherent to a calibration/audit task, not a placeholder; the procedure for
  handling every possible outcome (clean promotion, flip, stays directional) is fully
  specified above.
