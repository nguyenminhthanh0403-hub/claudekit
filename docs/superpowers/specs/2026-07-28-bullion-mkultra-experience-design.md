# Bullion Mk Ultra — Experience Pass (Spec 2, Editorial Identity) — Design

**Status:** Approved by user, ready for planning · **Date:** 2026-07-28 · **Target file:**
`bullion-live-map/bullion_mkultra.html` ONLY — no other version file is touched.

## Context

Spec 1 (the "honesty pass," see `docs/superpowers/honesty-pass-handoff.md`) shipped the
trustworthiness/evidence-tier work as `bullion_mk18.html`. That handoff scoped a follow-up
**Spec 2 — "the Mk Ultra experience pass"** with four parts: (a) beginner legibility, (b) visual
elevation via the `impeccable`/`frontend-design`/`ui-ux-pro-max` skills, (c) motion polish, (d) a
WebGL/CDN fallback (Mk Ultra currently renders a silent black void when WebGL is unavailable or
the Three.js CDN is blocked).

This spec covers **only (b) visual elevation, plus signature personal-touch details, plus (d)
the WebGL/CDN fallback**. (a) beginner legibility and (c) motion/micro-interaction polish are
explicitly deferred to a separate future spec, as is a voice-narration-with-captions feature
raised during brainstorming (also deferred — see "Explicitly out of scope" below).

**Why now:** the user wants Mk Ultra to stop reading as a generic AI-generated dark-fintech
template and start reading as something a person deliberately designed, with a personal
identity and voice tied to their own experience building it — not just "prettier."

## Approach

Of three approaches proposed (A: editorial identity pass, B: component-by-component craft pass
keeping the system font, C: full masthead rebrand with sidebar navigation), the user chose
**Approach A**. It's scoped to typography, color, a header/brand mark, a couple of authored
personal-touch details, and the WebGL fallback — no layout or navigation restructuring (that
was Approach C, declined).

## Design

### 1. Typography

**Times New Roman for every header/title in the app.** This was revised mid-brainstorm from an
initial self-hosted-Fraunces proposal — the user explicitly asked for Times New Roman, applied
everywhere a heading/title appears, not just the wordmark. Because it's a system font, this
requires **no new font assets, no `.woff2` hosting, and no CSP change** (the earlier
`bullion-live-map/fonts/` plan is dropped entirely).

Apply `font-family: "Times New Roman", Times, serif` to:
- `<h1>` (line ~511) — the header wordmark/title
- `#detail-title` (CSS ~184, markup ~545) — node-detail panel title
- `#coach-title` / `<h3 id="coach-title">` (CSS ~282, markup ~534) — guided-tour step heading
- `.legend-causal-title` (~2729, 2734, 2740) — the "Link effect" / "Evidence" / "Layers (tap to
  filter)" section headers in the legend
