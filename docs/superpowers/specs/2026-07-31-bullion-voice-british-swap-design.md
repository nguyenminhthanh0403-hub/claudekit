# Bullion Voice Narration — British Voice Swap — Design

**Written:** 2026-07-31 · **Status:** approved, ready for `writing-plans`.

**Builds on:** `2026-07-30-bullion-voice-narration-phase1-design.md` (39-node coverage,
shipped/live via Chatterbox voice cloning) and supersedes the open investigation in
`docs/superpowers/voice-narration-accent-debug-handoff.md` (cfg_weight tuning to fix the
cloned voice's wrong accent — that effort is now moot; this spec replaces the voice
entirely instead of tuning it).

## Goal

Replace the Chatterbox-cloned narration voice (reported by the user to sound like it has
an Indian accent, not their own) with macOS's built-in "Jamie (Premium)" British English
voice via the `say` CLI. Same 39 output files, same manifest, same front-end — only the
generation engine changes.

## Why not clone an actual "Jarvis" voice

The user's original ask was a British "Jarvis"-style assistant voice. Jarvis (voiced by
Paul Bettany in the Marvel films) is a copyrighted performance by a real, identifiable
actor. Feeding that audio into Chatterbox as a cloning reference and publishing the
output on a live public site (this map is deployed on GitHub Pages) would be cloning and
redistributing a real person's copyrighted voice without rights — ruled out on that basis,
not a technical limitation. A British, formal-assistant-toned voice delivers the same
*feel* without that problem.

## Approaches considered

1. **macOS `say` CLI with a built-in British voice — chosen.** Zero cost, fully offline,
   already installed, deterministic output. Limitation: only speaking rate is
   scriptable (`-r <wpm>`); the pitch/timbre/sentence-pause personalization the user
   tuned in System Settings → Accessibility → Spoken Content lives in a newer
   neural-voice parameter set that the classic `say` CLI does not expose — confirmed by
   generating before/after samples and diffing checksums (identical output across the
   System Settings change) and by testing legacy `[[pbas]]` pitch-embedding codes (the
   voice spoke the literal command text instead of applying it). The user accepted this
   trade-off (speed-only control) over the alternatives below.
2. **AVSpeechSynthesizer directly** (Swift/PyObjC, bypassing `say`) — rejected. Might
   expose `pitchMultiplier`, but Apple's own developer forums show open bugs
   ("AVSpeechSynthesisVoice ignores user-selected voices — Regression") on recent OS
   versions for this exact API surface. Uncertain payoff, real risk of flakiness, still
   no confirmed path to timbre/pause control either.
3. **Commercial TTS API (Amazon Polly Neural)** — rejected, though it was the
   technically strongest option: SSML `<prosody rate="" pitch="">` / `<break time="">`
   maps directly onto the speed/pitch/pause controls the user tuned by ear, at near-zero
   cost for this volume (~$0.10–0.20 one-time for 39 short clips). Rejected because it
   requires an AWS account, API credentials, and a network dependency the current
   fully-offline pipeline doesn't have — the user preferred staying on the free/offline
   `say` CLI and accepting partial control.

## Voice and parameters

- Voice: `Jamie (Premium)` (`en_GB`) — already downloaded on the user's machine via
  System Settings → Accessibility → Spoken Content → Manage Voices. **Not guaranteed to
  exist on a fresh machine** — the generation script should fail loudly (not silently
  fall back to a different voice) if `say -v "Jamie (Premium)"` errors.
- Rate: `-r 200` (measured ~9% faster than Jamie's default rate on the pilot "fed" node
  sentence — an audible approximation of the "slightly higher than normal premium" speed
  the user tuned). Confirm against a rendered sample before locking in; adjust the number
  if it doesn't match.
- Pitch, timbre, sentence-pause: **not reproduced** — see "Approaches considered" #1.
  This is an accepted, known gap, not a bug to chase further.

## Generation script changes

