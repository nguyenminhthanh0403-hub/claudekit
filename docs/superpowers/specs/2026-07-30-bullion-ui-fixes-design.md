# Bullion UI Fixes — Manual-Box Toggle Confirmation + Scenario Highlighting — Design

**Written:** 2026-07-30 · **Status:** approved, ready for `writing-plans`.

## Goal

Fix two UI complaints on the live map (`bullion-live-map/bullion_mk18.html` and
`bullion-live-map/bullion_mkultra.html`):

1. The "Set your own numbers" manual-drivers show/hide toggle "responds but nothing
   happened, no feedback."
2. No scenario control (preset buttons, dropdown) shows which scenario is currently
   active/selected.

## Scope

**In scope:**
- A `setActiveScenario(type)` function and its 3 call sites (see below), in both
  `bullion_mk18.html` and `bullion_mkultra.html`.
- A new CSS rule giving `#scenario-select` a distinct "active" look from the preset
  buttons.
- Verifying (not re-fixing) the manual-box toggle, which was already fixed in commit
  `d225580` earlier this session as part of an unrelated voice-narration pilot push.

**Out of scope:**
- Any redesign of the manual-drivers panel beyond confirming the existing fix works.
- Any change to `triggerShock`'s simulation logic, `resetState`'s reset logic, or
  `runManual`'s validation logic — this effort only adds highlight bookkeeping around
  their existing bodies.

## Root cause (already fixed, verification only)

Before commit `d225580`, `#manual-box.hidden { display: none }` did not exist in the
stylesheet, so the box was always visible regardless of the `hidden` class — clicking
"show" flipped a class with zero visual effect. That rule now exists; live-clicked
verification (real mouse clicks, both files) confirms the toggle correctly shows/hides
the five driver sliders post-fix. No code change is planned here — this effort just asks
the user to confirm on the live site that their original experience is resolved.

## Scenario highlighting

**Current state:** `.btn.active` CSS already exists (`bullion_mk18.html:96`) and is used
elsewhere (e.g. `#mode-toggle-btn`), but nothing wires it to scenario selection. The 5
preset buttons (`bullion_mk18.html:562-566`, `data-shock` attributes) and the
`#scenario-select` dropdown both funnel into `triggerShock(type)`
(`bullion_mk18.html:3527`) via existing listeners (`bullion_mk18.html:3902-3918`).
`resetState()` is at `bullion_mk18.html:3543`; `runManual()` is at
`bullion_mk18.html:4074`, guarded by `manualIsDirty()` (`bullion_mk18.html:2957`).

**New function:**

```js
function setActiveScenario(type) {
  document.querySelectorAll('#control-drawer [data-shock]').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-shock') === type);
  });
  document.getElementById('scenario-select').classList.toggle('active', false);
  // dropdown gets 'active' only when `type` matches its own current value below
}
```

Exact matching logic: the dropdown is marked active when `type` is non-null and equals
`document.getElementById('scenario-select').value` at call time (so a preset-button
click does not also light up the dropdown unless the dropdown happens to hold the same
value); the 5 buttons are marked active when their own `data-shock` equals `type`. When
`type` is `null`, everything is cleared.

**Call sites (no new event listeners — inserted into 3 existing functions):**
- Inside `triggerShock(type)`: call `setActiveScenario(type)` (covers both preset-button
  clicks and dropdown-select + Run, since both already funnel through this function).
- Inside `resetState()`: call `setActiveScenario(null)` — Reset clears any highlight.
- Inside `runManual()`, in the `manualIsDirty()` branch: call `setActiveScenario(null)` —
  entering manual mode clears any preset/dropdown highlight.

**CSS:**

Buttons keep the existing `.btn.active` rule (`bullion_mk18.html:96`,
`background: rgba(212,184,105,0.15); border-color: var(--gold-dim); color: var(--gold);`)
unchanged.

The dropdown gets a **new, deliberately different-colored** treatment per explicit user
choice (a plain gold outline was rejected in favor of a genuinely distinct hue), using a
new CSS custom property alongside the existing `--gold`/`--green`/`--red`/`--amber` in
`:root` (`bullion_mk18.html:24-38`):

```css
:root {
  /* existing vars unchanged */
  --scenario-active: #8b0000; /* deep blood-red, deliberately darker/more saturated
                                  than the existing --red (#e0654f, used for negative
                                  shock direction) so the two are not visually confused */
}

select.scenario-select.active {
  border-color: var(--scenario-active);
  box-shadow: 0 0 0 2px rgba(139,0,0,0.35);
}
```

Note on the color choice: `--red` (`#e0654f`) already carries a fixed semantic meaning
(negative/"down" shock direction) elsewhere in the UI. `--scenario-active` is a
deliberately darker, more saturated red chosen so it reads as a distinct marker rather
than a duplicate of the existing negative-direction indicator — this was flagged to the
user during design and confirmed as an acceptable, intentional tradeoff (chosen over the
alternative of picking a non-red hue).

Same CSS and JS changes are mirrored in both `bullion_mk18.html` and
`bullion_mkultra.html`.

## Error handling

- `setActiveScenario` operates purely on DOM classList state — there is no failure mode
  beyond the elements not existing, which cannot happen since `#control-drawer
  [data-shock]` and `#scenario-select` are static markup present in both files.
- No new error states are introduced; this is additive class-toggling on existing,
  always-present elements.

## Testing

- **Manual, real Chrome:** click each of the 5 preset buttons, select+Run the dropdown,
  click Reset, and use the manual sliders — confirm exactly one control (or none) shows
  the active highlight at any time, in both `mk18.html` and `mkultra.html`.
- **Headless-Chrome DOM probe** (isolated `--user-data-dir`, per project convention):
  script through `triggerShock('rate_hike')`, `resetState()`, and a manual-driver change,
  asserting `classList.contains('active')` transitions correctly across all 6 controls
  (5 buttons + dropdown) at each step.
- Confirm with the user, separately and not blocking, that the manual-box toggle fix
  resolves their original complaint on the live site.
- **Freeze-check:** `bullion_mk11.html`–`bullion_mk17.html` unchanged via
  `shasum -a 256` (this effort only touches `mk18` and `mkultra`).
- **Python suite:** `cd bullion-live-map && python3 -m unittest discover -s tests &&
  python3 -m unittest test_calibrate` — unrelated to this change but cheap to re-run per
  project convention.

## Risks / unverified

- Whether the manual-box toggle fix actually resolves the user's original experience —
  verified so far only via automation, not yet confirmed by the user on the live site.

## Explicitly not building

- Any change to which scenarios exist, their simulation math, or the manual-driver
  validation logic.
- Any animation/transition on the highlight beyond a plain CSS state change.
- Any highlighting for the manual-drivers panel itself (only the 5 presets + dropdown
  are in scope).
