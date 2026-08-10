# Mk Ultra Macro Engine — Session Handoff

**Written:** 2026-08-11 · **For:** whoever next touches `bullion_mkultra.html`'s "Run macro analysis" feature, or revisits the composite health score specifically

## Goal

Replace `bullion_mkultra.html`'s dead "Run AI analysis" button (a `fetch('https://api.anthropic.com/...')` call with no API key — always 401s on the public site, silently falls back to a crude hand-picked formula) with an honest, deterministic engine. Shipped: a node-level current-conditions readout reusing the map's already-sourced `NODE_ELASTICITY` matrix, plus a short narrative. **Not shipped, disabled after a final review**: a numeric composite health score — it was found inverted under real financial stress and a proposed fix was proven mathematically impossible. Full technical diagnosis lives in the plan's Addendum, not repeated here.

- Spec: `docs/superpowers/specs/2026-08-09-bullion-mkultra-macro-engine-design.md` (now **stale** re: the health score — still describes it as a shipped output; not corrected, see Traps below)
- Plan (authoritative — has the full C1 diagnosis in its **Addendum, dated 2026-08-11, at the very end of the file**): `docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md`
- Progress ledger: **deleted** — it was git-ignored, worktree-local scratch (`.superpowers/sdd/2026-08-09-bullion-mkultra-macro-engine/`), removed after the branch merged cleanly, per this project's standing SDD convention ("git history is the record now"). The two most valuable pieces of its content were copied to durable, committed locations first — see the two `docs/superpowers/archive/bullion-mkultra-macro-engine-*.md` files referenced below. For the full task-by-task history (two mutation-tested fix loops, the final-review saga), read `git log --oneline 05872c1..6bc47b2` and the individual commit messages; they're detailed.

## How to resume (do this first)

