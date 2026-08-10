# Bullion Persona Orb — Header Toggle Replacement — Design

**Written:** 2026-08-01 · **Status:** approved, ready for `writing-plans`.

**Builds on:** `2026-07-31-bullion-voice-persona-toggle-design.md` (the toggle/captions/
autoplay work, Tasks 1-6 of that plan, code-complete). This spec covers only the
**visual replacement** of that plan's header `#persona-toggle-btn` with a persistent
floating orb — no changes to persona resolution, fallback, caption timing, or autoplay
logic, all of which are reused as-is.

**Not blocked on:** the open `say`-CLI voice-quality question (see
`docs/superpowers/bullion-voice-persona-toggle-and-orb-handoff.md`, "What has failed").
The user chose to proceed with this UI work independently — the per-word sync hook this
spec adds works identically regardless of which TTS engine eventually produces the audio.

## Goal

Replace the small header button (`#persona-toggle-btn`, `bullion_mk18.html` +
`bullion_mkultra.html`) with a persistent floating orb, bottom-right corner, present
identically in both files. Always visible; shows the active persona's name/icon/color;
breathes gently at rest; pulses per spoken word during narration; click toggles persona
(same `narrationPersona` state/`localStorage` key the existing toggle already uses — no
new state surface). Default persona stays **Alfred** (Alfred covers all 39 nodes, Johnny
only 6 — unchanged from the existing toggle's default).

## Component markup

Static markup, inserted as a sibling near `#legend-box` (`#legend-box` is bottom-**left**,
`left:12px; bottom:12px`, `z-index:10` — the orb sits at the mirror position,
bottom-**right**, so the two never overlap):

```html
<div id="persona-orb" title="Switch narration voice" class="idle"
     role="button" tabindex="0" aria-label="Switch narration voice, currently Alfred">
  <div class="orb-core"><span class="orb-icon">&#127913;</span></div>
  <div class="orb-label">Alfred</div>
</div>
```

The persona emoji lives in `.orb-icon`, inside `.orb-core` — `.orb-core` carries the
breathing/pulse animations and the per-persona gradient background (see "Icons / colors"
below), `.orb-icon` is the text glyph layered on top, `.orb-label` is the separate
name text underneath. `role="button"` + `tabindex="0"` + `aria-label` (kept in sync by
`applyPersonaToggle()`, see "Removal" below) match this project's existing convention for
custom interactive elements that aren't native `<button>`s — node dots
(`tabindex="0"` + `aria-label`), `#coach-dismiss`/`#drawer-close`
(`aria-label`). A `keydown` handler for Enter/Space is required alongside the `click`
listener in "Click → toggle persona" below, since a `div[role=button]` gets no native
keyboard activation.

```css
#persona-orb {
  position: fixed; right: 18px; bottom: 18px; z-index: 15;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  cursor: pointer; transition: transform 0.28s ease;
}
```

`z-index: 15` — above `#stage`/`#legend-box` (10), below `#detail-panel` (20), matching
the existing panel-vs-content stacking order already in use.

## Icons / colors

- **Alfred:** 🎩 (top hat emoji, plain Unicode glyph — matches this project's existing
  icon convention of plain emoji rather than hand-drawn SVG, e.g. 🎤/⚙/◉ used elsewhere).
  New blue gradient — no `--blue` token exists in either file's `:root` today (only
  `--gold`/`--gold-dim`/`--green`/`--red`). Add one alongside them:
  ```css
  --blue:     #4d7fb8;
  --blue-dim: #24425e;
  ```
  (Palette values from the approved brainstorm mockup: light `#9fc6f5` → mid `#4d7fb8` →
  dark `#24425e`; only mid/dark become named tokens, matching how `--gold`/`--gold-dim`
  are the only two gold shades tokenized today — the light shade stays a literal in the
  gradient stop, same pattern `--gold`'s glow effects already use.)
- **Johnny:** 👹 (Japanese Oni emoji), red gradient reusing the existing `--red: #e0654f`
  token — no new red token needed.
- A hand-drawn custom-SVG "butler face" (monocle + mustache) alternative was mocked
  during the brainstorm and explicitly **not** chosen.

Gradient applied to `.orb-core`'s `background`, keyed by a `persona-alfred`/
`persona-johnny` class on `#persona-orb` that `applyPersonaToggle()` toggles (see
"Removal" below):

```css
#persona-orb.persona-alfred .orb-core {
  background: radial-gradient(circle at 35% 30%, #9fc6f5, var(--blue) 55%, var(--blue-dim));
}
#persona-orb.persona-johnny .orb-core {
  background: radial-gradient(circle at 35% 30%, #f2a08f, var(--red) 55%, var(--red-dim, #7a2e1f));
}
```

`--red-dim` does not exist today (only `--red`) — add it alongside `--blue`/`--blue-dim`
above, same reasoning: a dark stop for the radial gradient's outer edge, matching the
two-shade-per-color pattern `--gold`/`--gold-dim` already establishes.

## States

Two CSS states, `.idle` and `.active`, toggled by adding/removing `.active` on
`#persona-orb` (JS hook below):

```css
#persona-orb.idle .orb-core { animation: orbBreathe 3.6s ease-in-out infinite; }
@keyframes orbBreathe {
  0%, 100% { transform: scale(1);    opacity: 0.75; }
  50%      { transform: scale(1.12); opacity: 1;    }
}
#persona-orb.active .orb-core.pulse { animation: orbPulse 0.32s ease-out; }
@keyframes orbPulse {
  0%   { transform: scale(1);   box-shadow: 0 0 0 0 currentColor; }
  60%  { transform: scale(1.22); box-shadow: 0 0 0 10px transparent; }
  100% { transform: scale(1);   box-shadow: 0 0 0 0 transparent; }
}
```

`.idle`'s 3.6s period intentionally does not match `hubPulse`'s existing 3.2s (nodes'
breathing halo) — close enough to feel like the same visual language (a slow scale+fade
loop) without literally syncing two unrelated elements' animations, which would imply a
connection that doesn't exist. `.active`'s pulse is a **single retriggerable animation**
(add `.pulse`, force reflow, remove `.pulse`), not a fixed-interval loop — see "Narration
sync" below for exactly when it fires.

## Narration sync

Reuses the **existing** per-word `setTimeout` schedule already in `startCaption()`
(`bullion_mk18.html:3402-3419`, identical in `bullion_mkultra.html`) — no second timer
system. Inside the existing per-word callback (`bullion_mk18.html:3414-3417`, where
`wordsHost.textContent = shown` already runs), add one line to retrigger the pulse:

```js
words.forEach(function(word, i) {
  const wordDuration = (word.length / totalChars) * duration;
  captionTimeouts.push(setTimeout(function() {
    shown += (i > 0 ? ' ' : '') + word;
    wordsHost.textContent = shown;
    pulseOrb();                          // new
  }, elapsed * 1000));
  elapsed += wordDuration;
});
```

```js
function pulseOrb() {
  const core = document.querySelector('#persona-orb .orb-core');
  if (!core) return;
  core.classList.remove('pulse');
  void core.offsetWidth;   // force reflow so the animation retriggers
  core.classList.add('pulse');
}
```

`#persona-orb` gains `.active` (loses `.idle`) at the **top of `startCaption()`**, and
loses `.active` (regains `.idle`) inside `clearCaption()` — the same two functions that
already gate captions, so narration state has one single source of truth ("is anything
narrating") rather than a parallel state machine. `clearCaption()` already runs on panel
close (`bullion_mk18.html:2015`/`2018`-adjacent), on opening a different node
(`:1967`), and at the top of every `playNarration()` call (`:3422`) — the orb's idle/
active transitions ride along automatically with no new call sites needed. Natural
completion (the clip finishes playing on its own, panel still open) is **not** covered by
any of those three call sites, so it's handled separately via a `setOrbNarrating(false)`
call from the audio element's `ended` event — deliberately not `clearCaption()`, since
that would also wipe the caption text, which should stay visible after a clip finishes
rather than vanish along with the orb's motion state.

## Click → toggle persona

```js
function toggleNarrationPersona() {
  narrationPersona = narrationPersona === 'alfred' ? 'johnny' : 'alfred';
  localStorage.setItem('bullion-narration-persona', narrationPersona);
  applyPersonaToggle();
  dismissOrbNudge();
}
const orbEl = document.getElementById('persona-orb');
orbEl.addEventListener('click', toggleNarrationPersona);
orbEl.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleNarrationPersona(); }
});
```

Same `narrationPersona` variable and `'bullion-narration-persona'` `localStorage` key the
existing button already reads/writes (`bullion_mk18.html:3434-3446`) — `applyPersonaToggle()`
is repurposed (see "Removal" below) rather than duplicated. The `keydown` handler exists
because `#persona-orb` is a `div[role=button]`, not a native `<button>` (see "Component
markup" above) — a native button gets Enter/Space activation for free, this doesn't.
Click/keydown only swap icon/color/label; they have no effect on `.idle`/`.active`
motion, which tracks narration state independently per "Narration sync" above.
`dismissOrbNudge()` is defined in "First-visit nudge" below.

## Placement & panel-open repositioning

**Correction to the brainstorm's working assumption:** the brainstorm described this as
reusing "the same value the existing `#stage` shift-left rule already uses." Checked
against the actual files — `#app.panel-open #stage { transform: translateX(-11vw); }`
(`bullion_mk18.html:179`, identical in `bullion_mkultra.html:203`) — that rule shifts by a
fixed `-11vw`, **not** by the detail panel's own width. There is no existing rule that
shifts by `min(380px, 92vw)`; that value only appears in `#detail-panel`'s own `width`
declaration (`:167`). The orb's shift is written directly against the panel's real width
instead of borrowing a rule that doesn't actually match it:

```css
#app.panel-open #persona-orb { transform: translateX(calc(-1 * min(380px, 92vw))); }
```

This guarantees the orb clears the panel's actual right edge regardless of viewport width
(the panel is `width: min(380px, 92vw)` — same expression, so the orb's left-shift always
equals the panel's true width). Slides back via the existing `transition: transform 0.28s
ease` already on `#persona-orb`. Applies identically in both files.

**New: mobile case, not covered by the original brainstorm.** Below `640px`,
`#detail-panel` becomes a bottom sheet (`bullion_mk18.html:315-322`): `max-height: 62vh`,
slides up from the bottom edge (`bottom: 0`), not from the right. The desktop
`translateX` rule above does nothing useful there, and worse, an orb sitting at
`bottom: 18px` would end up **underneath** the sheet whenever it's open — precisely when
narration is playing, the one moment the orb most needs to stay visible and legible. Add
a mobile-specific rule in the existing `@media (max-width: 640px)` block, alongside the
existing `#app.panel-open #stage` mobile override (`:324`):

```css
@media (max-width: 640px) {
  #app.panel-open #persona-orb { transform: translateY(calc(-62vh - 12px)); }
}
```

This lifts the orb clear above the open sheet (`62vh` sheet height + `12px` breathing
room), mirroring the desktop fix's logic — shift by exactly the panel's real extent — but
along the axis mobile actually uses. `#legend-box` fully hides on mobile
(`bullion_mk18.html:311`) rather than repositioning, but the orb can't take that shortcut:
it's the active narration indicator, so it must stay visible and clear of the sheet while
playing, not disappear.

## First-visit nudge

One-time ring-pulse, reusing the `toolsPulse` keyframe verbatim (`bullion_mk18.html:263-267`,
`box-shadow` ring expanding from the element then fading), plus a tooltip ("Tap to switch
narrator voice"). Gated by a new `sessionStorage` flag (own key,
`'bullion-orb-nudge-dismissed'` — **not** reusing `mode-toggle-btn`'s existing
`.tools-ready` class/flag, since that one is driven by `onFirstInteraction()`
(`:2142-2147`) for an unrelated affordance and never explicitly cleared; the orb needs its
own independently-dismissible flag). The key tracks whether the nudge has been
**dismissed**, not whether it has been shown — it's only ever written inside
`dismissOrbNudge()`, so an ignored (never-dismissed) nudge correctly reappears on reload.

The tooltip is a plain child `<span>`, not a `::after` pseudo-element — it needs to hold
real dismissible text and be independently positioned, which a pseudo-element makes
awkward. Added to the static markup from "Component markup" above:

```html
<div id="persona-orb" title="Switch narration voice" class="idle"
     role="button" tabindex="0" aria-label="Switch narration voice, currently Alfred">
  <div class="orb-core"><span class="orb-icon">&#127913;</span></div>
  <div class="orb-label">Alfred</div>
  <div class="orb-nudge-tip" hidden>Tap to switch narrator voice</div>
</div>
```

```css
#persona-orb.nudge .orb-core { animation: toolsPulse 2s ease-out 3; }
.orb-nudge-tip {
  position: absolute; right: 0; bottom: 100%; margin-bottom: 8px;
  background: rgba(11,14,22,0.95); border: 1px solid var(--border); border-radius: 6px;
  padding: 4px 8px; font-size: 10.5px; white-space: nowrap; color: var(--text-dim);
}
```

(`#persona-orb` needs `position: fixed` already set from "Component markup," which
establishes the containing block `.orb-nudge-tip`'s `position: absolute` resolves
against — no extra positioning context needed.)

```js
if (!sessionStorage.getItem('bullion-orb-nudge-dismissed')) {
  const orb = document.getElementById('persona-orb');
  orb.classList.add('nudge');
  orb.querySelector('.orb-nudge-tip').hidden = false;
}
function dismissOrbNudge() {
  sessionStorage.setItem('bullion-orb-nudge-dismissed', '1');
  const orb = document.getElementById('persona-orb');
  if (!orb) return;
  orb.classList.remove('nudge');
  orb.querySelector('.orb-nudge-tip').hidden = true;
}
```

Called from both the orb's click/keydown handler (already wired in "Click → toggle
persona" above) and the top of `startCaption()` (first narration) — dismissed on
whichever happens first, per the brainstorm's confirmed behavior.

**Cascade note:** `.nudge` and `.idle` both set `animation` on the same `.orb-core`
element at equal specificity (`#persona-orb.nudge .orb-core` vs.
`#persona-orb.idle .orb-core`); since `#persona-orb` carries both classes simultaneously
during the nudge (`idle nudge`) and `.nudge`'s rule is declared later in the stylesheet,
`toolsPulse` wins by source order and fully replaces `orbBreathe` for the ~6s the nudge
runs (`2s ease-out` × 3 iterations). This is the intended behavior — the ring-pulse is a
stronger, more attention-grabbing motion than the idle breathe, and design section 6 only
called for the ring-pulse to run once, not layered on top of continuous breathing.

## Removal

Remove `#persona-toggle-btn` and its click listener from `#header-controls` in both files
(`bullion_mk18.html:527` + `:3441-3445`; `bullion_mkultra.html:579` + `:4108`-adjacent).

`applyPersonaToggle()` (`bullion_mk18.html:3435-3440`) is **repurposed**, not replaced —
same function name and call sites (once at init, once inside the toggle handler), new
body:

```js
function applyPersonaToggle() {
  const orb = document.getElementById('persona-orb');
  if (!orb) return;
  const isJohnny = narrationPersona === 'johnny';
  orb.classList.toggle('persona-alfred', !isJohnny);
  orb.classList.toggle('persona-johnny', isJohnny);
  orb.querySelector('.orb-icon').textContent = isJohnny ? '\u{1F479}' : '\u{1F3A9}';
  orb.querySelector('.orb-label').textContent = isJohnny ? 'Johnny' : 'Alfred';
  orb.setAttribute('aria-label', 'Switch narration voice, currently ' + (isJohnny ? 'Johnny' : 'Alfred'));
}
```

(`\u{1F479}` = 👹, `\u{1F3A9}` = 🎩 — same two glyphs as the static markup's initial
`&#127913;` HTML entity for 🎩, just written as JS string escapes here since this runs in
a `.js`-context `<script>` block, not HTML.) No Python/backend changes — pure front-end,
both files.

## Testing

No new automated tests — same category as the existing toggle/caption/autoplay work
(pure UI/CSS/animation, not asserted by the Python suite). Verification follows the
existing Task 6 pattern from the persona-toggle plan: mechanical checks via
claude-in-chrome —
- 0 console errors on fresh load, both files
- click toggles `narrationPersona`, updates `localStorage`, and updates the orb's
  label/icon/color
- `.active`/`.idle` class flips correctly around `startCaption()`/`clearCaption()` calls
- pulse fires once per revealed word (instrument `pulseOrb` call count against the known
  word count of a sample clip's text — reload between instrumentation attempts, per this
  project's standing double-wrap caveat)
- panel-open repositioning happens on both the desktop `translateX` path and, via a
  narrow-viewport Chrome window, the mobile `translateY` path
- nudge shows once per session, not on a second load within the same tab

Whether the pulse *feels* right in sync with real audio is not verifiable by automation —
same standing limitation as every audio/motion check in this project (see
`docs/superpowers/bullion-voice-persona-toggle-and-orb-handoff.md`, "Verification idioms")
— and is a human-in-a-focused-tab step for the user, independent of and not blocked by the
open voice-quality question.

## Explicitly not building

- Any change to persona resolution, the Johnny/Alfred fallback rule, caption word-timing
  math, or autoplay logic — all reused exactly as the existing toggle plan built them.
- Any change driven by the outcome of the open `say`-CLI voice-quality conversation — if
  that conversation later changes anything about *how* audio is produced (e.g. per-persona
  characteristics beyond a single MP3 file), this spec's sync mechanism (word-timeout →
  pulse) is unaffected; it reacts to caption timing, not to the audio source.
- A distinct mobile *icon/label* treatment — only positioning changes on mobile; the orb's
  visual content is identical across breakpoints.

## Risks / unverified

- The brainstorm's original placement rationale (reusing an "existing" panel-width shift
  value) didn't match the actual code — corrected above by writing the shift directly
  against the real panel width/height on each axis. Worth a visual sanity check once
  implemented, since this is new-written CSS, not a copy of a proven existing rule.
- Mobile repositioning is new scope the original brainstorm didn't consider at all (it
  only discussed desktop). The `62vh` sheet height is read from `#detail-panel`'s own
  `max-height` (`bullion_mk18.html:316`) — if that value ever changes, the orb's
  `translateY` offset must change with it; they're two independent declarations, not
  derived from one shared value.
- `.idle`'s 3.6s breathing period is a deliberate near-miss of `hubPulse`'s 3.2s (see
  "States" above) — a judgment call, not a measured constraint; revisit if it reads as
  visually clashing once both animations are on screen together.
