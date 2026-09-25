# Bullion Mk Ultra — Done Criteria + Criterion 2 Per-Dimension Scoping — Session Handoff

**Written:** 2026-09-25 · **For:** a fresh session picking up the per-dimension macro read in
`bullion_mkultra.html`. **The feature is BUILT and verified but UNCOMMITTED.** The owner chose to
keep the working composite score and add the five dimensions beneath it. Three rounds of stale
beliefs about the macro engine were corrected against the live file along the way — those
corrections are the most valuable thing in this document.

## Goal

Bullion had no finish line. It has been absorbing polish sessions since July (start screen, nav
redesign, orb docking) with every handoff reading "closed loop, nothing in progress" while
spawning new deferred items. This session gave it written, checkable done criteria, then scoped
criterion 2 (the market-analysis criterion) down to something buildable.

Authorities:
- **Done criteria (new, authoritative, UNTRACKED):** `docs/superpowers/bullion-done-criteria.md`
- Global workflow (revised this session, **outside this repo**): `~/.claude/CLAUDE.md`
- Writing standard for any node/link copy this work touches: the `bullion-descriptions` skill
- Spec: none. Plan: none. Progress ledger: none. This was the bounded brainstorm path, so this
  handoff plus `bullion-done-criteria.md` are the only record.

## How to resume (do this first)

1. **`git fetch origin` first.** This session pulled 15 automated data/news bot commits and the
   checkout is now at `8925500`, so the working file is current and can be read directly. Bot
   commits land on `main` continuously, so expect to be behind again.
2. Read `docs/superpowers/bullion-done-criteria.md` in full. Its "Criterion 2 — LOCKED ...
   corrected against the live file" section is the authority and already contains the corrections
   listed below. Trust it over any other handoff in this directory.
3. Do **not** trust `docs/superpowers/bullion-mkultra-macro-engine-composite-score-descoped-handoff.md`
   (2026-08-10) on the current state of the health score. See "Traps."
4. **Immediate next action: review the uncommitted diff and commit it.** `git diff --stat` should
   show one file, `bullion-live-map/bullion_mkultra.html`. Nothing else in the tree is modified.
   The owner has not yet seen the panel in their own browser, so do not commit without their
   go-ahead.

## Current state (active files)

**Branch:** `main`, 0 commits ahead of `origin/main`. The 15-behind note in "How to resume" was
true at session start; the branch was pulled to `8925500` before any edit, so read the checkout
directly now. **One modified tracked file: `bullion-live-map/bullion_mkultra.html`.**

**Files created this session (all UNTRACKED / UNCOMMITTED):**
- `bullion-live-map/bullion_mkultra.html` — **MODIFIED, uncommitted.** The whole feature. See
  "What has changed."
- `docs/superpowers/bullion-done-criteria.md` — 127 lines. The done criteria. Corrected twice as
  the live file contradicted it.
- `docs/superpowers/bullion-mkultra-criterion2-per-dimension-scoping-handoff.md` — this file.
- `~/.claude/plans/archive/CLAUDE-md-pre-2026-09-25-rewrite.md` — the pre-rewrite global workflow,
  moved somewhere durable at the owner's request. Outside this repo and not in any git repo.

**Where the new code lives in `bullion_mkultra.html`:**
- CSS `.dim-*` rules, immediately after `.health-bar-fill`.
- `<div id="dimension-rows"></div>`, between the health bar and `#narrative-box`.
- `DIM_FIELD_META`, `dimBand`, `dimDirection`, `dimNodeLabel`, `buildDimensionReads`,
  `renderDimensionReads` — **immediately before `// ─── METRIC GUIDE (Mk9)`**. ⚠️ That position is
  load-bearing, see Traps.
- One call, `renderDimensionReads(composite, live);`, at the end of `runMacroAnalysis`.
- Four new `METRIC_GUIDE` entries plus `field:` keys on three existing ones.
- The composite disclaimer paragraph, extended to describe the new panel.

