# Descope report — remove the composite health score from the shipped UI

**Date:** 2026-08-11
**Commit:** `34bc403` — "Mk Ultra: descope the composite health score from the shipped UI"
**Base:** `21ddb37` (clean tree confirmed before starting; only untracked `__pycache__/` present)
**Scope:** removal of one feature's UI surface. Not a bug-fix attempt on the composite score.

---

## Context

The final review's C1 finding: the PCA-weighted composite health score is backwards under real
stress (a synthetic crisis scored 100/"Healthy"). The proposed sign-alignment fix was proven a
mathematical no-op (PCA is invariant to per-column sign flips). Root cause is the fitting
window, not the code. Owner decision: stop shipping the number; keep the node-level impact
multipliers (separate mechanism, `NODE_ELASTICITY`, no PCA) and the narrative.

The full technical diagnosis lives in the session transcript and is now referenced by pointer
from three places in the code (see Changes 4, 5, 6) rather than re-derived here.

---

## Changes

### Change 1 — hide the health-score UI (number + bar)

`bullion_mkultra.html`. Added `class="hidden"` to `.health-score-row` and `.health-bar-wrap`
as specified.

**Deviation from the brief, and why it was necessary.** The task described `.hidden` as "this
file's existing `.hidden` utility class — the same one `#impacts-section` already uses." That
premise is false, and adding the class alone would have been a silent no-op that looked correct
in the diff. Verified exhaustively:

- `grep -n "display: *none"` over the whole file returns 14 rules; **none** is a bare `.hidden`.
- Every `.hidden` rule in the file is id-scoped: `#narration-caption.hidden`, `#coach.hidden`,
  `#manual-box.hidden` (lines 260, 452, 453).
- `grep -n "hidden{"` (for a `.hidden{display:none}` string injected from JS) returns nothing.
- `grep -n "<link\|@import"` returns nothing — the file is fully self-contained, so no external
  stylesheet could be supplying the rule.

`.health-score-row` also carries `display: flex` at equal specificity, so even a generic
`.hidden` would have needed to win on source order.

Fix applied: a scoped rule immediately after `.health-score-row`, with a comment recording why
it exists.

```css
.health-score-row.hidden, .health-bar-wrap.hidden { display: none; }
```

Deliberately scoped to these two selectors rather than adding a global `.hidden { display: none }`.
A global rule would also have changed `#impacts-section`'s behavior (5 JS call sites toggle
`.hidden` on it), which is outside this descope. See Concerns.

### Change 2 — `buildMacroNarrative`: 3 sentences → 2, drop the unused parameter

Replaced the function exactly as specified. Signature is now `buildMacroNarrative(nodeResult, live)`;
the composite-percentile sentence is gone; `s2`/`s3` renumbered to `s1`/`s2`.

`_ordinal` removed. Per the brief's instruction to check first: `grep -n "_ordinal(" bullion_mkultra.html`
showed the declaration as the only remaining reference, so the deleted sentence was its only
caller. (This had a knock-on effect in the test file — see Change 7.)

### Change 3 — `runMacroAnalysis`: stop computing/rendering the composite

Replaced the body as specified. Drops `computeCompositeScore(live)`, the `window.BULLION_LIVE_DATA`
merge that existed only to feed it, and the three DOM writes to `#health-num` / `#health-label` /
`#health-bar`. Those elements keep their static initial markup and are now never touched by JS
(confirmed in the browser: `#health-num` still reads `"—"` and `#health-bar` still has inline
`width: "0%"` after a real analysis run).

Also carries the two improvements included in the specified replacement: the shock path's
`noDataNodes` is now a real coverage check (`Object.keys(NODE_MAP).filter(...)`) instead of a
fabricated empty list, and the empty-`tiers` gap is documented rather than silent.

### Change 4 — annotate `computeCompositeScore` as not-currently-called

Inserted the specified 15-line comment above `function computeCompositeScore(live) {` (now line
4103). Function body untouched.

