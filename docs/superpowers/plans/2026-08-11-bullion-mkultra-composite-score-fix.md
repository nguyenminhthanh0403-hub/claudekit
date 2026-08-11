# Mk Ultra Composite Health Score Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the disabled, PCA-weighted composite health score in `bullion_mkultra.html` with a working one — hierarchical equal-weighted, sign-aligned z-scores over a trimmed 7-field set — and re-enable the health-score UI it feeds.

**Architecture:** `backfill_baseline.py` becomes the single source of truth for two new domain-judgment maps (`EXPECTED_STRESS_SIGN`, `COMPOSITE_CATEGORY`), which it emits into the spliced `BASELINE_STATS` JS constant alongside the existing per-field `fields` stats. `computeCompositeScore` in `bullion_mkultra.html` is rewritten to consume those maps as data — sign-align each field's z-score, average within category, average across categories, map to a 0–100 score — with no PCA anywhere in the live path. The four functions that implemented PCA fitting are deleted from `backfill_baseline.py` and preserved verbatim in a new archive file. The UI's hidden health-score row/bar are unhidden and wired back into `runMacroAnalysis()`, and `buildMacroNarrative` regains its 3rd, composite-aware sentence.

**Tech Stack:** Python 3 stdlib only (no new dependencies), vanilla JS (matches the existing file), `node` CLI for JS↔Python parity testing (already used by `test_macro_engine_js_parity.py`).

## Global Constraints

- Scope is `bullion_mkultra.html` and `bullion-live-map/backfill_baseline.py` ONLY. `bullion_mk11.html` through `bullion_mk18.html` are never touched — verify with a frozen-file sha256 check in the final task.
- No new Python dependencies (no numpy/scipy/pandas) — pure stdlib, matching `calibrate.py`'s and `backfill_baseline.py`'s existing convention.
- No LLM call, no external network call of any kind in the analysis path (unchanged from the existing design) — fully deterministic and free.
- Composite field set shrinks from 11 to 7: `hy_oas`, `ig_oas`, `vix`, `spx`, `fed_bs`, `rrp`, `curve_slope`. Dropped: `sofr`, `tbill_3m`, `us10y`, `us2y` as raw levels — policy-rate-driven, not stress-driven, the same ambiguity that caused the original PCA bug. `us10y`/`us2y` remain live-tracked fields elsewhere and still feed `curve_slope` (`us10y − us2y`), just aren't composite inputs themselves.
- Category → fields mapping (5 categories): Credit = `hy_oas`, `ig_oas`; Volatility = `vix`; Equity valuation = `spx`; Funding = `fed_bs`, `rrp`; Safe assets = `curve_slope`.
- Expected stress sign per field (`+1` = higher raw value means more stress, `-1` = higher raw value means less stress): `hy_oas: +1`, `ig_oas: +1`, `vix: +1`, `spx: -1` (z-scored vs. its own recent window; falling = risk-off), `fed_bs: -1` (shrinking = tighter liquidity), `rrp: -1` (draining = liquidity cushion depleting), `curve_slope: -1` (steeper = calmer; inverted = stress).
- A category with zero present live fields (e.g. a `vix` data-source outage, since it's Volatility's only member) is skipped when averaging across categories — it contributes no term, not a synthetic 0. See Task 3.
- Direct z-score-to-score mapping, no percentile-rank/historical-distribution walk: `score = round(clip(50 - (avg_z / 3) * 50, 0, 100))`, where `avg_z` is the equal-weighted average of the present categories' scores and each field's underlying z-score is clipped to ±3 before sign-alignment. 50 = neutral, 0 = max stress, 100 = max calm.
- `COMPOSITE_MIN_FIELDS_FOR_MEASURED` changes from `9` (of 11) to `6` (of 7) — preserves roughly the same ~82% completeness bar for the `measured` vs. `directional` tier.
- The exact pre-descope tier/color/label logic (verified from git commit `34bc403^`, the commit immediately before the descope) must be restored verbatim in `runMacroAnalysis()`:
  ```js
  document.getElementById('health-label').textContent =
    (composite.score > 70 ? 'Healthy' : composite.score > 45 ? 'Moderate stress' : 'Elevated stress') +
    (composite.tier === 'directional' ? ' (directional — limited live data)' : '');
  const barColor = composite.score > 70 ? '#7bbf8e' : composite.score > 45 ? '#e0b15a' : '#e0654f';
  ```
- The two repro cases that caught the original bug (synthetic full crisis; the actual calm day) become permanent regression tests — this is the most important testing addition in this plan (Task 6).
- Spec: `docs/superpowers/specs/2026-08-11-bullion-mkultra-composite-score-fix-design.md`. Prior context: `docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md` (`## Addendum (2026-08-11)`), `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-sign-invariance-proof.md`, `docs/superpowers/bullion-mkultra-macro-engine-composite-score-descoped-handoff.md`.

---

## File Structure

- Modify: `bullion-live-map/backfill_baseline.py` — add `EXPECTED_STRESS_SIGN`/`COMPOSITE_CATEGORY`, shrink `COMPOSITE_FIELDS`, remove PCA-fitting functions and the composite-specific block of `build_baseline()`.
- Modify: `bullion-live-map/tests/test_backfill_baseline.py` — remove PCA-specific tests, add sign/category assertions, update `TestBuildBaseline`.
- Create: `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-implementation.py` — verbatim preservation of the removed PCA code.
- Modify: `bullion-live-map/bullion_mkultra.html` — rewrite `computeCompositeScore`, remove the JS-side `COMPOSITE_CATEGORY` constant and `_percentileRank`, unhide the health-score UI, restore `runMacroAnalysis()`'s composite wiring, restore `buildMacroNarrative`'s 3rd sentence, rewrite the audit log's macro-engine section.
- Modify: `bullion-live-map/tests/test_macro_engine_js_parity.py` — rewrite `TestComputeCompositeScoreParity` for the new formula (including the two permanent crisis/calm regression tests), update `TestBuildMacroNarrativeParity` for the 3-sentence signature. `TestComputeNodeMultipliersParity` is untouched — `computeNodeMultipliers` isn't part of this fix.
- Regenerate (no source change): `bullion-live-map/bullion_mkultra.html`'s spliced `BASELINE_STATS` block, via `python3 backfill_baseline.py`.

---

### Task 1: `backfill_baseline.py` — replace PCA fitting with sign/category maps