**Traps:**
- ⚠️ **Do not move the new dimension code back up next to `computeCompositeScore`.** It was written
  there first and broke 6 tests in `tests/test_macro_engine_js_parity.py`. That test slices JS out
  of the HTML by text markers, and its `computeCompositeScore` slice runs all the way to
  `const NODE_ELASTICITY = {`, so anything placed between them gets captured by two overlapping
  ranges and re-declared. The block now sits before `// ─── METRIC GUIDE (Mk9)`, past every
  extraction anchor in that file. Function declarations hoist, so `runMacroAnalysis` can still call
  it from earlier in the same script block (verified).
- ⚠️ **`beginnerMode` is `true` and is never assigned anywhere else.** All 39 nodes' `expert`
  arrays are unreachable on the live page. Do not put anything a reader needs into `expert`.
- ⚠️ **`docs/superpowers/bullion-mkultra-macro-engine-composite-score-descoped-handoff.md` is
  stale and actively misleading.** It says the composite health score was found inverted and
  disabled. That was the **PCA-weighted** version. It was replaced by a hierarchical
  equal-weighted composite that is **live and visible right now**. This document sent this session
  down the wrong path for several steps. It is tracked, so it stays in place per convention — but
  do not believe it about the score.
- ⚠️ `.health-score-row.hidden` / `.health-bar-wrap.hidden` exist in CSS (line 716) but **nothing
  ever applies the `hidden` class.** It is a PCA-era vestige. The score is on screen.
- ⚠️ The local checkout is 15 commits behind. Reading `bullion-live-map/data.json` from disk gives
  2026-09-18 values; origin has 2026-09-25.
- ⚠️ `data.json`'s `class` field is `"measured"` for **all 29 fields**. It does **not** encode
  administered-versus-market-set. That mapping is new work, not a lookup.
- Not a trap, checked and fine: `BASELINE_STATS.generated_at` is 2026-08-12, six weeks old, but
  `annual-baseline-refresh.yml` regenerates it every Jan 1 with a `baseline-alarm` issue on
  failure. A 15yr/2yr baseline drifting slowly is the documented design.

**Not mine — leave alone:** `bullion_mk11.html` … `bullion_mk18.html` (frozen prototypes), the four
untracked files already in `docs/superpowers/archive/`, `.DS_Store`.

## What has changed

**In `bullion-live-map/bullion_mkultra.html` (uncommitted).** A "What is driving that score" panel
now renders beneath the retained composite score, one row per category, sorted most-stressed first.
Each row shows: the signed z, a verdict sentence, every driving field with its live value and
distance from its own average, an inline "How to read it" line with its source, and what the
audited link graph says moves it. Everything is visible without clicking — no chevrons, no
expand toggles, per the render contract.

Four things the panel does that the single score could not:
- **Flags the inflation signal.** A field more than 1.5 SD from its mean whose deviation *lowers*
  the stress read is called out in place. Right now that fires on exactly one thing: the S&P at
  2.1 SD above its 2-year mean, the most stretched number on the board, which the composite counts
  as calming.
- **States its own baseline window.** Funding and Equity valuation say they rest on 2 years of
  history, a weaker read than the 15-year dimensions.
- **Reports partial rather than quietly dropping.** Credit says "1 causal link into this dimension
  is unverified and excluded, so this list is partial" — that is `geo→credit`, `aud:false`.
- **Admits honest gaps.** Volatility says the map carries no verified causal links into it, because
  the `vix` node genuinely has zero incoming links. Nothing was invented to fill it.
