# Bullion Narration — Voice-Conversion Blend ("Thamie") — Design

**Written:** 2026-08-01 · **Status:** approved, ready for `writing-plans`.

**Builds on:** `2026-07-31-bullion-voice-british-swap-design.md` (current engine:
`say -v "Jamie (Premium)"` for both personas' content) and resolves the open
voice-quality complaint carried forward from
`bullion-voice-persona-toggle-and-orb-handoff.md` / `bullion-persona-orb-shipped-handoff.md`
("`say`-CLI sounds too robotic/synthetic for either persona — not a rate issue"). Also
resolves the deferred `bullion-thamie-voice-blend-idea` project memory (blend the user's
cloned reference voice with `say`'s Jamie into a "Thamie" persona), generalizing it to
cover both Alfred and Johnny rather than a single blend.

## Goal

Reduce the "robotic/synthetic" quality of both narration personas by adding a
voice-conversion pass after `say` generates the content audio, re-coloring the timbre
toward a blend of reference voices, instead of replacing the engine outright. Content
generation (pronunciation, timing, rate tuning already done by ear: Alfred 240 wpm,
Johnny 225 wpm) is unchanged — only timbre changes.

- Alfred's target timbre: 2-way blend of `Jamie (Premium)` (the existing content voice)
  and the user's own reference recording.
- Johnny's target timbre: 3-way blend of `Tom (Enhanced)`, the user's own reference
  recording, and `Jamie (Premium)`.

Both `Tom (Enhanced)` (`en_US`) and `Jamie (Premium)` (`en_GB`) are confirmed already
installed via System Settings → Accessibility → Spoken Content → Manage Voices (verified
`say -v '?'` on 2026-08-01). The user's reference recording is the existing
`audio/voice_sample/user_voice.wav` (108s, left over from the original Chatterbox engine).

## Why voice conversion instead of a different TTS engine

Two prior engines were already tried and rejected:

1. **Chatterbox voice cloning (original engine):** rejected — cloned output carried the
   wrong accent (see `2026-07-31-bullion-voice-british-swap-design.md`'s "Why not clone").
2. **`say` CLI (current engine):** solves the accent/reliability problem but is reported
   too robotic/synthetic — the open complaint this spec addresses.

Both are full text-to-speech engines: they generate pronunciation, prosody, *and* timbre
from scratch, which is where accent risk lives. Voice **conversion** is a different
operation — it takes `say`'s already-correct, already-tuned audio and re-colors only the
timbre, leaving pronunciation and cadence exactly as `say` produced them. This narrows
the accent risk considerably (it was Chatterbox's text-to-speech generation that produced
the wrong accent, not a conversion pass) without giving up the reliability of keeping
`say` as the content engine. Chatterbox's own package (`chatterbox-tts`, already installed
in `.venv-narration` from the original engine, no new dependency needed) exposes exactly
this as `chatterbox.vc.ChatterboxVC` — a pure audio-in/audio-out conversion class, distinct
from the `chatterbox.tts` module that was previously rejected.

## Approaches considered

1. **Voice-conversion blend on top of `say` (this spec, chosen).** Local, offline, no new
   dependency, keeps all prior rate-tuning work, lowest accent risk of the three options
   because `say` still does all pronunciation. Real unknown: whether averaging conditioning
   embeddings from multiple reference clips produces a coherent blended voice or a muddy
   one — ungated by a listening-test spike before full pipeline integration (see below).
2. **Direct local voice cloning (e.g. Coqui XTTS-v2), bypassing `say` entirely.** Rejected
   for now — same category of tool as the already-rejected Chatterbox TTS engine, carrying
   the same class of accent risk, for no clearly better payoff than option 1. Kept as the
   fallback if option 1's spike fails.
3. **Cloud TTS with voice cloning (e.g. ElevenLabs).** Rejected for now — best available
   naturalness/accent control, but costs per generation and needs an API key/network
   dependency the current fully-offline pipeline doesn't have. Held in reserve if both
   local options (1 and 2) fail to clear the quality bar.

## Blend mechanism

`ChatterboxVC.generate(audio, target_voice_path)` accepts exactly one reference clip per
conversion — internally, `set_target_voice()` loads that one clip and calls
`s3gen.embed_ref()` to produce a `ref_dict` of conditioning tensors. There is no built-in
multi-voice blend mode.

This design blends by **averaging the `ref_dict` tensors** extracted independently from
each reference clip, then running conversion against the averaged dict, rather than
picking one dominant voice or chaining multiple sequential conversions (chaining was
considered and rejected — each additional pass compounds artifacts rather than blending
cleanly).

- Reference clips for `Tom (Enhanced)` and `Jamie (Premium)` are synthesized once via
  `say` (any representative sentence — only timbre is extracted, content is irrelevant),
  cached in `audio/voice_sample/` (e.g. `tom_sample.wav`, `jamie_sample.wav`), and checked
  into the repo like `user_voice.wav`. Regenerated only if the underlying `say` voices
  change.
- Alfred's target = average of `embed_ref(jamie_sample.wav)` + `embed_ref(user_voice.wav)`.
- Johnny's target = average of `embed_ref(tom_sample.wav)` + `embed_ref(user_voice.wav)` +
  `embed_ref(jamie_sample.wav)`.
- This is unproven for this model and is exactly what the spike (below) tests before any
  pipeline integration work happens.

## Feasibility spike (gates everything below)

Before touching `generate_narration.py`, a throwaway script:

1. Loads `ChatterboxVC` once.
2. Builds Alfred's 2-way and Johnny's 3-way averaged `ref_dict`s as described above.
3. Converts one existing Alfred clip (e.g. `node-fed.mp3`) and one existing Johnny clip
   (e.g. `johnny-fed.mp3`) through their respective blended targets.
4. Drops the output somewhere for the user to listen to directly (not judged by
   automation — audible quality has never been automatable in this project, per every
   prior voice spec).

**Gate:** if either blend sounds muddy/incoherent, do not proceed to pipeline
integration. Fallback within this same approach: drop the weakest contributor from the
blend (e.g. 2-way instead of 3-way for Johnny) and re-spike, before considering Approach 2
or 3 above.

## Pipeline integration (after spike passes)

`bullion-live-map/scripts/generate_narration.py`:

1. `extract_node_texts()` and the `say` content-generation call are **unchanged**.
2. `ChatterboxVC` loads once at script start (real model weights — expensive to reload
   per clip). The two blended `ref_dict`s (Alfred's, Johnny's) are also built once at
   startup, not recomputed per node.
3. `synthesize()` grows a step: `say` → `.aiff` → `.wav` (needed for `librosa`/VC input,
   reusing the existing `ffmpeg` call) → voice-convert against the persona's blended
   `ref_dict` → final `.mp3` (`ffmpeg`, same encode settings as today).
4. Output contract unchanged: same `OUTPUT_DIR`, same `node-<id>.mp3` /
   `johnny-<id>.mp3` filenames, overwriting today's `say`-only files in place.
5. Error handling keeps the existing posture: fail loudly, no silent fallback (missing
   voice, missing reference clip, or model load failure all raise, same as today's
   missing-voice check).

## Front-end wiring

None. `playNarration()`/`startCaption()` (`bullion_mkultra.html:4154-4184`) derive
per-word caption/pulse timing from `audio.duration` at playback time — they have no
dependency on how the MP3 was generated. Confirmed by reading the current implementation;
this holds regardless of which engine or conversion step produces the file.

## Testing

- Extend `test_generate_narration.py` with tests for the new embedding-averaging and
  conversion steps. Since `ChatterboxVC` is a real ML model (expensive to load), these
  tests mock/stub the model rather than loading real weights on every run — matching the
  existing split in this test file between fast checks and the few tests that hit real
  system state (e.g. `_voice_installed` against the real installed voice list).
  `extract_node_texts()` tests are already engine-agnostic and need no changes.
- Full suite (`cd bullion-live-map && python3 -m unittest discover -s tests && python3 -m
  unittest test_calibrate && python3 -m unittest scripts.test_generate_narration -v`) run
  after regeneration, expecting the same pass count as today's baseline (96/96) plus the
  new conversion tests.
- Manual: play a handful of narration buttons across both personas in Chrome, confirm 0
  console errors — same idiom used for every prior audio change in this project.
- Audible quality (does the blend actually sound less robotic, does the accent stay
  correct) is **not automatable** — user judgment by ear, same as every prior voice
  change in this project. This is the actual acceptance criterion for the whole feature,
  not a formality.

## Explicitly not building

- No UI changes — this replaces the narration engine's timbre in place, not an additive
  voice option or toggle.
- No pitch/formant differentiation beyond the existing rate-based split (Alfred 240 wpm,
  Johnny 225 wpm) — both personas' blends feed the same downstream pipeline. A future
  per-persona pitch tweak is plausible but out of scope here.
- No new recording session for `user_voice.wav` — reused as-is unless the spike reveals a
  quality problem traceable to its length/quality, in which case recording a longer/cleaner
  sample becomes a follow-up, not part of this work.
- No cleanup of now-superseded artifacts from prior engine attempts.

## Risks / unverified

- **Primary risk, gated by the spike:** averaging `ChatterboxVC`'s internal conditioning
  tensors across 2-3 independently-extracted reference clips is not a documented/supported
  use of this model. It may produce a coherent blended timbre, or it may not — this is
  discovered empirically, not assumed.
- Tensor shape compatibility across reference clips of different lengths is expected
  (`set_target_voice` truncates to a fixed `DEC_COND_LEN` before extraction) but not yet
  confirmed — first thing checked during the spike.
- Whether the accent risk is actually as reduced as hypothesized (voice conversion
  preserving `say`'s pronunciation vs. full TTS generating it) is a reasoned expectation,
  not a verified guarantee — the spike's listening test is what actually confirms or
  refutes it.
- Whether `Tom (Enhanced)` and `Jamie (Premium)` survive a fresh machine/clone is the same
  pre-existing gap already noted in the British-voice-swap spec — Premium/Enhanced voices
  are a manual System Settings download, not something the pipeline can provision.