### Change 5 — `backfill_baseline.py`: same pointer near the PCA fit

Inserted the specified `KNOWN UNRESOLVED ISSUE (2026-08-11)` block immediately before
`dates, rows = build_zscore_rows(...)`.

Note on placement: the brief said both "immediately after that existing comment block" and
"before the `dates, rows = ...` line"; those are two different positions, because the windowing
code (`recent_cutoff` / `history_for_rows`) sits between them. Chose directly before
`dates, rows`, because the note's first clause reads "even with the windowing above" and only
makes sense after that windowing code.

No re-run of the backfill, and `BASELINE_STATS` is unchanged, as instructed.

### Change 6 — audit log methodology copy

Replaced the `BASELINE_STATS.generated_at`-gated ternary with the specified unconditional
string. This also corrects the pre-existing inaccuracy in which node impacts were described as
PCA-derived; they were always `NODE_ELASTICITY`-derived.

### Change 7 — tests

`tests/test_macro_engine_js_parity.py`:

- `test_narrative_has_exactly_three_sentences_and_cites_real_cpi` →
  `test_narrative_has_exactly_two_sentences_and_cites_real_cpi`; dropped the
  `computeCompositeScore`/`composite` lines; call is now `buildMacroNarrative(nodes, live)`;
  sentence assertion `3` → `2`. CPI-citation assertion unchanged.
- `test_narrative_with_populated_mults_names_worst_and_best_nodes`: dropped the `composite`
  construction, updated the call signature, sentence assertion `3` → `2`, and updated the
  docstring's "third sentence" → "second sentence". The headwind/support pairing assertions are
  unchanged in substance.
- **Additional necessary edit:** `_extract_js_snippet_through_node_mults` anchored its JS
  extraction on `html.index("function _ordinal(n) {")`. Removing `_ordinal` in Change 2 would
  have made that `index()` raise `ValueError` and error out the whole test class. Re-anchored to
  `function buildMacroNarrative(` with a comment explaining the move.

`TestComputeCompositeScoreParity` and `TestComputeNodeMultipliersParity` are untouched.

---

## Verification

### 1. Test suite

```
$ python3 -m unittest discover -s tests -v
...
Ran 74 tests in 2.213s

OK
```

74 tests, same count as before — Change 7 rewrote 2 existing tests and added/removed none.

### 2. `computeCompositeScore` reference count

```
$ grep -n "computeCompositeScore(" bullion_mkultra.html
4103:function computeCompositeScore(live) {
$ grep -c "computeCompositeScore(" bullion_mkultra.html
1
```

Exactly one reference: its own declaration. It is genuinely no longer called from any live code
path. (`grep -c "_ordinal" bullion_mkultra.html` → `0`, fully removed.)

### 3. Browser verification (headless Chrome via CDP)