- **Marks mixed provenance under a scenario.** Found by probing the shock path, which the first
  verification pass missed. `compositeLiveFromState` overrides only `vix`/`spx`/`us10y`/`us2y`, so
  with a scenario running, Volatility, Equity valuation and Safe assets go hypothetical while
  Credit and Funding keep showing **real live data** — `hy_oas`/`ig_oas`/`fed_bs`/`rrp` have no
  driver in the 5-variable model. The panel was presenting both as one coherent read. It now shows
  a banner plus a per-row `Hypothetical` / `Real live data` tag whenever `state.shock` is set, and
  neither appears when no scenario is running. Verified both ways:

  | Dimension | No shock | Under `rate_hike` | Tag |
  |---|---|---|---|
  | Safe assets | +0.66 | +1.11 | Hypothetical |
  | Funding | +0.43 | +0.43 | Real live data |
  | Volatility | −0.57 | −0.57 | Hypothetical |
  | Credit | −0.82 | −0.82 | Real live data |
  | Equity valuation | −2.06 | −1.65 | Hypothetical |

  ⚠️ If a future change gives `hy_oas`, `ig_oas`, `fed_bs` or `rrp` a scenario driver,
  `DIM_SHOCKABLE_FIELDS` must be updated with it or the tags will lie.

**Verified in headless Chrome** against live data (not jsdom — jsdom is not installed here):
5 rows, 5 signed-z values, 5 verdicts, 7 driver lines covering all 7 fields, 7 inline how-to-read
lines, 12 causal rows, 1 honest-gap notice, 3 caveat lines, 1 inflation flag, 2 administered tags,
**0 expand/collapse controls**. Screenshot confirmed the painted result, not just the DOM.

**Test status: back to the clean-tree baseline.** `126 passed, 1 failed`. The one failure,
`test_fetch_bullion_data.py::TestBuildEnvelope::test_every_known_field_has_metadata`, **fails on
the clean tree too** (verified by stashing) — it wants `fed_decision_kalshi` and
`fed_decision_polymarket` in `FIELD_META`. Pre-existing, not from this work.
`tests/test_fetch_bullion_news.py` cannot be collected at all because **Pillow is not installed**;
also pre-existing.

**Three rounds of corrections against the live file** — the real output of this session:
  1. **Option (b) already shipped.** The PCA composite was the inverted one. It was *replaced* by a
     hierarchical equal-weighted composite over 7 fields in 5 categories. Live since ~2026-08-12.
  2. **The score is visible**, not disabled. `.health-score-row.hidden` exists in CSS but nothing
     applies the class.
  3. **`computeCompositeScore` already computed the per-dimension read and discarded it.** The
     build surfaces `categoryContributions`; it does not recompute anything.
  4. **Two links are `aud:false`**, not three. The earlier count included a comment.
  5. **`beginnerMode` is permanently true**, so the planned "expert view carries the depth" was
     unbuildable. Depth went inline via `METRIC_GUIDE` instead.
  6. **The runtime graph is 93 links**, not 102. `LINKS` merges `PLUMBING_LINKS` into itself at
     load with supersede-or-append; counting both arrays pre-merge double-counts.

**Outside this repo:** `~/.claude/CLAUDE.md` rewritten (28 → 38 lines). Done criteria moved from
stage 6 to **stage 2** (the stage-6 gate could never fire, because no project ever declared it had
entered Refine); the feedback trigger changed from "reaches Refine" to "another person can use it";
a WIP limit added (2 active + 1 maintenance); stage 6 now requires every project to end **released**
or **buried**, with no third state.

## What has failed / risks / caveats

- **Nothing has failed.** No code was written, so nothing is broken.
- **UNVERIFIED:** nothing is committed, so nothing needs review. `bullion-done-criteria.md` has
  not been read back by the owner beyond the summary given in conversation.
- **The five dimensions are the ones that already exist** — Credit (`hy_oas`, `ig_oas`),
  Volatility (`vix`), Equity valuation (`spx`), Funding (`fed_bs`, `rrp`), Safe assets
  (`curve_slope`). An earlier draft of the criteria invented liquidity/credit/rates/growth. Do
  **not** build a second taxonomy alongside the live one.
- **Baseline windows differ and this must be surfaced per dimension:** Credit, Volatility and Safe
  assets use 15-year baselines; Equity valuation and Funding use **2-year**. Averaging them into
  one score hides how much less is known about two of the five. This is the strongest argument for
  the per-dimension view and it does not depend on the score being wrong.
