---
name: narration-regen-workflow
description: Use when regenerating Alfred/Johnny narration audio for bullion-live-map — changing ALFRED_RATE/JOHNNY_TEMPO/loudnorm constants in generate_narration.py, running regen_narration_v2.py, resuming an interrupted regen, or adding new node/event narration scripts. Documents the sample-before-you-commit convention, marker-file resume mechanics, the raw-WAV cache's filename-only-keyed trap, and the mandatory listening-pass gate before any commit/push of regenerated audio.
---

# Narration Regen Workflow

## Overview

This machine has only 8GB unified memory (confirmed via `sysctl hw.memsize`). Loading both
ChatterboxVC (Alfred) and ChatterboxTTS (Johnny) simultaneously caused heavy swap and severe
slowdowns in a prior session — so `regen_narration_v2.py` deliberately runs Alfred's ENTIRE
pass first with only `ChatterboxVC` resident, fully releases it (`del` + `gc.collect()` +
`torch.mps.empty_cache()`), THEN loads `ChatterboxTTS` for Johnny's entire pass. Never load
both models at once outside that script's existing sequencing.

This workflow has **two standing gates that must not be skipped without an explicit,
informed, one-time user ask**:
1. Sample a candidate rate/tempo change on ONE clip before committing to a full regen.
2. A real human listening pass before any commit/push of regenerated audio.

Both have been overridden exactly twice each in this project's history. Both times were
deliberate, explicit, one-time exceptions — not a new norm. Treat every future skip request
the same way: as a one-time exception the user has to actually ask for, not a default you
reach for under time pressure.

## Sample before you commit

Never edit the tracked `ALFRED_RATE` / `JOHNNY_TEMPO` constant in `generate_narration.py`
until a sample clip has been generated and the user has confirmed it. Use an in-process
monkey-patch so the tracked constant stays untouched during sampling:

For Johnny (`JOHNNY_TEMPO`):
```python
import sys
sys.path.insert(0, "bullion-live-map/scripts")
import generate_narration as gn

gn.JOHNNY_TEMPO = 0.92  # candidate value — monkey-patch only, don't edit the file yet

out_path = gn.OUTPUT_DIR / "johnny-banks-sample-092.mp3"  # NEVER the real johnny-banks.mp3
tts = gn.load_tts_model()
gn.synthesize_johnny(gn.JOHNNY_SCRIPTS["banks"], out_path, tts)
```

For Alfred (`ALFRED_RATE`), the analogous pattern:
```python
gn.ALFRED_RATE = 210  # candidate value

vc = gn.load_vc_model()
alfred_dict = gn.alfred_ref_dict(vc)
out_path = gn.OUTPUT_DIR / "node-banks-sample-210.mp3"
gn.synthesize(gn.JOHNNY_SCRIPTS["banks"], gn.ALFRED_RATE, out_path, vc, alfred_dict)
```
(Alfred's node text comes from `extract_node_texts(gn.SOURCE_HTML)`, not `JOHNNY_SCRIPTS` —
find the "banks" node's `text` field from that list rather than reusing Johnny's script.)

Then `afplay <out_path>` and wait for the user's verdict. `"banks"` is the standing reference
node used for continuity across every past rate/tempo pick (Alfred: 218→213; Johnny:
0.9→0.95→0.92). Only after explicit confirmation does the tracked constant in
`generate_narration.py` actually get edited.

## Full regen

Invoke via the narration venv, never plain `python3`:
```bash
.venv-narration/bin/python3 bullion-live-map/scripts/regen_narration_v2.py
```

**Critical caveat:** the marker file
`bullion-live-map/audio/narration/.regen_2026-08-02_v2_done.txt` gates every clip — a line
present means that clip is treated as already done and SKIPPED. If it already has all 100
entries (39 node + 11 event, × Alfred/Johnny), a naive re-run does nothing at all, silently.
To re-run for one persona only (e.g. a Johnny-only tempo change), strip only that persona's
50 lines first:
- Johnny lines: `johnny-<node_id>` and `event-johnny-<event_id>`
- Alfred lines: `alfred-<node_id>` and `event-alfred-<event_id>` — leave these untouched for a
  Johnny-only change.