**Files:**
- Modify: `bullion-live-map/backfill_baseline.py:44` (`COMPOSITE_FIELDS`), `:145-197` (functions to remove), `:200-277` (`build_baseline`)
- Test: `bullion-live-map/tests/test_backfill_baseline.py`

**Interfaces:**
- Consumes: nothing new — `field_stats`, `forward_fill`, `add_curve_slope` (all unchanged) still power this.
- Produces: `EXPECTED_STRESS_SIGN: dict[str, int]`, `COMPOSITE_CATEGORY: dict[str, str]` (both module-level, 7 keys each) and `build_baseline()`'s output gaining two new top-level keys `"stress_sign"` and `"category"` (each a dict copy of the constants above), while losing `"pc1_loadings"`, `"composite_percentiles"`, `"composite_window_years"`. Later tasks (3, 4, 7) rely on `BASELINE_STATS.stress_sign` and `BASELINE_STATS.category` existing with exactly these 7 keys once spliced into the HTML.

- [ ] **Step 1: Write the failing tests for the new constants and `build_baseline()` output shape**

Replace the entire top of `bullion-live-map/tests/test_backfill_baseline.py` — the import line and the `TestZscoreRows`/`TestPCA`/`TestPercentileTable` classes are being removed since their functions are being removed in Step 3. New content for the top of the file (import line through where `TestZscoreRows` currently starts):

```python
import os
import statistics
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backfill_baseline import (
    field_stats, forward_fill, fetch_all_history,
    add_curve_slope, EXPECTED_STRESS_SIGN, COMPOSITE_CATEGORY, COMPOSITE_FIELDS,
)


class TestFieldStats(unittest.TestCase):
    def test_field_stats_matches_hand_computed_mean_and_std(self):
        values = [10.0, 12.0, 14.0, 16.0, 18.0]
        stats = field_stats(values)
        self.assertAlmostEqual(stats["mean"], 14.0)
        self.assertAlmostEqual(stats["std"], statistics.pstdev(values))
        self.assertEqual(stats["n"], 5)

    def test_field_stats_empty_raises(self):
        with self.assertRaises(ValueError):
            field_stats([])


class TestCurveSlope(unittest.TestCase):
    def test_curve_slope_is_us10y_minus_us2y(self):
        history = {"us10y": {"2020-01-01": 4.0, "2020-01-02": 4.5},
                    "us2y": {"2020-01-01": 1.0, "2020-01-02": 2.0}}
        out = add_curve_slope(history)
        self.assertAlmostEqual(out["curve_slope"]["2020-01-01"], 3.0)
        self.assertAlmostEqual(out["curve_slope"]["2020-01-02"], 2.5)


class TestCompositeSignAndCategoryMaps(unittest.TestCase):
    def test_composite_fields_is_the_trimmed_seven(self):
        self.assertEqual(
            set(COMPOSITE_FIELDS),
            {"hy_oas", "ig_oas", "vix", "spx", "fed_bs", "rrp", "curve_slope"},
        )

    def test_stress_sign_covers_exactly_the_composite_fields(self):
        self.assertEqual(set(EXPECTED_STRESS_SIGN.keys()), set(COMPOSITE_FIELDS))
        for f, sign in EXPECTED_STRESS_SIGN.items():
            self.assertIn(sign, (1, -1), f"{f} sign must be +1 or -1, got {sign}")

    def test_stress_sign_values_match_design_spec(self):
        self.assertEqual(EXPECTED_STRESS_SIGN["hy_oas"], 1)
        self.assertEqual(EXPECTED_STRESS_SIGN["ig_oas"], 1)
        self.assertEqual(EXPECTED_STRESS_SIGN["vix"], 1)
        self.assertEqual(EXPECTED_STRESS_SIGN["spx"], -1)
        self.assertEqual(EXPECTED_STRESS_SIGN["fed_bs"], -1)
        self.assertEqual(EXPECTED_STRESS_SIGN["rrp"], -1)
        self.assertEqual(EXPECTED_STRESS_SIGN["curve_slope"], -1)

    def test_category_covers_exactly_the_composite_fields(self):
        self.assertEqual(set(COMPOSITE_CATEGORY.keys()), set(COMPOSITE_FIELDS))

    def test_category_values_match_design_spec(self):
        self.assertEqual(COMPOSITE_CATEGORY["hy_oas"], "Credit")
        self.assertEqual(COMPOSITE_CATEGORY["ig_oas"], "Credit")
        self.assertEqual(COMPOSITE_CATEGORY["vix"], "Volatility")
        self.assertEqual(COMPOSITE_CATEGORY["spx"], "Equity valuation")
        self.assertEqual(COMPOSITE_CATEGORY["fed_bs"], "Funding")
        self.assertEqual(COMPOSITE_CATEGORY["rrp"], "Funding")
        self.assertEqual(COMPOSITE_CATEGORY["curve_slope"], "Safe assets")
```

Now find and delete the `TestZscoreRows`, `TestPCA`, and `TestPercentileTable` classes (currently lines 37–76 of the file, immediately after `TestCurveSlope` and before the `import json` / `TestBuildBaseline` section) — they test functions Step 3 removes.

Then update `TestBuildBaseline` (find the class starting `class TestBuildBaseline(unittest.TestCase):`) — replace its `test_build_baseline_produces_expected_keys` method body:

```python
    def test_build_baseline_produces_expected_keys(self):
        baseline = build_baseline(self._synthetic_history())
        self.assertIn("fields", baseline)
        self.assertIn("curve_slope", baseline["fields"])
        self.assertIn("stress_sign", baseline)
        self.assertEqual(set(baseline["stress_sign"].keys()),
                          {"hy_oas", "ig_oas", "vix", "spx", "fed_bs", "rrp", "curve_slope"})
        self.assertIn("category", baseline)
        self.assertEqual(set(baseline["category"].keys()),
                          {"hy_oas", "ig_oas", "vix", "spx", "fed_bs", "rrp", "curve_slope"})
        self.assertNotIn("pc1_loadings", baseline)
        self.assertNotIn("composite_percentiles", baseline)
        self.assertNotIn("composite_window_years", baseline)
        for f in ("ffr", "cpi_yoy", "dxy", "wti_px"):
            self.assertIn(f, baseline["fields"])
```

