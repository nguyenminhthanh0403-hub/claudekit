# Bullion Voice Narration — Design (Pilot)

**Written:** 2026-07-30 · **Status:** approved, ready for `writing-plans`.

## Goal

Add narration, read in the user's own cloned voice, to a small pilot set of node
explanations and field notes in `bullion-live-map/bullion_mk18.html` and
`bullion-live-map/bullion_mkultra.html`. Prove the pipeline end-to-end on ~6-8 clips
before ever considering expansion to the full ~39-node set.

## Scope

**In scope:**
- Narrating the **beginner**-mode text of 6 pilot nodes (both files share the same 39
  node IDs, so one pilot list and one audio manifest per node ID covers both files):
  `fed`, `gold`, `vix`, `sec`, `repo`, `yield`
- Narrating `bullion_mkultra.html`'s 2 existing first-person field notes, on the
  `credit→equit` and `usd→oil` links (the only two links carrying a `fieldNote` field
  today)
- A local, offline, one-time generation script producing static MP3 files
- A small 🔊 button per narrated node/field-note that plays the matching file

**Out of scope (explicitly, per prior brainstorming):**
- Expert-mode text (only beginner text is narrated)
- The AI-generated `#narrative-box` market narrative — it calls `api.anthropic.com` live
  and is different text every run, so it can't be pre-generated as a static file
- Any paid cloud TTS API (ElevenLabs was researched and rejected — cheapest cloning tier
  is $6/mo; the free self-hosted route was chosen instead)
- Full ~39-node coverage — this is a pilot only
- Any Web-Speech-API fallback or hybrid — rejected, adds a second code path and a jarring
  mixed-voice experience

## Voice / generation approach

The user's own voice, cloned via a free, self-hosted, open-source model — **Chatterbox**
was identified as the current best open-source quality/ease-of-setup match (GPT-SoVITS
and Kokoro were noted as alternatives, not chosen). Generation happens once, offline, on
the user's own Mac (CPU-only, no GPU assumed — expect real one-time setup cost: Python
env, multi-GB model download, slower inference). This is untested; treat as a real setup
risk to be resolved during implementation, not a solved step.

## Content & naming convention

Each pilot node's narration is its full `beginner` bullet array joined into one flowing
paragraph — **one audio clip per node**, not one per bullet, matching the "one 🔊 button
per node" interaction. Field notes narrate the existing `fieldNote` string as-is (no
modification).

Files live under `bullion-live-map/audio/narration/`:

| Content | Filename |
|---|---|
| Node `fed` | `node-fed.mp3` |
| Node `gold` | `node-gold.mp3` |
| Node `vix` | `node-vix.mp3` |
| Node `sec` | `node-sec.mp3` |
| Node `repo` | `node-repo.mp3` |
| Node `yield` | `node-yield.mp3` |
| Field note `credit → equit` | `link-credit-equit.mp3` |
| Field note `usd → oil` | `link-usd-oil.mp3` |

## Generation script

A one-time Python script, `bullion-live-map/scripts/generate_narration.py`. The 8
narration texts are **hardcoded directly in the script**, copy-pasted from the current
`beginner`/`fieldNote` source text in the HTML — not extracted programmatically from the
live `NODES`/`LINKS` arrays. For a fixed pilot of 8 static strings, building an HTML
parser/extractor is unneeded infrastructure (YAGNI); the script's only link back to the
HTML is via the output filenames above. The script loads the cloned voice and writes all
8 MP3s to `audio/narration/`.

## Front-end wiring — nodes

An inline manifest added to both `bullion_mk18.html` and `bullion_mkultra.html`:

```js
const NARRATION_MANIFEST = {
  fed:   'node-fed.mp3',
  gold:  'node-gold.mp3',
  vix:   'node-vix.mp3',
  sec:   'node-sec.mp3',
  repo:  'node-repo.mp3',
  yield: 'node-yield.mp3',
};
```

In `openDetail(d)` (currently at `bullion_mk18.html:1942`), a 🔊 button is added to
`#detail-header` next to the title. It is shown only when `NARRATION_MANIFEST[d.id]`
exists for the current node; otherwise it stays hidden (no placeholder, no disabled
state — a narrated node simply looks like every other node did before this feature).
Clicking it runs `new Audio('audio/narration/' + NARRATION_MANIFEST[d.id]).play()`.

## Front-end wiring — field notes

Same pattern, a second small manifest keyed by `"<source>-<target>"`:

```js
const NARRATION_LINKS = {
  'credit-equit': 'link-credit-equit.mp3',
  'usd-oil':      'link-usd-oil.mp3',
};
```

Checked wherever `.rel-field-note` is rendered (currently `bullion_mkultra.html:2546`).
When a matching entry exists, a small inline 🔊 button is appended after the field-note
text, playing the matching file the same way as the node button.

## Error handling

- **No manifest entry → no button, ever.** This is the only "missing content" state and
  it produces zero UI difference from today — no errors, no placeholders.
- **Button exists but playback fails** (missing file, decode error): the `.play()`
  promise rejection is caught, `console.warn`'d, and otherwise silent — no fallback
  voice, no retry, no visible error state. This matches the already-rejected
  Web-Speech-API-hybrid decision: a broken clip should look like nothing happened, not
  trigger a second code path.
- Each click constructs a fresh `Audio()` object, so a clip simply restarts from the
  beginning on repeat clicks — no play/pause state machine needed for a pilot.

## Testing

- **Manual, real Chrome:** click through all 8 pilot clips in both files and confirm
  they actually play and sound correct — headless Chrome cannot verify audible sound.
- **Headless-Chrome DOM probe** (isolated `--user-data-dir`, per this project's existing
  convention — never run headless Chrome against these files without one): assert the 🔊
  button appears only for the 6 pilot nodes and 2 pilot field notes, and is absent for
  the other ~33 nodes and 0 other links.
- **Freeze-check** `bullion_mk11.html`–`bullion_mk17.html` unchanged via `shasum -a 256`
  (this effort intentionally edits `mk18`, so `mk18` is excluded from the freeze-check,
  per the existing project convention for this specific effort).
- **Python suite:** `cd bullion-live-map && python3 -m unittest discover -s tests &&
  python3 -m unittest test_calibrate` — unrelated to this JS/audio work but cheap to
  re-run per project convention.
- **CSP:** `bullion_mk18.html`'s CSP (`default-src 'self'; script-src 'self'
  'unsafe-inline'; ...`) has no explicit `media-src`, so same-origin audio should fall
  through to `default-src 'self'`. This is an assumption from the prior brainstorm —
  confirm with a real browser load, don't treat as settled until verified.

## Risks / unverified

- Chatterbox (or an alternative) installing and running cleanly on this specific Mac is
  completely untested.
- CSP allowing same-origin audio playback is assumed, not yet confirmed.

## Explicitly not building

- Any extraction pipeline that reads narration text out of the live `NODES`/`LINKS`
  arrays — the pilot's 8 texts are hardcoded in the generation script.
- Any play/pause/seek UI, progress indicator, or waveform — a single click-to-play button
  per clip is the entire interaction.
- Any handling for nodes/links beyond the 8 listed above — everything else is
  unaffected by this change.