## Raw-WAV cache caveat

`generate_narration.py`'s `synthesize_johnny()` caches the pre-atempo raw WAV in
`bullion-live-map/audio/narration/raw_cache_johnny/`, **keyed by output filename stem only —
not content-hashed.** A cache hit skips the expensive `tts.generate()` diffusion step
entirely and re-encodes straight from the cached raw audio; a cache miss runs full
generation.

**The trap:** if a node's or event's SCRIPT TEXT changes but its output filename doesn't, the
cache will silently serve the OLD stale audio at the new tempo. There is no automatic
invalidation. Before trusting a cache hit, confirm the script text for that id hasn't changed
since the cached `.wav` was written — if it has, manually delete
`raw_cache_johnny/<id>.wav` to force fresh generation. (Alfred's `synthesize()` has no
equivalent cache — every Alfred clip is always a full VC conversion.)

## Memory-safety / timing expectations

Alfred always completes before Johnny starts loading (see Overview) — don't try to
parallelize or interleave them. Realistic timing, from an actual measured run: a 411-character
Johnny script (near the top of this project's range — average is ~323 characters, longest is
436 for "mortgage") took ~62 seconds of pure diffusion sampling under a clean, uncontended
run. Scaling that across all 50 Johnny clips gives a rough estimate of **35-50 minutes** under
normal conditions for a full Johnny-only regen.

That estimate can be wrong in one direction: a documented per-generation memory-growth
ceiling has caused a single long clip to stall for many extra minutes with swap pinned at
13/13GB in a prior session. The driver is safe to kill and resume at any point
(marker-file-driven) — a slow run is not risky, just slow. Budget real wall-clock time rather
than trusting the estimate as a hard ceiling.

## Mandatory listening-pass gate

**Before any commit or push of regenerated/re-encoded audio:** `afplay` at least the
new/changed persona's full clip set, or at minimum a representative spot-check — all event
clips (11) plus a sample of node clips. This is not optional and not a default judgment call
to skip under time pressure, even though it has happened twice before in this project's
history. Skipping it requires an explicit, informed, one-time request from the user in that
specific session — never assume a prior override still applies.

## Commit + push

Run the test suite first, exactly:
```bash
cd bullion-live-map && python3 -m unittest discover -s tests && \
  python3 -m unittest test_calibrate && \
  python3 -m unittest scripts.test_generate_narration -v
```
(Plain `python3` for the test suite — NOT the narration venv.) Then the standard pattern
already used in this project: `git add` the specific changed files (never `git add -A`/`.` —
this project has a long list of untracked "not mine, leave alone" files, see any recent
narration handoff for the current list), `git commit`, `git push origin main` (works directly
from the Bash tool via `GIT_TERMINAL_PROMPT=0`; `gh` CLI is not installed).

## Common mistakes

- **Forgetting to strip the marker file before a targeted re-run.** The driver reports "no
  clips remaining" and exits having done nothing — easy to mistake for a fast, successful
  no-op run instead of a fully-skipped one.
- **Trusting the raw-WAV cache after editing a script's TEXT** (not just a tempo/rate
  constant). Silently serves stale audio at the new tempo/rate. The affected id's cached
  `.wav` must be deleted manually — there is no automatic invalidation.
- **Editing the tracked `ALFRED_RATE`/`JOHNNY_TEMPO` constant before the sample clip is
  actually confirmed by the user.** Always sample via the in-process monkey-patch first (see
  "Sample before you commit") — never edit the file speculatively.
- **Leaving throwaway sample files uncleaned.** Sample-step output (e.g. a past session's
  `johnny-banks-sample-092.mp3`, or its cached `raw_cache_johnny/johnny-banks-sample-092.wav`)
  is easy to forget. Before a real regen or a commit, check for and remove any
  `*-sample-*.mp3` / `*-sample-*.wav` files left in `bullion-live-map/audio/narration/` and
  its cache subdirectory.