Also update the import line just above `TestBuildBaseline` (currently `from backfill_baseline import build_baseline, render_js_block, splice_into_html, RECENT_WINDOW_YEARS`) — drop the now-unused `RECENT_WINDOW_YEARS`:

```python
from backfill_baseline import build_baseline, render_js_block, splice_into_html
```

Finally, update `TestSplice.test_render_js_block_is_valid_json_payload` (drop the now-nonexistent `pc1_loadings`/`composite_percentiles` keys from its fixture):

```python
    def test_render_js_block_is_valid_json_payload(self):
        baseline = {"generated_at": "2026-08-09", "fields": {"vix": {"mean": 18.0, "std": 5.0, "n": 100, "window_years": 15}},
                    "stress_sign": {"vix": 1}, "category": {"vix": "Volatility"}}
        block = render_js_block(baseline)
        self.assertTrue(block.strip().startswith("const BASELINE_STATS ="))
        inner = block.strip()[len("const BASELINE_STATS ="):].rstrip(";").strip()
        self.assertEqual(json.loads(inner), baseline)
```

- [ ] **Step 2: Run the tests to verify they fail with an import error**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline -v`
Expected: `ImportError: cannot import name 'EXPECTED_STRESS_SIGN' from 'backfill_baseline'` (the constant doesn't exist yet).

- [ ] **Step 3: Implement the new constants and remove the PCA-fitting code**

In `bullion-live-map/backfill_baseline.py`, replace the `COMPOSITE_FIELDS` line (currently line 44) and add the two new maps right after it:

```python
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
```

Delete these four functions entirely (they will be preserved in Task 2, not lost): `build_zscore_rows`, `pca_first_component`, `orient_loadings`, `percentile_table` — currently occupying roughly lines 145–197 (from `def build_zscore_rows(history, stats_by_field, fields):` through the end of `def percentile_table(values, n_points=101):`, i.e. everything between `add_curve_slope` and `build_baseline`).

In `build_baseline()`, replace the composite-specific block — everything from the `# The row matrix that feeds the PCA fit AND the percentile table...` comment through the `return` statement — with:

```python
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "fields": fields_out,
        "stress_sign": dict(EXPECTED_STRESS_SIGN),
        "category": dict(COMPOSITE_CATEGORY),
    }
```

The rest of `build_baseline()` (forward-fill grid construction, the `fields_out` loop over `MEAN_REVERTING_FIELDS`/`TRENDING_FIELDS`) is unchanged — leave it as-is.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_backfill_baseline -v`
Expected: all tests OK, no failures or errors.

- [ ] **Step 5: Commit**

```bash
git add bullion-live-map/backfill_baseline.py bullion-live-map/tests/test_backfill_baseline.py
git commit -m "Mk Ultra: replace PCA composite fit with sign/category maps in backfill_baseline.py"
```

---

### Task 2: Archive the removed PCA implementation

**Files:**
- Create: `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-implementation.py`

**Interfaces:**
- Consumes: the exact pre-Task-1 source of `build_zscore_rows`, `pca_first_component`, `orient_loadings`, `percentile_table`, and the composite-specific block of `build_baseline()` (from git history, since Task 1 already removed them from the live file).
- Produces: nothing consumed by later tasks — this is a pure preservation/reference artifact, not imported by any test or script.

- [ ] **Step 1: Retrieve the pre-removal source**

Run: `git show HEAD~1:bullion-live-map/backfill_baseline.py > /tmp/pre-removal-backfill.py` (run from the repo root, right after Task 1's commit — `HEAD~1` is the commit before Task 1's, i.e. the state before the PCA functions were removed; if other commits have landed in between, use the specific commit hash from Task 1 instead of `HEAD~1`).

- [ ] **Step 2: Write the archive file**

Create `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-implementation.py` with this header, followed by the four removed functions and the removed composite block copied verbatim from `/tmp/pre-removal-backfill.py`:

```python
"""Archived: the PCA-weighted composite scoring implementation removed from
backfill_baseline.py on 2026-08-11.

This code is CORRECT (does what it says) but its OUTPUT was found inverted
under real financial stress -- see the full diagnosis:
  - docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md
    (search "## Addendum (2026-08-11)")
  - docs/superpowers/archive/bullion-mkultra-macro-engine-pca-sign-invariance-proof.md
  - docs/superpowers/specs/2026-08-11-bullion-mkultra-composite-score-fix-design.md
    (the replacement methodology's design)

Root cause, briefly: PCA fit over the only window where all 11 original
composite fields had comparable history (~2yr, bounded by hy_oas/ig_oas's
short FRED retention) put ~90% of its weight on nominal rate levels, not
stress. A proposed sign-alignment fix was proven a mathematical no-op (PCA
is invariant to per-column sign flips).

Preserved here, not deleted, in case a materially longer fitting window
becomes viable later (blocked as of 2026-08-11 by hy_oas/ig_oas's ~3yr real
FRED data ceiling -- verify that constraint still holds before reviving
this) and PCA-discovered weights are worth retrying. Not imported or
executed by anything -- copy relevant pieces back into backfill_baseline.py
if reviving.
"""
import math
import random
```

Then paste in, unmodified, the four function bodies (`build_zscore_rows`, `pca_first_component`, `orient_loadings`, `percentile_table`) and the removed `build_baseline()` composite block (the row-matrix/PCA-fit code, kept as a comment-annotated standalone snippet showing how it plugged into `build_baseline`, since the surrounding function itself no longer exists in this shape) — copied verbatim from `/tmp/pre-removal-backfill.py`. Do not paraphrase or "clean up" the code during the copy — this file's entire value is being an exact historical record.

- [ ] **Step 3: Verify the archive file is syntactically valid Python**

Run: `python3 -m py_compile docs/superpowers/archive/bullion-mkultra-macro-engine-pca-implementation.py`
Expected: no output, exit code 0 (a `.pyc` is written to `__pycache__` — that's fine, it's already gitignored).

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/archive/bullion-mkultra-macro-engine-pca-implementation.py
git commit -m "Mk Ultra: archive the removed PCA composite-scoring implementation"
```

---