- All other `<h2>`/`<h3>` elements in dynamically-generated panels (Audit Log's `<h2>Audit
  Log</h2>` at ~4334, its `<h3>` sub-headings ~4266-4334, and `<h3 id="disclaimer-heading">` at
  ~4934) — apply via a general `h1, h2, h3, .legend-causal-title, #detail-title, #coach-title`
  selector rather than hunting down every generated string individually.

Body copy, buttons, live-data numbers, and tabular/dense UI (`.btn`, tables, the metrics grid)
**keep the existing system sans stack** (`-apple-system, BlinkMacSystemFont, "Segoe UI",
Roboto, sans-serif`) — Times New Roman is a headings-only treatment; using it for dense data
would hurt tabular-number legibility.

**Execution note carried from brainstorming:** lean editorial-masthead (tight kerning, confident
size/weight for the h1) rather than default-Word-document — the risk with Times New Roman is
under-executing it so it reads as "no font chosen" rather than "chosen deliberately."

### 2. Color Palette

**Problem (grounded in the actual file):** `GROUP_COLOR` (`bullion_mkultra.html:697-710`)
currently has:
```
monetary:   #b79be0   commercial: #8f9ee0   shadow:     #b586c8
sovereign:  #7fb4e0   fx:         #8fb0c8
```
Five of the twelve swatches crowd two adjacent hue families (purple and blue), which is why the
legend reads as noise rather than information — this was flagged directly in the honesty-pass
handoff's "observed problems" list.

**Fix approach:**
- Re-space the 12 `GROUP_COLOR` values around the hue wheel so no two groups that appear
  adjacent in the legend sit within roughly 25° of hue of each other. Concretely: keep
  `monetary` as the anchor purple (it's the Central Bank / most-important group); move
  `commercial` toward a warm rust/copper (ties into the gold accent family instead of competing
  with purple); move `shadow` toward a cooler teal-slate; keep `sovereign` blue but shift `fx`
  toward a sandy blue-green so the two are no longer near-identical.
- Desaturate the full 12-color set by roughly 8-12% and warm the midtones a few degrees, to move
  away from a default D3-categorical-scheme look and tie into the tactile, less-flat background
  direction.
- `--gold` (`#d4b869`) stays the singular accent color (live-data highlights, hub nodes, the
  wordmark) — none of the 12 group colors should be tuned close enough to it to dilute it.
- Final 12 hex values are a hand-picked, eyeballed pass against the existing gold/navy base
  (checked for at-a-glance distinguishability), not an algorithmically generated palette — do
  this during implementation, not automated in the plan.

### 3. Header / Brand Mark

Currently the header is a plain `<h1>US Financial System — Mk Ultra Constellation</h1>` with no
mark — while `bullion-live-map/preview-card.png` (the social share card) already established a
Georgia-serif "Bullion" wordmark that nothing inside the app itself echoes.

- Promote **"Bullion"** into the in-app header as the primary wordmark (now in Times New Roman
  per Section 1), with the existing descriptive text (`US Financial System — Mk Ultra
  Constellation`) demoted to a subtitle/eyebrow line underneath — mirroring the share-card
  identity instead of contradicting it.
- Add a **minimal constructed monogram** to the left of the wordmark: a small inline SVG built
  from 2-3 arcs (echoing the orbit/constellation visual language already in the 3D globe),
  rendered in the gold accent. Not an illustrated icon or gradient badge — restrained enough
  that it could sit on a business card. No asset pipeline needed (inline SVG).
- **Scope boundary:** header markup/CSS only. The existing button row (`3D Map` / `Overview` /
  `Controls` / `Live Data` / etc.) is not restructured — it may pick up incidental type/spacing
  refinement as a side effect of the new type system, but no navigation redesign (declined
  Approach C).

### 4. Signature Personal-Touch Details

Two elements:

**a) Field-note annotations.** On 2-3 links where the honesty pass's calibration corrected a
sign the user had originally hand-coded from textbook intuition, add a short first-person
marginal note in the node-detail panel, visually distinct from the sourced `stat:`/`note:`
fields (Times New Roman italic, with a small distinguishing mark — e.g. an underline or
asterisk treatment. Exact styling decided during implementation, not prescribed here).

Confirmed candidates (from `docs/superpowers/honesty-pass-handoff.md`'s "4 arrows flipped"
list) and starting draft copy — **the user will supply/edit the final wording, these are
placeholders**:
- `usd→oil` (originally coded dollar-up-means-oil-down; the fitted data over the training
  window showed the opposite sign): *"I had this coded as dollar up → oil down — the textbook
  FX-pricing story everyone learns. The data disagreed. Over this window it's actually
  positive. I'm leaving that in and telling you it's weird rather than hiding it."*
- `credit→equit` (originally coded wider credit spreads lifting stocks; t=12.5 measured the
  opposite): *"I originally had wider credit spreads lifting stocks — which, looking back,
  never made sense. Once I actually measured it, spreads widening tracks equities falling, the
  way you'd expect."*
- A third candidate (`mortgage→credit` or `vix→defn`, both also flipped per the honesty-pass
  handoff) may be added if the user wants a third note; not required.

**b) Signature interaction — compass cursor.** The 3D globe currently has no affordance showing
it's drag-to-spin (a real gap, flagged in the honesty-pass handoff's "observed problems" list).
Add a custom cursor/hover state over the globe: a small hand-drawn compass-rose icon replacing
the default arrow cursor on hover. This simultaneously fixes a real discoverability problem and
reads as a deliberate crafted detail (a custom cursor isn't something a template ships with).

### 5. WebGL / CDN Fallback

**Current failure mode:** on a device without WebGL, or if the pinned jsDelivr Three.js CDN is
blocked (locked-down in-app browsers, corporate networks), Mk Ultra renders a silent black
void — no error, no explanation. This is the single worst "looks broken, not intentional" tell
in the app, and was explicitly flagged as an open item in the honesty-pass handoff.

**Fix:**
- **Detect early**, before the Three.js import runs: a cheap `canvas.getContext('webgl2')`
  probe.
- On failure (or on a timeout waiting for the Three.js ESM module to load from jsDelivr — same
  fallback path for both a missing-WebGL device and a blocked CDN), show an explanatory card in
  the app's own voice (Times New Roman heading, consistent with the rest of the redesign):
  something like *"This view needs 3D graphics your browser isn't giving us. Here's the same
  map, flattened."* — with a button dropping into the existing 2D `#board-view` (Overview
  board), which already shares the same underlying node data and `openDetail()` function, so no
  new data plumbing is needed.

