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
  recording, and `Jamie (Premium)`, plus a small Johnny-only post-conversion pitch-down
  for a meaner edge (see "Persona voice-color tweak" below) — added after the Task 1
  spike's listening test found the base blend "not fully convincing yet" and the user
  asked for more spite specifically in Johnny's character.

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
`s3gen.embed_ref()` to produce a `ref_dict`. There is no built-in multi-voice blend mode.

**Confirmed by reading `S3Gen.embed_ref()`'s source directly (2026-08-01):** `ref_dict` is
not one uniform kind of tensor — it has two conceptually different kinds of fields:

- `embedding` — a fixed-size speaker x-vector. This is the actual speaker-identity signal
  and the only field that's meaningful to average across independently-extracted clips.
- `prompt_token` / `prompt_token_len` / `prompt_feat` — a variable-length acoustic prompt
  (speech tokens + mel spectrogram) taken directly from that one clip's audio content,
  used for flow-matching continuation. Length is tied to that specific clip's duration.
  Averaging these across clips of different lengths either shape-mismatches or, if shapes
  happen to align, blends unrelated spectrograms into acoustic mush — not a blended voice.
  `prompt_feat_len` is always `None` (confirmed in source), not something to average.

This design therefore blends by **averaging only the `embedding` x-vector** across the
blend's reference clips, and takes `prompt_token`/`prompt_token_len`/`prompt_feat` from a
single designated clip rather than averaging them — defaulting to the user's own voice
clip as that designated source, since that's the identity most worth anchoring the
acoustic prompt to. Chaining multiple sequential conversions (as an alternative to
blending) was considered and rejected — each additional pass compounds artifacts rather
than blending cleanly.

- Reference clips for `Tom (Enhanced)` and `Jamie (Premium)` are synthesized once via
  `say` (any representative sentence — only timbre is extracted, content is irrelevant),
  cached in `audio/voice_sample/` (e.g. `tom_sample.wav`, `jamie_sample.wav`), and checked
  into the repo like `user_voice.wav`. Regenerated only if the underlying `say` voices
  change.
- Alfred's target = average of `embed_ref(jamie_sample.wav)['embedding']` +
  `embed_ref(user_voice.wav)['embedding']`; acoustic prompt from `user_voice.wav`.
- Johnny's target = average of `embed_ref(tom_sample.wav)['embedding']` +
  `embed_ref(user_voice.wav)['embedding']` + `embed_ref(jamie_sample.wav)['embedding']`;
  acoustic prompt from `user_voice.wav`.
- Even with this correction, whether averaging x-vectors alone (while anchoring the
  acoustic prompt to one clip) actually sounds like a coherent blend — versus just
  sounding like the user's voice with a marginal shift — is unproven and exactly what the
  spike (below) tests before any pipeline integration work happens.

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

**Result (2026-08-01): gate passed.** Both blends confirmed by the user as a coherent
blend with the correct accent. Caveat raised alongside the pass: the voice is "not fully
convincing yet" — not a blocker for proceeding, but a quality bar to re-check against real,
full-length regenerated clips at Task 4's listening pass (see the implementation plan). If
it's still not convincing at that point, the next move is revisiting blend composition
(the spec's stated fallback above), not further tuning around the underlying issue.

## Persona voice-color tweak: Johnny-only pitch-down

Raised by the user immediately after the spike gate passed, prompted by both the "not
fully convincing yet" note above and a separate ask for Johnny's character to read as
more spiteful. Two levers exist for "more spiteful": sharper script wording (a copy
change, no pipeline impact, not in scope for this spec) and a harsher voice *color* (in
scope here).

Neither `say` (rate-only scripting) nor `ChatterboxVC` (timbre, not prosody/emotion) can
express "spiteful delivery" directly — the only available lever in this pipeline is a
small pitch/formant adjustment applied to Johnny's already-converted output. Tested via a
quick extension of the Task 1 spike: `librosa.effects.pitch_shift` at **-1.5 semitones**,
applied after voice conversion, before MP3 encoding. Confirmed by ear in the same session
as the base blend. Johnny-only — Alfred's blend and output are unaffected by this section.

This supersedes the "Explicitly not building" section's original "no pitch/formant
differentiation" line below, scoped narrowly to this one Johnny-only tweak — the broader
point (no *per-persona voice-cloning* differentiation beyond this, no UI-exposed control
over it) still holds.

## Pipeline integration (after spike passes)

`bullion-live-map/scripts/generate_narration.py`:

1. `extract_node_texts()` and the `say` content-generation call are **unchanged**.
2. `ChatterboxVC` loads once at script start (real model weights — expensive to reload
   per clip). The two blended `ref_dict`s (Alfred's, Johnny's) are also built once at
   startup, not recomputed per node.
3. `synthesize()` grows a step: `say` → `.aiff` → `.wav` (needed for `librosa`/VC input,
   reusing the existing `ffmpeg` call) → voice-convert against the persona's blended
   `ref_dict` → (Johnny only) pitch-shift -1.5 semitones per the "Persona voice-color
   tweak" section above → final `.mp3` (`ffmpeg`, same encode settings as today).
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
- Test that Johnny's synthesis path applies the -1.5 semitone pitch-shift and Alfred's
  does not — a cheap, mockable assertion (call arguments / conditional branch), not one
  that needs real pitch-shifted audio to verify.
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
- No pitch/formant differentiation beyond the existing rate-based split and Johnny's
  single -1.5 semitone pitch-down (see "Persona voice-color tweak" above, added
  2026-08-01) — no further per-persona voice tuning, and no UI-exposed control over any
  of this, is in scope here.
- No new recording session for `user_voice.wav` — reused as-is unless the spike reveals a
  quality problem traceable to its length/quality, in which case recording a longer/cleaner
  sample becomes a follow-up, not part of this work.
- No cleanup of now-superseded artifacts from prior engine attempts.

## Risks / unverified

- **Primary risk, gated by the spike:** averaging speaker x-vectors across 2-3
  independently-extracted reference clips, while anchoring the acoustic prompt
  (`prompt_token`/`prompt_feat`) to a single clip, is not a documented/supported use of
  this model. It may produce a coherent blended timbre, or it may sound more like "user's
  voice with a marginal shift" than a true blend, since the acoustic prompt (arguably the
  bigger driver of perceived voice color) comes from only one clip — this is discovered
  empirically, not assumed.
- The x-vector (`embedding`) is fixed-size regardless of input clip length (speaker
  encoders produce a constant-dimension output), so shape compatibility for the averaging
  step itself is low-risk — confirmed by reading `S3Gen.embed_ref()`'s source. The real
  unknown is perceptual (does it sound blended), not a shape/crash risk.
- Whether the accent risk is actually as reduced as hypothesized (voice conversion
  preserving `say`'s pronunciation vs. full TTS generating it) is a reasoned expectation,
  not a verified guarantee — the spike's listening test is what actually confirms or
  refutes it.
- Whether `Tom (Enhanced)` and `Jamie (Premium)` survive a fresh machine/clone is the same
  pre-existing gap already noted in the British-voice-swap spec — Premium/Enhanced voices
  are a manual System Settings download, not something the pipeline can provision.