### Task 3: `computeCompositeScore` — rewrite for hierarchical sign-aligned z-scores

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html:4063-4131` (approximate — the `COMPOSITE_CATEGORY` constant, `COMPOSITE_MIN_FIELDS_FOR_MEASURED`, `_clip3`, `_percentileRank`, and `computeCompositeScore` all live in this region, immediately before `computeNodeMultipliers`)
- Test: `bullion-live-map/tests/test_macro_engine_js_parity.py` (`TestComputeCompositeScoreParity`)

**Interfaces:**
- Consumes: `BASELINE_STATS.fields[f]` (`{mean, std, n, window_years}`, unchanged shape, produced by Task 1), `BASELINE_STATS.stress_sign[f]` and `BASELINE_STATS.category[f]` (new, produced by Task 1, spliced into the HTML by Task 7's regeneration — until Task 7 runs, the currently-spliced `BASELINE_STATS` block still has the *old* shape with no `stress_sign`/`category` keys, so this task's own parity tests must supply their own synthetic `BASELINE_STATS`-shaped fixture inline rather than relying on the file's live spliced block; see Step 1).
- Produces: `computeCompositeScore(live)` returning `{ score: number, tier: 'measured'|'directional', leadingCategory: string|null, categoryContributions: {[category: string]: number}, fieldsUsed: string[], fieldsMissing: string[] }` — same shape as before, consumed by Task 4's `runMacroAnalysis()` and `buildMacroNarrative()`.

- [ ] **Step 1: Write the failing tests for the new formula**

In `bullion-live-map/tests/test_macro_engine_js_parity.py`, replace the entire `TestComputeCompositeScoreParity` class body (keep the class declaration and `@unittest.skipUnless` decorator, replace `setUp` and all test methods):

```python
@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class TestComputeCompositeScoreParity(unittest.TestCase):
    def setUp(self):
        with open(MAP_PATH) as f:
            self.snippet = _extract_js_snippet(f.read())

    def _synthetic_baseline_prelude(self):
        # The live BASELINE_STATS block spliced into bullion_mkultra.html
        # won't have stress_sign/category until Task 7 regenerates it, so
        # these tests inject a synthetic BASELINE_STATS-shaped object with
        # exactly the 7 composite fields, matching backfill_baseline.py's
        # EXPECTED_STRESS_SIGN/COMPOSITE_CATEGORY values.
        return """
BASELINE_STATS.stress_sign = {hy_oas:1, ig_oas:1, vix:1, spx:-1, fed_bs:-1, rrp:-1, curve_slope:-1};
BASELINE_STATS.category = {hy_oas:'Credit', ig_oas:'Credit', vix:'Volatility', spx:'Equity valuation', fed_bs:'Funding', rrp:'Funding', curve_slope:'Safe assets'};
"""

    def test_all_fields_at_their_own_mean_scores_near_neutral(self):
        # Unlike the old PCA version, every field independently sign-aligned
        # and z-scored against its own mean has no cross-field regime
        # heterogeneity concern -- "every field at its own baseline mean"
        # IS the neutral point by construction, so this can assert a
        # specific target (unlike the old test, which explicitly could not).
        script = self.snippet + self._synthetic_baseline_prelude() + """
const live = {};
for (const f of Object.keys(BASELINE_STATS.stress_sign)) {
  live[f] = BASELINE_STATS.fields[f].mean;
}
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertAlmostEqual(result["score"], 50, delta=1)
        self.assertEqual(result["tier"], "measured")
        self.assertEqual(len(result["fieldsMissing"]), 0)

    def test_missing_fields_degrade_tier_to_directional(self):
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
// Only supply 2 of the 7 composite fields -- well under the 6-of-7 bar.
live[fields[0]] = BASELINE_STATS.fields[fields[0]].mean;
live[fields[1]] = BASELINE_STATS.fields[fields[1]].mean;
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertEqual(result["tier"], "directional")

    def test_all_fields_at_max_stress_clip_scores_near_zero(self):
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
fields.forEach(f => {
  const stat = BASELINE_STATS.fields[f];
  const sign = BASELINE_STATS.stress_sign[f];
  // Push every field 3 std-devs in ITS OWN stress direction.
  live[f] = stat.mean + sign * 3 * stat.std;
});
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertLessEqual(result["score"], 5)

    def test_all_fields_at_min_stress_clip_scores_near_hundred(self):
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
fields.forEach(f => {
  const stat = BASELINE_STATS.fields[f];
  const sign = BASELINE_STATS.stress_sign[f];
  live[f] = stat.mean - sign * 3 * stat.std;
});
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertGreaterEqual(result["score"], 95)

    def test_category_with_zero_present_fields_is_skipped_not_zeroed(self):
        # Volatility's only member is vix. Omitting vix from `live` entirely
        # must drop Volatility from the average, not silently treat it as a
        # neutral (z=0) contributor -- a neutral synthetic vote would still
        # subtly pull the score, which is exactly the kind of unstated
        # imputation this fix's category-weighting was designed to avoid.
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign).filter(f => f !== 'vix');
const live = {};
fields.forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertNotIn("Volatility", result["categoryContributions"])
        self.assertAlmostEqual(result["score"], 50, delta=1)

    def test_synthetic_crisis_scores_low_not_high(self):
        # THE regression test for the original bug. VIX 45, HY spreads to
        # 8%, SPX -35% from mean must NOT score "Healthy" -- this exact
        # scenario scored 100/"Healthy" under the old PCA version. Verified
        # by hand during plan-writing (executed against this project's real
        # BASELINE_STATS.fields values, not just reasoned about): this
        # scenario now scores 6/"Elevated stress" under the new formula.
        script = self.snippet + self._synthetic_baseline_prelude() + """
