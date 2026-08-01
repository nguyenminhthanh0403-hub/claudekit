# Bullion Persona Orb — Translucency + Custom Icons — Design Spec

**Written:** 2026-08-01 · **Supersedes:** nothing — this is a follow-up restyle of the
already-shipped persona orb (`docs/superpowers/specs/2026-08-01-bullion-persona-orb-design.md`,
see `bullion-persona-orb-shipped-handoff.md` for that feature's full history). That feature
is done and live; this spec covers two purely visual changes to it requested after the user
eyeballed the live orb.

## Goal

Two changes to `#persona-orb` in both `bullion_mk18.html` and `bullion_mkultra.html`:

1. **Turn the orb's resting opacity down** to match the map's own translucent-node look
   (nodes rest at `NODE_BASE_OPACITY = 0.4`), instead of its current near-full-opacity
   idle state.
2. **Replace both persona emoji** (🎩 Alfred, 👹 Johnny) **with custom SVG glyphs**,
   rendered as translucent filled shapes rather than solid emoji — Johnny's evoking an
   angular samurai/kabuto mark (in the spirit of his in-fiction "Samurai" band, *not* a
   reproduction of CD Projekt Red's actual trademarked logo), Alfred's a companion mark in
   the same visual language reading as butler/gentleman.

## Non-goals

- No change to orb positioning, panel-open repositioning, the nudge tooltip, or narration
  sync logic (`setOrbNarrating`, per-word pulsing) — those are working and out of scope.
- No change to the parked narration-overlap bug from the prior handoff — untouched here.
- Not reproducing CD Projekt Red's actual "Samurai" band logo asset — see below.

## Design

### A. Opacity model

Scope: **`.orb-core` only** (the circle + glyph). `.orb-label` (the "Alfred"/"Johnny" text
underneath) stays fully legible — the map's own node labels aren't translucent either, only
the node bodies are, so this mirrors that convention.

| State | Current | New |
|---|---|---|
| Idle breathe low point | `opacity: 0.75` | `opacity: 0.4` (matches `NODE_BASE_OPACITY`) |
| Idle breathe high point | `opacity: 1` | `opacity: 0.65` (keeps the existing ~0.25 swing) |
| Hover / keyboard-focus | *(no explicit rule — inherits idle)* | `opacity: 1 !important` — needs `!important` to win over the running `orbBreathe` keyframe animation; standard/expected CSS behavior, not a hack. |
| `.active` (narration playing) | *(no explicit rule — inherits idle breathe/pulse)* | `opacity: 1` for the whole clip, not just per-word pulse blips. `.idle`/`.active` are already mutually exclusive via `setOrbNarrating()`'s `classList.toggle`, so no animation conflict here — plain non-`!important` opacity is enough. |

```css
#persona-orb.idle .orb-core { animation: orbBreathe 3.6s ease-in-out infinite; }
@keyframes orbBreathe {
  0%, 100% { transform: scale(1);    opacity: 0.4;  }
  50%      { transform: scale(1.12); opacity: 0.65; }
}
#persona-orb.active .orb-core { opacity: 1; }
#persona-orb:hover .orb-core,
#persona-orb:focus-visible .orb-core { opacity: 1 !important; }
```

Add a one-line code comment at the `0.4` value noting it's intentionally matching
`NODE_BASE_OPACITY` (defined far away, in the THREE.js section) — same pattern this file
already uses elsewhere for cross-referenced constants (e.g. the sibling-combinator DOM-order
comment from the last orb session).

### B. Icon glyphs

Both replace the current `<span class="orb-icon">` emoji `textContent` with an inline
`<svg>` swapped via `innerHTML` in `toggleNarrationPersona()` (currently line ~4186,
`orb.querySelector('.orb-icon').textContent = isJohnny ? '\u{1F479}' : '\u{1F3A9}'`) — and
the HTML markup's initial Alfred icon (currently the `&#127913;` emoji at line ~675).

Shared treatment: `viewBox="0 0 24 24"`, `fill="#fff"`, `fill-opacity="0.55"` on every path
(the "frosted glass over the gradient" look — semi-transparent filled silhouette, not
outline/stencil, not solid). `aria-hidden="true"` on the `<svg>` root since `#persona-orb`
already carries the real accessible name via its `aria-label`.

**Johnny — angular kabuto/samurai mon** (original design, not CDPR's actual "Samurai" logo):
a diamond crest above a hexagonal angular face-guard, split by a faint center seam for a
faceted/glitchy read.

```html
<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
  <path d="M12 2 L15.5 5.5 L12 9 L8.5 5.5 Z" fill="#fff" fill-opacity="0.55"/>
  <path d="M6 8 L18 8 L20 13 L15.5 22 L8.5 22 L4 13 Z" fill="#fff" fill-opacity="0.55"/>
  <path d="M12 8 L12 22" stroke="#fff" stroke-width="1" stroke-opacity="0.3" fill="none"/>
</svg>
```

**Alfred — top hat + cane**, same flat/angular language, reading as gentleman/butler:

```html
<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
  <path d="M7 15 L17 15 L17 17 L7 17 Z" fill="#fff" fill-opacity="0.55"/>
  <path d="M9 6 L15 6 L15 15 L9 15 Z" fill="#fff" fill-opacity="0.55"/>
  <path d="M9 8.5 L15 8.5 L15 9.5 L9 9.5 Z" fill="#fff" fill-opacity="0.35"/>
  <path d="M17.5 16 L20.5 20 L19 22" stroke="#fff" stroke-width="1.4" stroke-opacity="0.55" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

These path coordinates are the starting design, not pixel-final — refine proportions in
place during implementation using live screenshots (this project's established visual-QA
idiom for anything CSS/shape-related; see the memory note on why `getComputedStyle()` reads
aren't trustworthy for this kind of check). Both files must end up byte-identical in the
touched regions, matching this project's standing convention for `bullion_mk18.html` /
`bullion_mkultra.html` parity.

`.orb-icon`'s CSS (`font-size: 24px; line-height: 1;`) becomes sizing for the `<svg>` child
instead: `.orb-icon svg { display: block; width: 24px; height: 24px; }`.

### C. Implementation notes

- Files: `bullion-live-map/bullion_mk18.html`, `bullion-live-map/bullion_mkultra.html` —
  identical changes in both, as with every prior orb change.
- `toggleNarrationPersona()`'s icon swap changes from `.textContent = <emoji>` to
  `.innerHTML = <svg markup>`.
- Pure CSS/markup/one-function change — no new state, no data flow, no architecture impact.
  Does not touch narration sync, positioning, or the parked overlap bug.
- Python test suite unaffected (pure front-end change, same as the parent orb feature).

## Verification plan

- Visual: screenshot both files, both personas, in idle (breathing, low opacity), hover
  (brightened), and `.active`/narrating (brightened) states — confirm the 0.4/0.65/1.0
  opacity levels read as intended and the new glyphs render legibly at 24px.
- Structural: confirm `bullion_mk18.html` and `bullion_mkultra.html` stay byte-identical in
  every touched region.
- Regression: re-run the Python suite (96/96 expected, unaffected) to confirm no accidental
  cross-contamination — same idiom as every prior front-end-only orb change.
- Final human check: the user's own live-browser look, same standing limitation noted in
  the parent feature's handoff (automation can't judge "does this look right" for
  visual/motion polish).
