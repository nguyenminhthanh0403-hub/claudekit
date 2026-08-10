# Mk Ultra composite health score — fix design

## Problem

`bullion_mkultra.html`'s composite health score (`computeCompositeScore`, fed by `backfill_baseline.py`'s PCA fit) shipped **disabled** on 2026-08-11 (commit `34bc403`) after a final review found it inverted under real financial stress: a synthetic full crisis (VIX 45, HY credit spreads to 8%, SPX −35%) scored 100/"Healthy"; the actual calm market that day scored 18/"Elevated stress".

Root cause: the PCA fit ran over the only window where all 11 composite fields have comparable history (~2yr, bounded by `hy_oas`/`ig_oas`'s short FRED retention). Over that window, 89.6% of PC1's weight landed on nominal interest-rate levels; VIX/SPX/credit-spreads/Fed balance sheet contributed ~0%, because the window contained no real stress episode for them to correlate around — not a bug in the PCA implementation, a correct fit over a sample with no signal to find. A proposed fix (sign-align every field before fitting) was proven a mathematical no-op: PCA is invariant to per-column sign flips.

This is the fix. It's a redesign of one function's methodology (`computeCompositeScore` and the composite-specific half of `build_baseline()`), not a change to anything else shipped in the 2026-08-09 plan (node impact multipliers, narrative context, UI wiring) — those were never implicated and are untouched.

Full prior context: `docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md` (`## Addendum (2026-08-11)`), `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-sign-invariance-proof.md`, `docs/superpowers/archive/bullion-mkultra-macro-engine-descope-report.md`. The 2026-08-09 design spec's composite-score section (`docs/superpowers/specs/2026-08-09-bullion-mkultra-macro-engine-design.md`) is **superseded by this document** for the composite score specifically; its node-multiplier and narrative sections still stand.

A live-tracked field, `nfci` (Chicago Fed National Financial Conditions Index — a professionally-built, much-longer-window composite doing conceptually the same job), was considered as a replacement or supplement. Decision: not used. The point of this map's own composite is to explain a score using the same sourced driver fields as the rest of the UI, not to surface an external black-box number — kept as a candidate spot-check, not adopted.

## Decision

Replace PCA-discovered weights with **hierarchical equal-weighted, sign-aligned z-scores**: average sign-aligned z-scores within each stress category, then average the categories with equal weight. Chosen over a flat per-field average because the 11-field set is structurally imbalanced (7 of 11 were rate/funding-adjacent) — a flat average would silently let that imbalance dominate, reproducing the original bug's shape by hand instead of by PCA. Category-level averaging gives each of the 5 stress *dimensions* an equal vote regardless of how many FRED series happen to represent it.

Also replaces percentile-rank scoring with a **direct z-score-to-score mapping** (no historical row-matrix walk). The original bug's complexity lived partly in keeping a windowed historical distribution self-consistent (Task 3 was reopened once already for a window-mismatch discontinuity, before the fatal PCA bug was even found); a direct mapping needs only each field's own mean/std, which are already computed correctly and untouched by this fix.

## Composite field set — trimmed from 11 to 7

Dropped: `sofr`, `tbill_3m`, `us10y`, `us2y` as raw levels. These are policy-rate-driven, not stress-driven — their primary mover is the Fed's macro stance, not market stress, which is the same ambiguity that let PCA find "nominal rates" as its dominant (wrong) factor. `us10y`/`us2y` remain live-tracked fields elsewhere (and still feed `curve_slope`, below); they're just not composite inputs anymore. `curve_slope` (`us10y − us2y`) is kept — yield-curve inversion is one of the best-established, regime-independent recession/stress signals, unlike either rate's raw level.

| Category | Fields | Higher raw value means |
|---|---|---|
| Credit | `hy_oas`, `ig_oas` | more stress |
| Volatility | `vix` | more stress |
| Equity valuation | `spx` (z-scored vs. its own recent window) | less stress |
| Funding | `fed_bs`, `rrp` | less stress (more liquidity buffer) |
| Safe assets | `curve_slope` | less stress (steeper = calmer; inverted = stress) |

## Architecture

**`backfill_baseline.py` becomes the single source of truth for the two new domain-judgment maps**, mirroring how it already owns `MEAN_REVERTING_FIELDS`/`TRENDING_FIELDS`/`COMPOSITE_FIELDS`:

- New module-level constants: `EXPECTED_STRESS_SIGN` (7 entries, `+1`/`-1`) and `COMPOSITE_CATEGORY` (7 entries, field → category name). `COMPOSITE_FIELDS` shrinks to the 7 above.
- `build_baseline()`'s output gains two new keys, `stress_sign` and `category`, holding these maps verbatim — spliced into `BASELINE_STATS` in `bullion_mkultra.html` exactly like `fields` already is. This is the only way the maps reach the browser; JS never hand-authors its own copy, so there's nothing for the two to drift out of sync on.
- `fields_out` (per-field mean/std/window_years) is **unchanged** — same 15yr/2yr window logic, same function, still used by both the composite and `computeNodeMultipliers`.
- Removed from `build_baseline()` and this file entirely: `build_zscore_rows`, `pca_first_component`, `orient_loadings`, `percentile_table` (confirmed no other caller), and the composite-specific row-matrix/PCA block. Output loses `pc1_loadings`, `composite_percentiles`, `composite_window_years`.
- These four functions plus the removed block are preserved verbatim in `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-implementation.py`, with a header linking back to the Addendum and the sign-invariance proof, in case a materially longer fitting window ever becomes viable (blocked today by `hy_oas`/`ig_oas`'s ~3yr FRED retention ceiling) and PCA-discovered weights are worth retrying.

**`bullion_mkultra.html`'s `computeCompositeScore(live)` is rewritten** (same function name/call site, new body):

1. For each of the 7 fields: `z = clip3((live[f] - BASELINE_STATS.fields[f].mean) / BASELINE_STATS.fields[f].std)`, then `signed_z = BASELINE_STATS.stress_sign[f] * z` (positive always means "more stress," regardless of field).
2. Group `signed_z` by `BASELINE_STATS.category[f]`; average within each of the 5 categories present.
3. Average the per-category scores (equal weight, one vote per category) → `avg_z`.
4. `score = round(clip(50 - (avg_z / 3) * 50, 0, 100))` — 50 neutral, 0 max stress, 100 max calm, matching the pre-existing scale's meaning (z is bounded ±3 by the per-field clip in step 1, so this maps the full clipped range onto 0–100).
5. `tier = 'measured'` if enough of the 7 fields have live data, else `'directional'`. `COMPOSITE_MIN_FIELDS_FOR_MEASURED` updates from `9` (of 11) to `6` (of 7), preserving roughly the same ~82% completeness bar.
6. `leadingCategory` = the category with the largest `|category score|`, same idea as the removed version.
7. Return shape unchanged: `{ score, tier, leadingCategory, categoryContributions, fieldsUsed, fieldsMissing }` — callers (`buildMacroNarrative`, the UI wiring below) don't need to change shape-handling code, only what they do with real values again.

The "NOT CURRENTLY CALLED" dead-code comment above `computeCompositeScore` is removed; the function is live again.

## UI / narrative

- Remove the `hidden` class from `.health-score-row` and `.health-bar-wrap` (static markup, `bullion_mkultra.html` around line 891/895).
- `runMacroAnalysis()`: restore the exact pre-descope tier/color logic (verified from the commit before `34bc403`), unchanged in wording —
  ```
  health-label = (score > 70 ? 'Healthy' : score > 45 ? 'Moderate stress' : 'Elevated stress')
               + (tier === 'directional' ? ' (directional — limited live data)' : '')
  barColor     =  score > 70 ? '#7bbf8e' : score > 45 ? '#e0b15a' : '#e0654f'
  ```
- `buildMacroNarrative`: restore the 3-sentence shape (currently 2, composite-less). New first sentence replaces the old percentile-framed one: `"Financial conditions read {score}/100 ({label}), driven primarily by {leadingCategory}."` — no percentile-of-history language, since that mechanism is gone. The other two sentences (CPI/NFP context, node headwind/support) are unchanged.
- Audit log (`openAuditLog()`): composite section rewritten to describe the real methodology (hierarchical sign-aligned z-scores, 7 fields, 5 categories) — replacing the current text, which per the standing handoff was already known to conflate node impacts with PCA even before this fix.

## Testing

- **The two repro cases that caught the original bug become permanent regression tests** — this is the most important addition: a synthetic full crisis (VIX 45, HY 8%, SPX −35%, curve inverted, `fed_bs`/`rrp` at stressed levels) must score in the "Elevated stress" band; the actual calm day's real field values must score in the "Healthy" or at least "Moderate stress" band. Neither may invert.
- `TestComputeCompositeScoreParity` (in `test_macro_engine_js_parity.py`) rewritten for the new formula: all 7 fields at their own baseline mean → score ≈ 50 (this one *can* assert a specific target now, unlike the old PCA version — no cross-field regime heterogeneity concern once every field is independently sign-aligned and z-scored against its own mean); all fields pushed to their most-stressed clip → score at or near 0; least-stressed clip → score at or near 100; missing-fields → tier degrades to `directional`.
- `test_backfill_baseline.py`: verify `stress_sign`/`category` emitted with exactly the 7 expected keys and correct values; verify `COMPOSITE_FIELDS` no longer includes the 4 dropped fields; PCA-specific tests (sign-orientation, row-matrix construction) deleted along with the code they tested.
- `buildMacroNarrative` parity tests updated for 3-sentence output and the new first-sentence wording.
- Full suite (`python3 -m unittest discover -s tests -v`), frozen-file sha check (unaffected — this touches only `bullion_mkultra.html` and `backfill_baseline.py`), headless-Chrome browser verification (standing project convention) confirming the score row/bar are now **visible** (not hidden), render sane values, 0 console errors, and the audit log shows the new methodology text.
- After implementation, re-run `python3 backfill_baseline.py` once to regenerate and splice `BASELINE_STATS` with the new `stress_sign`/`category` keys and trimmed field set.