### 6. Testing / Verification

Lighter than the honesty pass's test suite, since this pass adds no new data or backend logic:

- **Visual verification in Chrome MCP** (this project's standing idiom) for each piece: header/
  wordmark render, palette legend distinguishability, field-note panel styling, compass-cursor
  hover state, and the WebGL-fallback card. Standard bar: 0 console errors, screenshot-checked.
- **Headless-probe check for the fallback path** specifically, since it's the one piece with
  real conditional logic. Run the project's existing headless-Chrome probe idiom (see
  `docs/superpowers/honesty-pass-handoff.md`'s "Verification idioms" section) twice:
  - **With** `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader` → confirms the
    normal 3D path still renders correctly.
  - **Without** those flags, and/or with the jsDelivr host blocked in the probe copy (hosts-file
    or CSP override in the temp copy only) → confirms the fallback card appears instead of a
    blank canvas.
- **Freeze check unchanged:** `shasum -a 256 bullion_mk15.html bullion_mk16.html
  bullion_mk17.html bullion_mk18.html` before and after — this pass touches
  `bullion_mkultra.html` only, nothing else.
- **No Python test changes needed.** Nothing in this pass touches `calibrate.py`,
  `fetch_bullion_data.py`, or `data.json` — the existing 41/33 test counts are unaffected;
  confirm they still pass as a sanity check, no new tests required for this pass itself.

## Explicitly out of scope (deferred to future specs)

- **(a) Beginner legibility** (progressive disclosure, plain-English jargon tooltips, guided
  first-run tour of 3 scenarios) — deferred to a follow-up spec, per user decision during
  brainstorming.
- **(c) Motion / micro-interaction polish** — deferred to the same follow-up spec.
- **Voice narration with captions.** Raised during brainstorming (narrating scenarios in the
  user's voice, with a captions UI). This is materially bigger than a "signature detail" — it
  needs its own design pass covering method (recorded audio needing production + same-origin
  hosting, vs. browser TTS via the Web Speech API needing no new assets), which scenarios get
  narrated, and captions styling. User explicitly chose to defer this to its own spec rather
  than fold it into this one.
- **Mk18 (the 2D shared map)** is not touched by this spec. Any visual-identity elements that
  prove out well in Mk Ultra (e.g. the wordmark/monogram) are a candidate for a *separate*,
  explicitly-scoped future decision — not an automatic port.

## File impact summary

| File | Change |
|---|---|
| `bullion-live-map/bullion_mkultra.html` | All changes: typography (CSS + selector additions), `GROUP_COLOR` palette values, header markup (wordmark + inline SVG monogram), field-note content/styling in the node-detail panel, compass-cursor CSS, WebGL-detection + fallback-card logic and markup. |
| `bullion-live-map/preview-card.png` | Unchanged — referenced as the existing wordmark identity to extend, not modified. |
| All other version files (`bullion_mk11..18.html`) | Unchanged — frozen, verify via `shasum -a 256` before/after. |
