# Bullion Voice Narration — Phase 1 (Full Node Coverage) — Design

**Written:** 2026-07-30 · **Status:** approved, ready for `writing-plans`.

**Builds on:** `2026-07-30-bullion-voice-narration-design.md` (the pilot: 6 nodes, 2
field-note links, shipped and live). This spec covers Phase 1 only — expanding node
narration from 6 to all 39 nodes. Link/relationship-row narration is explicitly deferred
to a separate Phase 2 with its own design pass (see "Explicitly not building").

## Goal

Full narration coverage for all 39 nodes in `bullion-live-map/bullion_mk18.html` and
`bullion-live-map/bullion_mkultra.html`, replacing the pilot's hardcoded 6-entry
`NARRATIONS` dict with a generation pipeline that extracts text from the live HTML, so
node text and narration audio cannot silently drift apart the way a hand-copied dict
could.

## Scope

**In scope:**
- Extracting all 39 nodes' `beginner` text from `bullion_mk18.html` at generation time.
- Regenerating all 39 MP3 clips (including the 6 already-piloted ones) through one
  consistent extraction + generation pipeline.
- Expanding `NARRATION_MANIFEST` in both `bullion_mk18.html` and `bullion_mkultra.html`
  from 6 to 39 entries.
- A completeness check asserting every `NODES` id has a manifest entry.

**Out of scope:**
- Any link/relationship-row narration (field notes beyond the 2 pilot ones, or any
  other relationship row) — Phase 2, not designed yet.
- Expert-mode text narration — beginner-only, same as the pilot.
- The AI-generated `#narrative-box` market narrative — still live/dynamic, still
  unsuited to pre-generated static files (unchanged from the pilot's decision).

## Node text source of truth

Confirmed via live JS inspection: `bullion_mk18.html` has 39 nodes (`NODES.length`), 93
`LINKS`, 16 `PLUMBING_LINKS`. Each node has shape `{id, label, group, beginner: [...],
expert: [...]}`. `bullion_mkultra.html`'s `NODES` array is byte-identical to
`bullion_mk18.html`'s (diffed as raw text — node text hasn't drifted since the honesty
pass), so **extraction happens once, from `mk18.html` only**, and both files' manifests
point at the same physical audio files under the existing shared
`bullion-live-map/audio/narration/` directory.

Each node's narration text is `beginner.join(' ')` — identical construction to the pilot,
so the 6 already-piloted nodes' wording is reproduced exactly, just regenerated through
the new pipeline (see "Risks" for what does and doesn't stay identical about a
regeneration).

## Generation script changes

`bullion-live-map/scripts/generate_narration.py` changes from the pilot's hardcoded
`NARRATIONS` dict to an HTML-extraction step:

1. Launch headless Chrome against `bullion_mk18.html`, using an isolated
   `--user-data-dir=/tmp/<unique>` (this project's standing convention — never launch
   headless Chrome against these files without one).
2. Evaluate `JSON.stringify(NODES.map(n => ({id: n.id, text: n.beginner.join(' ')})))`
   in-page and parse the result as the list of 39 `{id, text}` pairs. This becomes the
   sole source of truth for narration text, replacing the hardcoded dict entirely — no
   fallback to hardcoded text if extraction fails (see Error handling).
3. For each of the 39 pairs, generate one MP3 via the existing Chatterbox pipeline
   (unchanged from the pilot) and write it to
   `bullion-live-map/audio/narration/node-<id>.mp3`, overwriting the 6 pilot files that
   already exist there.
4. The 2 existing field-note clips (`link-credit-equit.mp3`, `link-usd-oil.mp3`) are
   untouched — this script's node-extraction path does not touch link narration at all.

## Front-end wiring

No new front-end code paths — `openDetail()`'s existing `NARRATION_MANIFEST[d.id]`
lookup already generalizes to any id present in the manifest. The only change is data:
`NARRATION_MANIFEST` expands from 6 to 39 entries in both `bullion_mk18.html` and
`bullion_mkultra.html`, one entry per node id pointing at `node-<id>.mp3`.

## Completeness check

A new check (script or test, decided during implementation) asserting
`Object.keys(NARRATION_MANIFEST).length === NODES.length` and that every `NODES[i].id`
has a corresponding manifest key, in both HTML files. This matters now in a way it didn't
for the pilot: the pilot was deliberately partial (6 of 39), so a missing entry was
expected; Phase 1 is meant to be complete coverage, so a missing entry is now a real bug
to catch.

## Error handling

- **Extraction failure** (headless Chrome fails to load the page, or `NODES` is
  unexpectedly empty/malformed): the generation script aborts loudly (non-zero exit,
  printed error) rather than falling back to any cached or hardcoded text — silently
  generating audio from stale/wrong text would be worse than failing the run.
- **Per-clip generation failure:** same as the pilot's front-end behavior — a missing
  manifest entry or missing file simply means no 🔊 button (or a button whose `.play()`
  rejects silently, caught and `console.warn`'d) — no retry, no fallback voice.
- The completeness check is the mechanism that turns "a clip failed to generate" into a
  visible failure at build/test time, rather than a silent gap discovered later by a
  user.

## Testing

- **Headless-Chrome DOM probe** (isolated `--user-data-dir`): sweep all 39 nodes (no
  allowlist, unlike the pilot's 6), asserting the 🔊 button appears for every one and
  that `NARRATION_MANIFEST` has exactly 39 entries in each file.
- **Completeness check** as its own assertion (see above), run as part of this effort's
  test pass.
- **Programmatic audio check** (same idiom as pilot Task 3 Step 3): for all 39 clips,
  verify each file is non-empty and decodable, and duration is within a sane range for
  its text length.
- **Manual listen-through:** spot-check ~6-8 clips across different node groups (not all
  39) — backed by the programmatic check above for full coverage without requiring the
  user to listen to every clip.
- **Freeze-check:** `bullion_mk11.html`–`bullion_mk17.html` unchanged via
  `shasum -a 256` (this effort only touches `mk18`, `mkultra`, and the generation
  script/audio directory).
- **Python suite:** `cd bullion-live-map && python3 -m unittest discover -s tests &&
  python3 -m unittest test_calibrate`.

## Risks / unverified

- Chatterbox is likely not fully deterministic — regenerating the 6 pilot clips through
  this new pipeline may produce audibly different output for those 6 even with identical
  text/voice/model. The user has already confirmed regenerate-all is acceptable despite
  this.
- Chatterbox's generation time scaling to 39 clips is unverified — the pilot's 8-clip
  runtime is the only data point so far; this effort's implementation should budget for
  an unknown, possibly much longer run.
- Whether `mkultra.html`'s `LINKS`/`PLUMBING_LINKS` text matches `mk18.html`'s the same
  way `NODES` does is unchecked — irrelevant to this spec (nodes only), but will matter
  once Phase 2 starts.

## Explicitly not building

- Any link/relationship-row narration — Phase 2, starting from scratch design-wise (no
  call sites, no manifest-key scheme, no button placement decided). Reason surfaced
  during brainstorming: the pilot's 🔊 button only appears on 2 rare, visually-distinct
  italic field-note blocks; a typical node's relationship list runs 6-11 rows (Credit
  Markets showed 11 in a screenshot), so a 🔊 on every row is a real crowding/layout
  question the pilot never tested and Phase 1 does not attempt to answer.
- Expert-mode text narration.
- Any change to the `#narrative-box` live AI narrative.
- Any UI change beyond the manifest growing from 6 to 39 entries — no new buttons, no
  new interaction patterns.