- **The substantive design finding, carried forward:** the stress framing hides the inflation
  signal the owner asked for. Reproduced from live data 2026-09-25 (verify before relying on it):

  | Dimension | signed z | Baseline |
  |---|---|---|
  | Credit | −0.82 | 15 yr |
  | Volatility | −0.57 | 15 yr |
  | Equity valuation | **−2.06** | 2 yr |
  | Funding | +0.43 | 2 yr |
  | Safe assets | +0.66 | 15 yr |

  composite `avgZ` −0.473 → score **58/100**. Equity valuation is the largest reading on the board
  and is counted as **less** stress, because `spx` at 7,725.76 is 2.06 SD **above** its 2-year mean
  and `stress_sign.spx` is −1. Both readings are true, but a beginner reads "low stress" as
  reassuring when the underlying fact is the most stretched number present. **Equity valuation must
  show both axes** — calming on stress, stretched on valuation — or criterion 2's "what is being
  inflated" is answered by the one number that looks most benign.
- **Verdict vocabulary is decided:** three bands on the single signed-z axis — under 0.5 "in its
  normal range", 0.5 to 1.5 "somewhat outside normal", over 1.5 "well outside normal" — each
  always paired with an explicit "more/less stress than usual" direction phrase. Never let a word
  or colour carry direction alone, per the render contract. An earlier mockup used
  LOOSE/STRETCHED/NEUTRAL/NORMAL, which was four words from two different scales. Do not reuse it.

## What's next (ordered)

1. **Have the owner look at the panel in a real browser**, then commit
   `bullion-live-map/bullion_mkultra.html`. They have seen a screenshot from automation, not the
   live page.
2. **Commit `docs/superpowers/bullion-done-criteria.md`** — untracked, and it is now the project's
   only finish line.
3. **Run the stage-5 panel.** Three people, at least one with no finance background. This is the
   only thing that can actually close criteria 1 and 2, and both close on the same run. The
   question for criterion 2: can they restate, in their own words, why one flagged number is where
   it is and why it matters?
4. Build **criterion 3b**, the daily report. It is the last unbuilt criterion. No delivery channel
   exists in this repo; ntfy is already proven in the owner's Graywind stack and needs an
   `NTFY_TOPIC` decision from them.
5. Optional, deferred by decision: re-expose an expert-mode toggle. It would revive 39 nodes of
   written, cited content that is currently unreachable. Someday list, not part of these criteria.
6. Consider auditing `geo→credit` so the Credit dimension stops reporting partial. Its own `stat`
   string concedes a 2025 study found a small spread *decrease* per 1-SD rise in the Caldara &
   Iacoviello Geopolitical Risk Index, which complicates the `sign:-1` it asserts. Auditing it may
   well mean changing the sign or setting `sign:0`, which is an audit event, not a formatting fix.

## Verification idioms used in this project (for the resuming session)

- **jsdom is NOT installed here** and `npm ls -g jsdom` is empty. This session verified through
  **headless Chrome over a local HTTP server** instead, using the `headless-chrome-verification`
  skill's `cdp_probe.mjs` template. That is the path that actually works on this machine. If you do
  install jsdom, the rule below still holds.
- **Through the rendered DOM.** Call `openDetail(node)` and query the resulting HTML.
  **Do not read `NODES` or `LINKS` off `window`** — they are top-level `const`s, jsdom's module
  scope does not attach them, and they read as `undefined`. There is an `openNode()` helper
  pattern in the skill's `references/testing.md`.
- **Serve over HTTP, never `file://`.** The page fetches `data.json` and `news.json`.
  `python3 -m http.server <port>` from inside `bullion-live-map/`. Prior sessions used 8934; assume
  nothing is running and start your own.
- **Isolate headless Chrome with `--user-data-dir`**, and trust screenshots over `getComputedStyle`
  reads on hidden or backgrounded tabs — a transitioning property reports stale values there.
- **Before rewriting any node or link copy, diff the data first.** Mk versions carry identical
  `NODES`/`LINKS`; a legibility complaint is almost always a render problem, not a content problem.
- Python tests: `python3 -m pytest bullion-live-map/tests/ -q`.