1. **This work is done: merged to `main` and pushed to `origin`.** Merge commit `6bc47b2` (local merge of `worktree-bullion-mkultra-macro-engine`, itself preceded by a routine merge of `origin/main`'s daily-data-cron bot commits). Confirm with `git log --oneline -3` on `main` — should show the merge commit at the tip, and `git log --oneline origin/main -1` should match. The feature branch and its worktree have both been deleted (`git branch -d worktree-bullion-mkultra-macro-engine`, `git worktree remove`); there is nothing left to resume mid-flight.
2. Read the plan's Addendum section first (search `docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md` for `## Addendum (2026-08-11)`) — it is the single source of truth for why the health score is disabled and what the two live candidate fix directions are.
3. For the raw diagnostic detail behind the Addendum's summary (exact commands run, candidate-weighting evaluations, the full mathematical proof), read `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-sign-invariance-proof.md` and `docs/superpowers/archive/bullion-mkultra-macro-engine-descope-report.md` — both committed, both survive independent of the deleted worktree/ledger.
4. **Immediate next action:** none required — this is a completed, merged, pushed piece of work. The only reason to come back to it is to revisit the composite health score (see "What's next" below) or to close the small deferred Minor items.

## Current state (active files)

**Branch:** none — merged into `main` and deleted. `main` is at `6bc47b2` on both local and `origin`.

**Files created / changed (all inside `bullion-live-map/`):**
- `backfill_baseline.py` (new) — fetches 15yr FRED/Yahoo history, computes per-field baseline stats, fits a PCA-derived composite weighting, splices `BASELINE_STATS` into `bullion_mkultra.html`. The composite-weighting part (`pc1_loadings`, `composite_percentiles`) is correct-but-unused infrastructure now (see Traps) — the per-field stats it also produces (`BASELINE_STATS.fields`) ARE live-load-bearing, consumed by `computeNodeMultipliers`.
- `bullion_mkultra.html` — three new pure JS functions (`computeCompositeScore`, `computeNodeMultipliers`, `buildMacroNarrative`), a `runMacroAnalysis()` handler replacing the dead AI call, a new audit-log section. `bullion_mk11.html` through `bullion_mk18.html` are confirmed byte-unchanged throughout (frozen-file sha check ran clean in Task 9).
- `tests/test_backfill_baseline.py`, `tests/test_macro_engine_js_parity.py` (new) — 74 tests total across the whole suite, all green as of `main`'s tip (`6bc47b2`) — re-verified after the merge, not just before it.
- `docs/superpowers/specs/2026-08-09-bullion-mkultra-macro-engine-design.md`, `docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md` — spec and plan, both on `main` now.
- `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-sign-invariance-proof.md`, `docs/superpowers/archive/bullion-mkultra-macro-engine-descope-report.md` — the two preserved raw diagnostic reports (see point 3 above).

**Files later work will modify (untouched so far):** none anticipated unless the composite score gets revisited — that work would live entirely in `backfill_baseline.py`'s `build_baseline()` and `bullion_mkultra.html`'s `computeCompositeScore`.

**Scratch workspace / traps:**
- ⚠️ **`docs/superpowers/specs/2026-08-09-bullion-mkultra-macro-engine-design.md` (the design spec) is stale.** It still describes the composite health score as one of three shipped outputs and details a methodology (PCA over a 15yr window, `composite_percentiles` median=50, sector-ETF dispersion) that was never fully implemented and is now also disabled. It was **not** corrected during the descope — only the plan document's Addendum has the accurate, current story. Don't trust the spec for how the health score currently works; it doesn't currently work at all.
- ⚠️ **`computeCompositeScore` (client) and the PCA-fitting path inside `build_baseline()` (Python) are intentionally dead code as of `HEAD`** — correct, tested, but not called from the live UI. Both carry an explicit code comment pointing back to the plan's Addendum. Don't delete them without reading that Addendum first; don't re-enable them without addressing the root cause (see "What's next").
- The SDD workspace and its ledger are gone (deleted after merge, per convention) — this is expected, not a trap. Its two most valuable files were already copied to `docs/superpowers/archive/` and committed before deletion (see above).
- Not mine — leave alone: everything outside `bullion-live-map/` and the doc files listed above.

## What has changed

- **Tasks 1-8** (per the original 9-task plan) all shipped clean: statistical backfill script, three pure JS engine functions, UI wiring, audit-log integration. Each went through individual task review; two (Task 5, Task 6) needed fix rounds for test-quality gaps (not logic bugs) — both verified via mutation testing, both closed clean. Task 3 was reopened once mid-plan when Task 4's testing surfaced a real bug (composite row-matrix mixing a 15yr window for some fields with a 2yr window for trending fields, producing an artificial discontinuity) — fixed, re-reviewed clean, documented in the plan's Global Constraints.
- **Task 9** (final regression + whole-branch review) found a second, much more serious problem: **the composite health score reads backwards under real stress.** Verified directly: a synthetic full crisis (VIX 45, HY credit spreads to 8%, SPX −35%) scored **100/"Healthy"**; the actual calm market that day scored 18/"Elevated stress". Root cause: PCA fit over the only window where all 11 composite fields have comparable history (~2yr, bounded by two credit-spread series' short real FRED history) found that **89.6% of its dominant factor's weight sits on nominal interest-rate levels**, with VIX/SPX/credit-spreads/Fed-balance-sheet contributing **~0%** — the window simply had no real stress episode for those to correlate around, and PCA correctly (not buggy) found whatever else was the dominant pattern instead.
- A proposed fix (sign-align every input to its expected stress direction before fitting PCA) was implemented and **proven to be a mathematical no-op**: PCA is invariant to per-column sign flips (formal proof + empirical confirmation — the "fixed" loadings came out bit-identical to the buggy ones, diff `1.39e-17`, pure float noise). Full proof preserved at `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-sign-invariance-proof.md`.
- **Decision (made by the project owner, not unilaterally):** disable the composite health score from the shipped UI rather than attempt a third, riskier methodology change in the same session. `computeNodeMultipliers` (the separate, correct, `NODE_ELASTICITY`-based mechanism) and a trimmed 2-sentence narrative ship as designed. This descope shipped as commit `34bc403`, reviewed clean (0 Critical/Important findings), merged to `main` at `6bc47b2` and pushed to `origin`.

## What has failed / risks / caveats

- **The composite health score does not work and is not shown.** This is the headline caveat — see above. It is not a small residual bug; the whole mechanism (PCA-discovered weights on a window this short) may not be viable at all without either much longer history for the credit-spread fields (blocked by FRED's April-2026 retention change — verify that's still true if revisiting) or abandoning PCA-discovered weights for a different scheme.
- **UNVERIFIED / low-risk residuals, all Minor, deferred to the ledger, none block using this branch as-is:**
  - Audit log no longer surfaces `BASELINE_STATS.generated_at`, even though `computeNodeMultipliers` (shipped) still depends on that baseline's freshness — small transparency regression, one clause would restore it.
  - Two in-code comments say credit spreads contributed "~0%" to the bad PCA fit; the Addendum's more precise finding is that credit spreads specifically loaded with an **inverted sign** (actively backwards, not merely silent) — worth aligning the comments to the Addendum's wording.
  - `clearAI()` still writes to the now-hidden `#health-num`/`#health-label`/`#health-bar` elements — harmless dead writes, no user-visible effect.
  - A pre-existing, unrelated bug was found and correctly left alone (out of this branch's scope): `#impacts-section`'s `class="hidden"` has no matching CSS rule anywhere in the file, so it's silently always visible — not something this branch introduced or should fix.
- **Nothing is BLOCKED.** All 74 tests pass, the frozen `mk11-18.html` files are confirmed byte-unchanged, and the shipped feature (node impacts + narrative) is independently browser-verified working with 0 console errors.

## What's next (ordered)

1. **Nothing required.** This work is complete, merged, and pushed. The items below are only relevant if/when someone chooses to pick this back up.
2. **If revisiting the composite health score**, read the plan's Addendum in full first, then pick one of the two evaluated-but-not-adopted directions it documents (both were investigated this session, only the first was empirically validated on the specific repro cases):
   - **Equal-weighted sign-aligned z-scores** — drop PCA-discovered weights entirely, average the 11 `EXPECTED_STRESS_SIGN`-aligned z-scores (a dict already partially sketched during the blocked fix attempt — check `docs/superpowers/archive/bullion-mkultra-macro-engine-pca-sign-invariance-proof.md` for what was tried) with equal weight. Empirically confirmed during this session to correctly rank a synthetic crisis below a synthetic calm scenario.
   - **Hand-specified category weights** on sign-aligned z-scores, reviving the original credit/funding/equity/safe-assets/volatility structure from the design spec's brainstorming phase — closer to a real FCI's category structure, reintroduces a manual judgment call.
   - A third option (a materially longer fitting window with a proper stationarity transform for the trending fields, instead of the current window-shrinking approach) would let PCA-discovered weights work as originally intended, but is blocked by `hy_oas`/`ig_oas`'s ~3yr real-data ceiling — verify that FRED constraint hasn't changed before ruling it out again.
3. Close the small Minor items from "What has failed" above if convenient — none are urgent, all are cheap. Start a fresh branch/worktree for this rather than trying to resume the deleted one.

## Verification idioms used in this project

- **Full test suite:** `cd bullion-live-map && python3 -m unittest discover -s tests -v` — expect `Ran 74 tests ... OK`.
- **JS parity tests specifically** (shell out to a real `node` process against the actual extracted JS, per this project's existing `test_chain_reaction_js_parity.py` pattern): `python3 -m unittest tests.test_macro_engine_js_parity -v`.
- **Frozen-file check:** `sha256sum bullion_mk11.html ... bullion_mk18.html` — must match prior sessions' recorded shas (mk15 `ebfaaaf6…`, mk16 `ef9fbc55…` per earlier project memory); none of this branch's work should ever touch these.
- **Browser verification:** this project's standing convention is headless Chrome with an isolated `--user-data-dir`, served over `http://localhost` (not `file://`, since the page fetches `data.json`), `--use-gl=angle --use-angle=swiftshader` if the 3D globe needs WebGL. The `headless-chrome-verification` skill wraps this.
- **Regenerating `BASELINE_STATS`** (only needed if `backfill_baseline.py`'s stats-computation logic changes): `python3 backfill_baseline.py` — needs `~/.config/bullion/fred_api_key` present, takes a couple of minutes (15yr fetch across ~19 fields), rewrites the spliced block in `bullion_mkultra.html` between the `BASELINE-STATS-START`/`END` markers.
