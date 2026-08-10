# Bullion Mk Ultra — identity-pass polish (P1s) — design

**Date:** 2026-08-06
**Status:** approved, not yet implemented
**Origin:** `/impeccable critique` dual-agent audit of `bullion-live-map/bullion_mkultra.html`'s
Spec 2 editorial identity pass, snapshot at
`.impeccable/critique/2026-08-06T12-49-55Z__bullion-live-map-bullion-mkultra-html.md`
(Design Health Score 27/40). Scope for this pass: the three P1 findings only, chosen by the
user over the two P2s (WebGL-fallback/orb overlap, field-note discoverability), which are
deferred, not rejected.

## Problem

The critique found the Spec 2 identity pass (wordmark, palette, cursor, field notes, WebGL
fallback — all implemented per `docs/superpowers/plans/2026-07-28-bullion-mkultra-experience.md`)
is real and specific to this project, but three things were designed and never fully delivered
or verified:

1. **The signature cursor never renders.** It's dead code — present in CSS, overridden at
   runtime by JS on every pointer move.
2. **Text runs undersized site-wide.** A live-rendered detector scan found 224 of 241
   anti-pattern hits are `tiny-text`/`undersized-ui-text`, down to 9px.
3. **The palette isn't color-blind-safe**, despite an earlier pass that re-spaced it
   specifically to fix crowding. Two pairs still collapse under deuteranopia.

All three are refinements to what already shipped — no new features, no visual redesign.

## Design

### Fix 1 — Compass-rose cursor

**Root cause** (confirmed in source): `#mkultra-canvas` (bullion-live-map/bullion_mkultra.html
lines 146-149) already defines the correct cursor —

```css
#mkultra-canvas { cursor: url("data:image/svg+xml,...compass...") 12 12, grab; }
#mkultra-canvas:active { cursor: url("data:image/svg+xml,...compass-filled...") 12 12, grabbing; }
```

— but `onPointerMove()` (line 2222) runs on every mouse move and does:

```js
canvas.style.cursor = id ? 'pointer' : 'grab';
```

An inline `style.cursor` always beats a stylesheet rule for the same element, `:active`
included, so the compass SVG has never actually painted since this shipped.

**Fix:** change that one line (and add the pointerdown/pointerup pair) so the JS sets the exact
same values the CSS already defines, instead of the bare keywords:
- hover-over-a-node: `'pointer'` (unchanged — this part was already correct)
- hover-over-empty-space: the compass-grab data-URI string (currently only in the CSS `cursor`
  rule)
- pointerdown (dragging): the compass-grabbing data-URI string, reverted to grab on pointerup

No new assets — both data-URIs already exist in the CSS block above; this fix copies them into
the two JS branches. The `#mkultra-canvas:active` CSS rule becomes dead code once JS sets the
cursor explicitly on every state change and can be left in place harmlessly or removed for
clarity — implementer's call, not load-bearing either way.

### Fix 2 — Site-wide undersized text (split treatment)

30+ CSS rules currently sit at 8-10.5px. These fall into two categories that get different
treatment, not one blanket floor:

**Reading content → 11-12px floor.** Text a visitor reads sentence-by-sentence: tooltip/glossary
definitions (`.gterm::after`, currently 10.5px), relationship detail stats (`.rel-detail
.rel-stat`, 10.5px), scenario/manual explainer copy (`.scenario-explain`, `.manual-intro`, both
10.5px), and any other rule in this category found during implementation. These move to at least
11px (12px preferred where the surrounding rhythm allows without visibly disrupting layout).

**Micro-labels stay compact, but get a smaller bump.** Uppercase, tracked-out, all-caps
eyebrows/badges/tags — `.metric-label`, `.metric-sub`, `.tier-badge`, `.audit-badge`,
`.stat-label small`, `.rel-strength`, and similar — are a deliberate compact-density UI
convention in this data-dense app, not a legibility failure on their own. These get a smaller
bump (e.g. 8px→9px, 9px→10px) rather than jumping to the reading-content floor, preserving their
current visual character and density. Do not enlarge these to 11-12px — that would visibly
crowd the already-dense Advanced/Tools header and card layouts without fixing a real readability
problem.

**Boundary calls during implementation:** a rule that's ambiguous between the two categories
(e.g. `.sim-note`, `.stats-foot`, `.manual-warn` — short but sentence-length warning/caveat text,
currently 9-10px) should default to the reading-content floor, since these carry real
information a visitor is meant to read, not just scan as a tag.

No rule should end up below 9px after this pass, and no previously-9px+ micro-label rule should
be *reduced* — this is a floor-raising pass only.

### Fix 3 — Color-blind-safe palette (re-hue, not a new signal system)

Two `GROUP_COLOR` pairs (`bullion-live-map/bullion_mkultra.html` line 912) collapse under
deuteranopia simulation despite reading distinctly for typical vision:

- `sovereign: '#6fa2d1'` vs `monetary: '#ab93d4'` — ΔE≈3.2 simulated
- `sectors: '#e0926a'` vs `indicator: '#9cc26a'` — ΔE≈4.0 simulated

**Approach:** re-hue these four swatches only, same technique as the prior "fix crowded
purples/blues and the gold collision" pass (`cf43c4d`) — adjust hue/lightness to widen
perceptual distance, verified this time under *both* normal vision and a deuteranopia
simulation, not normal vision alone (the gap that let this slip through last time).

**Target:** every pair among the 12 `GROUP_COLOR` values should read as distinguishable
(ΔE ≳ 10 in Lab space, the threshold Assessment A used) under a deuteranopia simulation, not
just normal vision. The other 8 swatches are not known to have a problem and should only change
if re-hueing the 4 flagged ones creates a *new* collision with one of them — check the full
12×12 pairwise matrix after any change, not just the 2 flagged pairs in isolation.

**Explicitly out of scope for this pass:** adding a non-hue identity signal (icon, ring pattern,
letterform) to the legend/nodes/cards. That's a more robust long-term fix but touches
significantly more UI surface than a polish pass — worth reconsidering if the palette ever needs
to grow past 12 groups.

**Unverified-until-rendered, same caveat as the original palette pass:** hand-picking hex values
by ΔE math is a first draft, not a final answer — the implementation step must actually render
the legend (both normal and a deuteranopia-simulated screenshot) and confirm the new values read
as distinguishable in practice, with explicit room to adjust if they don't.

## Testing / verification approach

- **Cursor:** headless-Chrome screenshot capturing hover-empty-space, hover-node, and
  mid-drag(pointerdown) states; confirm the compass SVG (not `grab`/`pointer` keyword) is the
  active cursor at each.
- **Text sizes:** grep sweep of every `font-size` rule touched, confirming reading-content rules
  are ≥11px and micro-label rules moved up but stayed below the reading-content floor; visual
  screenshot of the Tools header and a node detail card to confirm no new crowding.
- **Palette:** legend screenshot in normal rendering, plus a deuteranopia-simulated render
  (same method Assessment A used) confirming all 12 swatches are pairwise distinguishable.
- No Python/unit-test suites are affected — this pass is CSS/JS-only inside one file
  (`bullion_mkultra.html`); the standard freeze-check (`bullion_mk11`-`mk17` untouched) still
  applies since this file is one of the two live/mutable maps.

## Deferred (not rejected)

The two P2 findings from the same critique — the WebGL-fallback card getting covered by the
persona orb, and the field notes being undiscoverable (2 of 250+ links, no signifier) — are
explicitly out of scope for this pass by user choice, not because they're lower-value. Revisit
in a follow-up pass; the critique snapshot above has full detail on both.