Page served over `http://localhost:8765` (not `file://`, per the skill's gotcha #8). Error
collector installed via `Page.addScriptToEvaluateOnNewDocument` *before* page scripts ran, so
load-time errors would be captured too. Clicks dispatched through the real production handlers
via `element.click()`, not coordinates.

**Before clicking "Run macro analysis":**

```
.health-score-row display : none
.health-bar-wrap  display : none
#impacts-section  display : block
narrative text            : Tap "Run macro analysis" for a quantitative read on current conditions.
```

**After clicking "Run macro analysis":**

```
.health-score-row display : none
.health-bar-wrap  display : none
#health-num textContent   : "—"
#health-bar inline width  : "0%"
#impacts-section display  : block
#impacts-list row count   : 29

NARRATIVE: "Core CPI is running at 2.6% against the Fed's 2% target; payrolls are contracting.
            The largest current headwind is to Tech Equities (-14%), while USD shows the most
            support (+14%)."
sentence count           : 2

health-score-row rect h  : 0
health-bar-wrap  rect h  : 0
```

With the analyst drawer opened (so the panel is actually laid out):

```
drawer-open re-check, health-score-row rect h: 0
drawer-open re-check, narrative rect h       : 98.75
```

This last pair is the decisive evidence, and it is layout fact rather than a `getComputedStyle`
read (the skill's gotcha #9 warns that style reads can lie on a non-focused tab). The narrative
box and the health-score row are siblings in the same panel; the narrative measures 98.75px tall
while the score row and bar measure exactly 0. The panel is rendering; the score UI within it is
not. `#health-num` still holding `"—"` and `#health-bar` still holding inline `width: "0%"`
independently confirms JS never wrote to them.

**Console errors: 0.** Captured both before and after the audit-log step:
`window.__errs` → `[]` (count 0) at both points.

**Audit log.** Clicking `#audit-log-btn` reproducibly hung the CDP probe through a 150s
watchdog. Cause identified rather than worked around blindly: `openAuditLog()` renders into a
**new window** (`window.open` + `document.write`), so a probe bound to the original target both
blocks and would be querying the wrong document. Resolved by stubbing `window.open` to capture
what the real, shipped `openAuditLog()` writes — same production code path, intercepted sink —
then parsing it with `DOMParser`. Result:

```
## Macro engine methodology
Node-level current-conditions readings below are computed from real driver deviations run
through the existing, individually-sourced NODE_ELASTICITY matrix (not AI, not PCA). A separate
PCA-weighted composite health score was built but is currently disabled: a final review found it
inverted under real stress, and a proposed fix was proven mathematically impossible (PCA is
invariant to per-column sign flips). See
docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md for the full diagnosis. No
health score or bar is shown pending a methodology revisit.

## Macro engine node coverage
6 nodes have no live-data-backed baseline reading: Fed_Reserve, Dealers, Treasury, Russia,
Geopolitics, HF.

old 'Health score ... computed by PCA' claim present? false
says composite is disabled?                          true
stale 'baseline not generated' branch present?       false
```

Screenshot saved at `after-run.png` in the session scratchpad. It shows the map view with 0
rendering errors, but does **not** frame the macro-analysis panel — that panel sits in a
side drawer that the scripted toggle did not visibly expand in the headless window. The rect
measurements above are the primary evidence for Change 1, and they are stronger than a
screenshot would be for this specific question.

---

## Concerns

1. **`#impacts-section`'s `class="hidden"` is a pre-existing no-op.** The same missing-`.hidden`-rule
   problem that would have silently defeated Change 1 already affects `#impacts-section`. Browser-confirmed:
   its computed `display` is `block` *before* "Run macro analysis" is ever clicked, so its
   "Node impact multipliers" drawer label is always visible and the five JS call sites that
   `classList.add('hidden')` / `.remove('hidden')` on it have no visual effect. This is
   pre-existing, unrelated to the composite score, and out of scope for a descope commit, so it
   was left alone. Fixing it is a one-line generic `.hidden { display: none }` plus a check of
   those five call sites — worth a separate ticket.

2. **`docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md` is now cited from three
   places** (the `computeCompositeScore` comment, `buildMacroNarrative`'s comment, and the
   user-facing audit log) as holding "the full diagnosis." The pointer text was specified by the
   brief and written as instructed, but whether that plan document actually contains the PCA
   window/loadings diagnosis was not verified as part of this task. Worth confirming the doc
   carries the diagnosis before the branch merges, since one of those three citations is
   user-visible.

3. **The shock path's `tiers: {}` gap** is now documented in-code rather than silent, but it is
   still a real gap: a hypothetical-shock run produces no per-node confidence tiers, unlike the
   real-conditions path. Unchanged by this commit, just no longer invisible.

4. **`BASELINE_STATS` is still generated and embedded** but is now consumed only by
   `computeCompositeScore` (uncalled) and the parity tests. It is dead weight in the shipped
   page until the methodology is revisited. Left intact deliberately, per the brief.