const live = {
  hy_oas: 8.0,
  ig_oas: BASELINE_STATS.fields.ig_oas.mean + 3 * BASELINE_STATS.fields.ig_oas.std,
  vix: 45,
  spx: BASELINE_STATS.fields.spx.mean * 0.65,
  fed_bs: BASELINE_STATS.fields.fed_bs.mean - 2 * BASELINE_STATS.fields.fed_bs.std,
  rrp: BASELINE_STATS.fields.rrp.mean - 2 * BASELINE_STATS.fields.rrp.std,
  curve_slope: -1.0,
};
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertLess(result["score"], 45,
            "Synthetic crisis (VIX 45, HY 8%, SPX -35%) must score below the "
            "'Moderate stress' threshold -- scoring 'Healthy' here is exactly "
            "the bug this fix exists to close.")

    def test_calm_baseline_scores_healthy_not_stressed(self):
        # The counterpart regression case: the actual calm market day that
        # scored 18/"Elevated stress" under the old PCA version must now
        # land in "Healthy" (score > 70) -- never inverted. Every field
        # nudged 1.5 std toward calm (verified by hand against this
        # project's real BASELINE_STATS.fields values during plan-writing:
        # this exact nudge produces score=75, comfortably inside "Healthy"
        # with real, not cherry-picked, margin).
        script = self.snippet + self._synthetic_baseline_prelude() + """
const live = {};
Object.keys(BASELINE_STATS.stress_sign).forEach(f => {
  const stat = BASELINE_STATS.fields[f];
  const sign = BASELINE_STATS.stress_sign[f];
  live[f] = stat.mean - sign * 1.5 * stat.std;
});
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertGreater(result["score"], 70,
            "A day with every field nudged 1.5 std toward calm must score "
            "'Healthy' (>70) -- this is the inverse of the original bug's "
            "failure mode (a calm day scoring 18/'Elevated stress').")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd bullion-live-map && python3 -m unittest tests.test_macro_engine_js_parity.TestComputeCompositeScoreParity -v`
Expected: failures — either a `node` runtime error (`BASELINE_STATS.stress_sign is undefined` — the prelude sets it, but the old `computeCompositeScore` body doesn't read it yet) or assertion failures against the still-PCA-based scoring. Either failure mode confirms the test is exercising real (not-yet-updated) code.

- [ ] **Step 3: Rewrite `computeCompositeScore`**

In `bullion-live-map/bullion_mkultra.html`, delete the `COMPOSITE_CATEGORY` JS constant (currently `const COMPOSITE_CATEGORY = { ... };` right after the `BASELINE-STATS-END` comment) — it's superseded by `BASELINE_STATS.category`, spliced in from Python by Task 1/7. Update `COMPOSITE_MIN_FIELDS_FOR_MEASURED`:

```js
const COMPOSITE_MIN_FIELDS_FOR_MEASURED = 6; // of 7 total
```

Delete `_percentileRank` entirely (its only caller is the `computeCompositeScore` body being replaced below).

Delete the `// NOT CURRENTLY CALLED...` comment block above `computeCompositeScore`, and replace the entire function body:

```js
function computeCompositeScore(live) {
  const fields = Object.keys(BASELINE_STATS.stress_sign);
  const liveWithSlope = Object.assign({}, live);
  if (typeof live.us10y === 'number' && typeof live.us2y === 'number') {
    liveWithSlope.curve_slope = live.us10y - live.us2y;
  }
  const fieldsUsed = [], fieldsMissing = [];
  const categorySums = {}, categoryCounts = {};
  fields.forEach(f => {
    const stat = BASELINE_STATS.fields[f];
    const v = liveWithSlope[f];
    if (typeof v !== 'number' || !stat || !stat.std) { fieldsMissing.push(f); return; }
    fieldsUsed.push(f);
    const z = _clip3((v - stat.mean) / stat.std);
    const signedZ = BASELINE_STATS.stress_sign[f] * z;
    const cat = BASELINE_STATS.category[f];
    categorySums[cat] = (categorySums[cat] || 0) + signedZ;
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  });
  const categoryContributions = {};
  Object.keys(categorySums).forEach(cat => {
    categoryContributions[cat] = categorySums[cat] / categoryCounts[cat];
  });
  const presentCategories = Object.values(categoryContributions);
  const avgZ = presentCategories.length
    ? presentCategories.reduce((a, b) => a + b, 0) / presentCategories.length
    : 0;
  const score = Math.round(Math.max(0, Math.min(100, 50 - (avgZ / 3) * 50)));
  const tier = fieldsUsed.length >= COMPOSITE_MIN_FIELDS_FOR_MEASURED ? 'measured' : 'directional';
  let leadingCategory = null, leadingAbs = -1;
  Object.entries(categoryContributions).forEach(([cat, v]) => {
    if (Math.abs(v) > leadingAbs) { leadingAbs = Math.abs(v); leadingCategory = cat; }
  });
  return { score, tier, leadingCategory, categoryContributions, fieldsUsed, fieldsMissing };
}
```

Note `_clip3` (the `Math.max(-3, Math.min(3, z))` helper) is unchanged and still used — leave it in place.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_macro_engine_js_parity.TestComputeCompositeScoreParity -v`
Expected: all 7 tests OK.

- [ ] **Step 5: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html bullion-live-map/tests/test_macro_engine_js_parity.py
git commit -m "Mk Ultra: rewrite computeCompositeScore as hierarchical sign-aligned z-scores"
```

---

### Task 4: Re-enable the health-score UI and restore the 3-sentence narrative

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html:891,895` (hidden UI markup), `:5311-5330` (`buildMacroNarrative`), `:5342-5375` (`runMacroAnalysis`)
- Test: `bullion-live-map/tests/test_macro_engine_js_parity.py` (`TestBuildMacroNarrativeParity`)

**Interfaces:**
- Consumes: `computeCompositeScore(live)`'s return shape from Task 3.
- Produces: `buildMacroNarrative(compositeResult, nodeResult, live)` — signature reverts to 3 positional args (was 2 after the descope); later code (none in this plan, but any future caller) must pass the composite result first.

- [ ] **Step 1: Write the failing test for the narrative's composite-aware first sentence**

In `bullion-live-map/tests/test_macro_engine_js_parity.py`, `TestBuildMacroNarrativeParity`'s `setUp` currently uses `_extract_js_snippet_through_node_mults`, which already captures `computeCompositeScore` through `buildMacroNarrative` — no change needed there. Replace both test methods' bodies (the `buildMacroNarrative(nodes, live)` two-arg calls become three-arg `buildMacroNarrative(composite, nodes, live)` calls):

```python
    def test_narrative_has_exactly_three_sentences_and_cites_real_cpi_and_score(self):
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
BASELINE_STATS.stress_sign = {hy_oas:1, ig_oas:1, vix:1, spx:-1, fed_bs:-1, rrp:-1, curve_slope:-1};
BASELINE_STATS.category = {hy_oas:'Credit', ig_oas:'Credit', vix:'Volatility', spx:'Equity valuation', fed_bs:'Funding', rrp:'Funding', curve_slope:'Safe assets'};
const live = {};
Object.keys(BASELINE_STATS.stress_sign).forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
live.cpi_yoy = 2.6;
live.nfp_mom = 150;
const composite = computeCompositeScore(live);
const driverValues = {};
DRIVERS.forEach(d => { driverValues[d.key] = BASELINE_STATS.fields[d.key].mean; });
const nodes = computeNodeMultipliers(driverValues);
const narrative = buildMacroNarrative(composite, nodes, live);
process.stdout.write(JSON.stringify({ narrative, sentences: narrative.split(/(?<=[.])\\s+/).length, score: composite.score }));
"""
        result = _run_node(script)
        self.assertEqual(result["sentences"], 3)
        self.assertIn("2.6", result["narrative"])
        self.assertIn(str(result["score"]), result["narrative"])

    def test_narrative_with_populated_mults_names_worst_and_best_nodes(self):
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
BASELINE_STATS.stress_sign = {hy_oas:1, ig_oas:1, vix:1, spx:-1, fed_bs:-1, rrp:-1, curve_slope:-1};
BASELINE_STATS.category = {hy_oas:'Credit', ig_oas:'Credit', vix:'Volatility', spx:'Equity valuation', fed_bs:'Funding', rrp:'Funding', curve_slope:'Safe assets'};
const live = {};
Object.keys(BASELINE_STATS.stress_sign).forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
live.cpi_yoy = 3.2;
live.nfp_mom = -50;
const composite = computeCompositeScore(live);
const nodes = {
  mults: {
    "Tech_Equities": -0.60,
    "Inflation": -0.15,
    "USD_Strength": 0.45,
    "Credit": 0.05
  },
  noDataNodes: ["Russia", "Geopolitics"]
};
const narrative = buildMacroNarrative(composite, nodes, live);
process.stdout.write(JSON.stringify({
  narrative,
  sentences: narrative.split(/(?<=[.])\\s+/).length,
  hasWorstNodeAsHeadwind: narrative.includes("headwind is to Tech Equities"),
  hasBestNodeAsSupport: narrative.includes("USD Strength shows the most support")
}));
"""
        result = _run_node(script)
        self.assertEqual(result["sentences"], 3,
                         "Narrative must be exactly 3 sentences")
        self.assertTrue(result["hasWorstNodeAsHeadwind"],
                        "Worst node (Tech Equities, -60%) must be paired with 'headwind is to' "
                        "(substring check prevents role-swap regression)")
        self.assertTrue(result["hasBestNodeAsSupport"],
                        "Best node (USD Strength, +45%) must be paired with 'shows the most support' "
                        "(substring check prevents role-swap regression)")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd bullion-live-map && python3 -m unittest tests.test_macro_engine_js_parity.TestBuildMacroNarrativeParity -v`
Expected: `node` runtime error — `buildMacroNarrative` currently takes 2 args, so `composite` is silently treated as the first positional arg (`nodeResult`) and `nodes`/`live` shift, producing garbage or a thrown error reading `.mults` off the wrong object.

- [ ] **Step 3: Restore the UI markup, `buildMacroNarrative`'s 3rd sentence, and `runMacroAnalysis`'s wiring**

In `bullion-live-map/bullion_mkultra.html`, remove `hidden` from both elements (currently around lines 891 and 895):

```html
      <div class="health-score-row">
        <span class="health-score-num" id="health-num">&mdash;</span>
        <span style="font-size:11px;color:var(--text-dim)" id="health-label">Run macro analysis</span>
      </div>
      <div class="health-bar-wrap">
        <div class="health-bar-bg"><div class="health-bar-fill" id="health-bar" style="width:0%;background:var(--gold)"></div></div>
      </div>
```

Replace `buildMacroNarrative`'s signature and body (currently `function buildMacroNarrative(nodeResult, live) { ... }`):

```js
function buildMacroNarrative(compositeResult, nodeResult, live) {
  const s1 = `Financial conditions read ${compositeResult.score}/100 (` +
    (compositeResult.score > 70 ? 'Healthy' : compositeResult.score > 45 ? 'Moderate stress' : 'Elevated stress') +
    `), driven primarily by ${(compositeResult.leadingCategory || 'a mix of factors').toLowerCase()}.`;

  const cpi = live.cpi_yoy, nfp = live.nfp_mom;
  const cpiTxt = (typeof cpi === 'number')
    ? `Core CPI is running at ${cpi.toFixed(1)}% against the Fed's 2% target`
    : `Core CPI data is unavailable`;
  const nfpTxt = (typeof nfp === 'number')
    ? (nfp > 100 ? 'payrolls are trending firm' : (nfp < 0 ? 'payrolls are contracting' : 'payrolls are roughly flat'))
    : 'payroll data is unavailable';
  const s2 = `${cpiTxt}; ${nfpTxt}.`;

  const entries = Object.entries(nodeResult.mults);
  let s3;
  if (entries.length === 0) {
    s3 = 'No live driver is currently far enough from its historical baseline to move any node materially.';
  } else {
    entries.sort((a, b) => a[1] - b[1]);
    const worst = entries[0], best = entries[entries.length - 1];
    const pctTxt = v => (v >= 0 ? '+' : '') + (v * 100).toFixed(0) + '%';
    s3 = `The largest current headwind is to ${worst[0].replace(/_/g, ' ')} (${pctTxt(worst[1])})` +
      (best[0] !== worst[0] ? `, while ${best[0].replace(/_/g, ' ')} shows the most support (${pctTxt(best[1])}).` : '.');
  }
  return s1 + ' ' + s2 + ' ' + s3;
}
```

In `runMacroAnalysis()`, restore the composite computation and health-bar wiring. The current body reads:

```js
function runMacroAnalysis() {
  const btn = document.getElementById('run-ai-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Analyzing...';
  playEventNarration('ai_analysis');

  const s = applyTransmission(state);
  const driverValues = {};
  DRIVERS.forEach(d => { driverValues[d.key] = (typeof s[d.key] === 'number') ? s[d.key] : d.base; });

  const nodes = state.shock && Object.keys(nodeMultipliers).length
    ? {
        mults: Object.assign({}, nodeMultipliers),
        tiers: {},
        noDataNodes: Object.keys(NODE_MAP).filter(n => !(n in nodeMultipliers)),
      }
    : computeNodeMultipliers(driverValues);
  lastNodeMultiplierResult = nodes;
  hasRunMacroAnalysis = true;

  const live = { cpi_yoy: s.cpi_yoy, nfp_mom: s.nfp_mom };
  const narrative = buildMacroNarrative(nodes, live);

  document.getElementById('narrative-box').textContent = narrative;
  nodeMultipliers = nodes.mults;
  renderImpacts(nodeMultipliers, null,
    state.shock ? 'Scenario node impact multipliers' : 'Current-conditions node impact multipliers');
  updateGraph(applyTransmission(state));
  btn.disabled = false;
  btn.innerHTML = 'Run macro analysis ↗';
}
```

Replace the `const live = ...` line through the end of the function with:

```js
  const live = Object.assign({}, window.BULLION_LIVE_DATA || {}, {
    // The 5 NODE_ELASTICITY drivers can be scenario-shocked; always feed the
    // engine the CURRENT (possibly shocked) value so a running shock still
    // shows up in the score, matching this button's pre-descope behavior.
    vix: s.vix, cpi_yoy: s.cpi_yoy, dxy: s.dxy, wti_px: s.wti_px,
  });
  const composite = computeCompositeScore(live);
  const narrative = buildMacroNarrative(composite, nodes, live);

  document.getElementById('narrative-box').textContent = narrative;
  document.getElementById('health-num').textContent = composite.score;
  document.getElementById('health-label').textContent =
    (composite.score > 70 ? 'Healthy' : composite.score > 45 ? 'Moderate stress' : 'Elevated stress') +
    (composite.tier === 'directional' ? ' (directional — limited live data)' : '');
  const barColor = composite.score > 70 ? '#7bbf8e' : composite.score > 45 ? '#e0b15a' : '#e0654f';
  document.getElementById('health-bar').style.width = composite.score + '%';
  document.getElementById('health-bar').style.background = barColor;
  nodeMultipliers = nodes.mults;
  renderImpacts(nodeMultipliers, null,
    state.shock ? 'Scenario node impact multipliers' : 'Current-conditions node impact multipliers');
  updateGraph(applyTransmission(state));
  btn.disabled = false;
  btn.innerHTML = 'Run macro analysis ↗';
}
```

(The `const nodes = ...` block above the replaced section is unchanged — leave it exactly as it is; only the `const live = { cpi_yoy: s.cpi_yoy, nfp_mom: s.nfp_mom };` line onward gets replaced.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_macro_engine_js_parity.TestBuildMacroNarrativeParity -v`
Expected: both tests OK.

- [ ] **Step 5: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html bullion-live-map/tests/test_macro_engine_js_parity.py
git commit -m "Mk Ultra: re-enable health-score UI, restore 3-sentence narrative"
```

---

### Task 5: Update the audit log's macro-engine methodology section

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html:5552-5556` (the `macroEngineSection` string inside `openAuditLog()`)

**Interfaces:**
- Consumes: nothing new — this is copy-only, describing the now-working methodology instead of the disabled one.
- Produces: nothing consumed by other tasks.

- [ ] **Step 1: Replace the audit log copy**

In `bullion-live-map/bullion_mkultra.html`, find the `macroEngineSection` assignment inside `openAuditLog()` (currently):

```js
  const macroEngineSection =
    '<h3>Macro engine methodology</h3><p class="audit-note">Node-level current-conditions readings below are computed from real driver deviations run through the existing, individually-sourced <code>NODE_ELASTICITY</code> matrix (not AI, not PCA). ' +
    'A separate PCA-weighted composite health score was built but is currently <b>disabled</b>: a final review found it inverted under real stress, and a proposed fix was proven mathematically impossible (PCA is invariant to per-column sign flips). See ' +
    '<code>docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md</code> for the full diagnosis. No health score or bar is shown pending a methodology revisit.</p>' +
    '<h3>Macro engine node coverage</h3><p class="audit-note">' + macroCoverageNote + '</p>';
```

Replace it with:

```js
  const macroEngineSection =
    '<h3>Macro engine methodology</h3><p class="audit-note">Node-level current-conditions readings below are computed from real driver deviations run through the existing, individually-sourced <code>NODE_ELASTICITY</code> matrix (not AI, not PCA). ' +
    'The health score above is a hierarchical, equal-weighted composite over 7 fields in 5 categories (Credit: HY/IG spreads; Volatility: VIX; Equity valuation: SPX; Funding: Fed balance sheet, RRP; Safe assets: yield curve slope) &mdash; each field is sign-aligned to a fixed &ldquo;more stress&rdquo;/&ldquo;less stress&rdquo; convention and z-scored against its own historical baseline, averaged within category, then averaged across categories. This replaced an earlier PCA-weighted version that was found inverted under real stress and disabled; see ' +
    '<code>docs/superpowers/specs/2026-08-11-bullion-mkultra-composite-score-fix-design.md</code> for the full methodology and why PCA-discovered weights were abandoned.</p>' +
    '<h3>Macro engine node coverage</h3><p class="audit-note">' + macroCoverageNote + '</p>';
```

- [ ] **Step 2: Verify by inspection (no automated test covers audit-log HTML string content)**

Run: `grep -n "hierarchical, equal-weighted composite" bullion-live-map/bullion_mkultra.html`
Expected: one match, confirming the replacement landed. (Full behavioral verification of the audit log panel happens in Task 8's browser check.)

- [ ] **Step 3: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: update audit log copy for the working composite score"
```

---

### Task 6: Full test suite pass and BASELINE_STATS regeneration

**Files:**
- No source changes — this task runs the full suite, then regenerates the spliced constant.
- Modify (generated, not hand-edited): `bullion-live-map/bullion_mkultra.html`'s `BASELINE_STATS` block (between the `BASELINE-STATS-START`/`END` markers).

**Interfaces:**
- Consumes: `backfill_baseline.py`'s `build_baseline()` (Task 1) and the live FRED API key.
- Produces: a `BASELINE_STATS` block containing real `stress_sign`/`category` keys (previously only present in this plan's synthetic test fixtures) — this is what makes Task 3/4's rewritten `computeCompositeScore` actually work end-to-end in the browser, not just in tests that inject their own fixture.

- [ ] **Step 1: Confirm the FRED API key is present**

Run: `test -f ~/.config/bullion/fred_api_key && echo "present" || echo "MISSING"`
Expected: `present`. If `MISSING`, stop here and get the key from whoever owns this project's FRED credentials before continuing — do not proceed to Step 2 without it, since `backfill_baseline.py` will fail partway through a multi-minute fetch otherwise.

- [ ] **Step 2: Run the full test suite once before regenerating (sanity check on the code changes alone)**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests -v 2>&1 | tail -20`
Expected: `Ran 7X tests ... OK` (exact count will differ from the pre-fix 74 — Task 1 removed 3 test classes worth of PCA tests and added 5 new ones net; Task 3 added 5 new composite tests; Task 4 didn't add test count, only modified 2 existing ones). Any FAIL or ERROR here must be fixed before proceeding — do not regenerate `BASELINE_STATS` against known-broken code.

- [ ] **Step 3: Regenerate `BASELINE_STATS`**

Run: `cd bullion-live-map && python3 backfill_baseline.py`
Expected (stderr): `BASELINE_STATS refreshed: N fields, ...` — note this new script no longer prints a percentile-points count (that field is gone), so the exact message differs slightly from prior sessions' `"N fields, 101 percentile points"` — any successful non-error completion confirms the splice worked. Takes a couple of minutes (15yr fetch across ~19 fields).

- [ ] **Step 4: Verify the splice landed with the new keys**

Run: `grep -n '"stress_sign"' bullion_mkultra.html && grep -n '"category"' bullion_mkultra.html && grep -c '"pc1_loadings"' bullion_mkultra.html`
Expected: one match each for `"stress_sign"` and `"category"`, and `0` for the `"pc1_loadings"` count (confirms the old key is gone, not just added-alongside).

- [ ] **Step 5: Run the full suite again post-regeneration**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests -v 2>&1 | tail -20`
Expected: same `OK` result as Step 2 — regenerating `BASELINE_STATS` must not change test outcomes, since the parity tests use their own synthetic fixtures (Task 3/4), not the live spliced block.

- [ ] **Step 6: Commit the regenerated file**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: regenerate BASELINE_STATS with stress_sign/category"
```

---

### Task 7: Final whole-branch verification

**Files:**
- No source changes — verification only.

**Interfaces:**
- Consumes: everything from Tasks 1–6.
- Produces: nothing — this is the acceptance gate before merge.

- [ ] **Step 1: Full test suite, one more time, from a clean state**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests -v 2>&1 | tail -20`
Expected: `OK`, matching Task 6 Step 5's count.

- [ ] **Step 2: Frozen-file sha256 check**

Run: `cd bullion-live-map && sha256sum bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html bullion_mk18.html`
Expected: `bullion_mk15.html` hash starts `ebfaaaf6…` and `bullion_mk16.html` starts `ef9fbc55…` (recorded prior-session values) — confirms this branch's work never touched the frozen files, matching this plan's Global Constraints.

- [ ] **Step 3: Headless-Chrome browser verification**

Invoke the `headless-chrome-verification` skill (or follow its documented pattern directly) to: serve `bullion-live-map/` over `http://localhost:<port>` (not `file://`, since the page fetches `data.json`), load `bullion_mkultra.html` in headless Chrome with an isolated `--user-data-dir`, click `#run-ai-btn` (`document.querySelector('#run-ai-btn').click()` via `Runtime.evaluate`, not a coordinate click), then read back:
- `document.querySelector('.health-score-row').className` and `.health-bar-wrap`'s className — expect neither to contain `hidden` anymore (was the point of Task 4).
- `document.getElementById('health-num').textContent` — expect a number 0–100, not `—`.
- `document.getElementById('narrative-box').textContent` — expect 3 sentences (split on `. `), the first containing `/100 (`.
- Console messages captured during the click — expect no new JS exceptions (a `NotAllowedError: play() failed` autoplay warning is expected and harmless, per this project's established browser-automation caveat — audio autoplay is blocked in headless/backgrounded tabs regardless of app correctness).

Expected: all of the above hold; 0 real console errors.

- [ ] **Step 4: Manually re-verify the two regression scenarios directly in the running page**

Using the same headless Chrome session (or a fresh one), inject a synthetic crisis via `window.BULLION_LIVE_DATA` before clicking the button — e.g. `Object.assign(window.BULLION_LIVE_DATA, {hy_oas: 8.0, vix: 45, spx: window.BULLION_LIVE_DATA.spx * 0.65})` — then click `#run-ai-btn` and read `document.getElementById('health-label').textContent`. Expected: contains `Elevated stress` or `Moderate stress`, never `Healthy`. Then reload the page (clearing the injected override) and click `#run-ai-btn` again against real live data; read `health-label` again. Expected: does not read `Elevated stress` for what is, per the project's real data, a calm day (cross-check against `data.json`'s current `vix`/`hy_oas`/`spx` values to confirm the day is in fact calm before asserting on the label).

- [ ] **Step 5: Confirm nothing outside scope changed**

Run: `git diff --stat 6bc47b2..HEAD -- bullion-live-map/ docs/` (replace `6bc47b2` with this branch's actual base commit if different) and review the file list.
Expected: only `bullion-live-map/backfill_baseline.py`, `bullion-live-map/bullion_mkultra.html`, `bullion-live-map/tests/test_backfill_baseline.py`, `bullion-live-map/tests/test_macro_engine_js_parity.py`, `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-implementation.py`, and this plan/spec's own doc files appear — no `bullion_mk11.html`–`bullion_mk18.html`, no unrelated files.

- [ ] **Step 6: No commit needed**

This task is verification-only; if any check fails, return to the relevant earlier task, fix, and re-run this task's checks from Step 1.

---

## Self-Review Notes

- **Spec coverage:** every section of `docs/superpowers/specs/2026-08-11-bullion-mkultra-composite-score-fix-design.md` maps to a task — field trim/sign/category (Task 1), archive (Task 2), `computeCompositeScore` rewrite incl. missing-category handling (Task 3), UI/narrative (Task 4), audit log (Task 5), regeneration (Task 6), testing incl. the two permanent regression cases (Tasks 3 and 7 Step 4), frozen-file/scope checks (Task 7).
- **Type/shape consistency:** `computeCompositeScore`'s return shape (`{score, tier, leadingCategory, categoryContributions, fieldsUsed, fieldsMissing}`) is identical across Tasks 3, 4, and the audit log — no renamed fields. `buildMacroNarrative`'s signature change (2 args → 3 args, composite first) is applied consistently in both its definition (Task 4) and its only call site (`runMacroAnalysis`, also Task 4) — no stale 2-arg call left anywhere.
- **No placeholders:** every step has real, complete code — no "add appropriate handling" or "similar to Task N" shortcuts.