`bullion-live-map/scripts/generate_narration.py`:

1. `extract_node_texts()` (the headless-Chrome DOM probe against `bullion_mk18.html`)
   is **unchanged** — it has no dependency on the TTS engine and its own test coverage
   already passes independent of this change.
2. `main()`'s generation loop changes: drop the `torchaudio`/`chatterbox` imports,
   `VOICE_SAMPLE`, and `ChatterboxTTS.from_pretrained(...)` model load. For each
   extracted `{id, text}` pair, shell out to
   `say -v "Jamie (Premium)" -r 200 -o <tmp>.aiff <text>`, then reuse the existing
   `ffmpeg -i <tmp>.aiff -codec:a libmp3lame -qscale:a 2 <OUTPUT_DIR>/node-<id>.mp3`
   conversion, dropping the `afftdn` denoise filter (it existed to compensate for
   Chatterbox's generation noise floor; `say` output doesn't have that artifact).
3. Output contract is identical: same `OUTPUT_DIR`, same `node-<id>.mp3` filenames,
   overwriting the 39 Chatterbox-generated files in place.
4. The 2 existing field-note link clips (`link-credit-equit.mp3`, `link-usd-oil.mp3`)
   are regenerated the same way — no separate code path, since the loop is
   engine-agnostic per clip.

## Front-end wiring

None. `openDetail()`'s `NARRATION_MANIFEST[d.id]` lookup and `playNarration()` are
already engine-agnostic — they just play whatever MP3 sits at the manifest path. No
changes to `bullion_mk18.html` or `bullion_mkultra.html`.

## Error handling

Same posture as the existing script: fail loudly, no silent fallback.
- Missing/misnamed voice (`say -v "Jamie (Premium)"` not installed) → non-zero exit,
  printed error — same class of failure as today's missing `VOICE_SAMPLE` check.
- Extraction failure (headless Chrome/`NODES` probe) → unchanged from today, already
  raises `RuntimeError`.

## Testing

- `test_generate_narration.py`'s existing extraction and manifest-completeness tests are
  engine-agnostic (they assert `node-<id>.mp3` exists and is non-empty per node) and
  need no changes — they double as the regression check for this swap.
- Full Python suite (`cd bullion-live-map && python3 -m unittest discover -s tests`) run
  after regeneration, expecting the same pass count as today's baseline.
- Manual verification in Chrome MCP: play a handful of narration buttons across
  different node groups, confirm 0 console errors — same idiom used for every prior
  audio change in this project.
- Audible correctness (does Jamie actually sound right, does the rate feel natural) is,
  as always in this project, **not automatable** — the user judges by ear via `afplay`
  or Finder/QuickTime, same as the rejected Chatterbox cfg_weight experiment.

## Explicitly not building

- No UI toggle between voices — this replaces the cloned voice outright (user's
  choice), not an additive option.
- No cleanup of now-unused Chatterbox artifacts (`.venv-narration/`,
  `audio/voice_sample/user_voice.wav`) — left in place for now per the user's explicit
  call; a future pass can remove them if wanted.
- No attempt to reproduce pitch/timbre/sentence-pause via `say` — accepted gap, see
  "Voice and parameters."
- No archiving of `docs/superpowers/voice-narration-accent-debug-handoff.md` as part of
  this work — noted here as superseded; formal archiving follows this project's normal
  handoff-writing convention at the next handoff, not as part of this spec.

## Risks / unverified

- `-r 200` is a first approximation of "slightly faster than default," anchored to one
  measured duration comparison on one sentence — not yet confirmed by the user as
  matching what they tuned by ear. May need adjustment once real clips are heard.
- Whether Jamie (Premium) survives a fresh `git clone`/new-machine setup is unverified —
  Premium voices are a manual System Settings download, not something `pip`/`brew` can
  provision. If this pipeline is ever run from a different machine, that's a
  prerequisite, not something the script can fix.
