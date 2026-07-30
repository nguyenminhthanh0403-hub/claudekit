# Bullion Voice Narration (Pilot) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add click-to-play 🔊 narration, read in the user's own cloned voice, to 6 pilot node explanations and 2 field notes in `bullion_mk18.html` and `bullion_mkultra.html`, proving the local-TTS pipeline end-to-end.

**Architecture:** A one-time, offline Python script (Chatterbox voice cloning) generates 8 static MP3s from hardcoded text. Both HTML files get a small manifest object mapping node/link IDs to filenames, plus a 🔊 button wired to a `playNarration(file)` helper that does `new Audio('audio/narration/' + file).play()`. No manifest entry means no button, ever; playback failures are caught and silently logged.

**Tech Stack:** Python 3.12 (venv, isolated from the project's default `python3` 3.14 — Chatterbox requires Python >=3.10 and is untested on 3.14), `chatterbox-tts` (PyPI), `torch`/`torchaudio` (CPU), `ffmpeg` (Homebrew, for WAV→MP3), vanilla JS in the existing single-file HTML apps.

## Global Constraints

- Only **beginner**-mode text is narrated. Never touch expert text. (spec: Scope)
- No paid cloud TTS API. Voice cloning is local/offline via Chatterbox. (spec: Voice / generation approach)
- Exactly 8 static MP3s, named per the spec's table, under `bullion-live-map/audio/narration/`. Do not invent additional clips or nodes. (spec: Content & naming convention)
- The 8 narration texts are **hardcoded in the generation script**, copy-pasted verbatim from the HTML — no HTML parsing/extraction pipeline. (spec: Generation script, Explicitly not building)
- **No manifest entry → no button, ever.** No placeholder, no disabled state. (spec: Error handling)
- Playback failure (missing file, decode error): catch the `.play()` rejection, `console.warn`, otherwise silent. No fallback, no retry. (spec: Error handling)
- Each click builds a fresh `Audio()` object — no play/pause state machine. (spec: Error handling)
- No play/pause/seek UI, no progress indicator, no waveform. (spec: Explicitly not building)
- **Never `git add .` / `git add -A`.** Stage files by exact name only. (project convention)
- Freeze-check covers `bullion_mk11.html`–`bullion_mk17.html` only. `mk18.html` is this effort's intentional target and is excluded. (spec: Testing)
- Any headless Chrome invocation MUST pass an isolated `--user-data-dir=/tmp/<unique>` — omitting it has twice closed the user's real Chrome window in this project. (project convention)
- Don't `git push` unless the user asks for it this session.

---

## File Structure

**New files this plan creates:**
- `bullion-live-map/scripts/generate_narration.py` — one-time generation script (8 hardcoded texts → 8 MP3s).
- `bullion-live-map/audio/narration/*.mp3` — the 8 output clips (tracked in git; these are the shipped deliverable).
- `bullion-live-map/audio/voice_sample/user_voice.wav` — the user's raw cloning sample (NOT tracked in git — see Task 2).
- `bullion-live-map/.gitignore` — new file, ignores the local Python venv and the raw voice sample (neither should ever be committed).

**Existing files this plan modifies:**
- `bullion-live-map/bullion_mk18.html` — new CSS (`.narrate-btn`, `.detail-header-actions`), new `#detail-narrate` button markup in `#detail-header`, new `NARRATION_MANIFEST` + `playNarration()` JS, wiring in `openDetail()`.
- `bullion-live-map/bullion_mkultra.html` — same node-side changes as `mk18.html`, plus `NARRATION_LINKS` and a `.rel-field-note-narrate` button appended wherever `.rel-field-note` renders.

---

### Task 1: Provision the narration Python environment

**Files:**
- Create: `bullion-live-map/.gitignore`
- No application code yet — this task only proves the toolchain works.

**Interfaces:**
- Produces: a working virtualenv at `bullion-live-map/.venv-narration` with `chatterbox-tts` importable and able to run inference on CPU. Later tasks activate this venv to run `generate_narration.py`.

- [ ] **Step 1: Confirm Python 3.12 is available**

Run: `python3.12 --version`
Expected: `Python 3.12.x`. (The system default `python3` is 3.14, which Chatterbox's `torch` dependency has not been validated against — Chatterbox's own PyPI listing requires Python >=3.10 and states it was tested on 3.11. 3.12 is the newest available version on this Mac that's safely inside that support window.)

- [ ] **Step 2: Create an isolated venv and gitignore it**

```bash
cd bullion-live-map
python3.12 -m venv .venv-narration
```

Create `bullion-live-map/.gitignore`:
```
.venv-narration/
audio/voice_sample/
```

(The venv will pull in multi-GB `torch` wheels and model weights — it must never be `git add`ed. The raw voice sample is a personal recording, not a deliverable — see Task 2 for why it's excluded too.)

- [ ] **Step 3: Install ffmpeg (needed later for WAV→MP3 conversion)**

Run: `brew install ffmpeg` (skip if `which ffmpeg` already succeeds)
Expected: `ffmpeg -version` prints a version string afterward.

- [ ] **Step 4: Install chatterbox-tts and dependencies into the venv**

```bash
bullion-live-map/.venv-narration/bin/pip install --upgrade pip
bullion-live-map/.venv-narration/bin/pip install chatterbox-tts
```

Expected: installs succeed (this pulls `torch`, `torchaudio`, and other deps — expect several minutes and a multi-GB download). If `chatterbox-tts` fails to build/install on Python 3.12, that is real, useful signal — stop and report the exact error rather than working around it silently; this was flagged as an unverified risk in the spec.

- [ ] **Step 5: Smoke-test inference with a stock (non-cloned) voice**

```bash
bullion-live-map/.venv-narration/bin/python3 -c "
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

model = ChatterboxTTS.from_pretrained(device='cpu')
wav = model.generate('This is a smoke test of the narration pipeline.')
ta.save('/tmp/chatterbox_smoke_test.wav', wav, model.sr)
print('OK, sample rate:', model.sr)
"
```

Expected: prints `OK, sample rate: <n>` and `/tmp/chatterbox_smoke_test.wav` exists with non-zero size. This will trigger a one-time model weight download (multi-GB) on first run — expect it to take several minutes. `device='cpu'` is used deliberately: the spec assumes no GPU, and Chatterbox's documented examples all use `device='cuda'`, so CPU inference is itself unverified — if this step fails specifically on the `device='cpu'` argument, note that in your report; it's a real finding, not something to paper over.

Run: `ls -la /tmp/chatterbox_smoke_test.wav`
Expected: file exists, size > 0.

- [ ] **Step 6: Commit the gitignore**

```bash
git add bullion-live-map/.gitignore
git commit -m "Add gitignore for narration venv and raw voice sample"
```

---

### Task 2: Capture and validate the user's voice sample

**Files:**
- Create: `bullion-live-map/audio/voice_sample/user_voice.wav` (untracked — see Task 1's `.gitignore`)

**Interfaces:**
- Consumes: nothing from Task 1 except the venv's `torchaudio` for validation.
- Produces: `bullion-live-map/audio/voice_sample/user_voice.wav`, a mono WAV of the user's own speech. Task 3's `generate_narration.py` reads this path as `audio_prompt_path`.

- [ ] **Step 1: Ask the user for a voice sample**

This step cannot be automated — it requires the user to actually speak. Ask them directly:

> "I need a short recording of your voice to clone for narration. Please record about 60–90 seconds of yourself speaking clearly and naturally (reading a paragraph aloud is fine, doesn't need to be the narration content itself) in a quiet room, using QuickTime Player's 'New Audio Recording', Voice Memos, or any recorder. Export/save it as a `.wav` (or tell me the file format and I'll convert it), and tell me the file path once it's saved."

Wait for the user's response before proceeding — do not fabricate or reuse a placeholder audio file.

- [ ] **Step 2: Move/convert the sample into place**

```bash
mkdir -p bullion-live-map/audio/voice_sample
```

If the user's file isn't already a WAV, convert it (ffmpeg handles most formats):
```bash
ffmpeg -i "<path the user gave you>" -ar 24000 -ac 1 bullion-live-map/audio/voice_sample/user_voice.wav
```
If it's already a WAV, a plain copy is fine:
```bash
cp "<path the user gave you>" bullion-live-map/audio/voice_sample/user_voice.wav
```

- [ ] **Step 3: Validate duration and format**

```bash
bullion-live-map/.venv-narration/bin/python3 -c "
import torchaudio as ta
info = ta.info('bullion-live-map/audio/voice_sample/user_voice.wav')
duration = info.num_frames / info.sample_rate
print(f'duration={duration:.1f}s sample_rate={info.sample_rate} channels={info.num_channels}')
assert duration >= 10, f'sample too short ({duration:.1f}s) for reliable cloning'
print('OK')
"
```

Expected: prints `OK`. If the assertion fails, go back to Step 1 and ask the user for a longer recording — do not proceed with an inadequate sample.

---

### Task 3: Write and run the generation script

**Files:**
- Create: `bullion-live-map/scripts/generate_narration.py`
- Test: manual (run the script, then verify the 8 output files)

**Interfaces:**
- Consumes: `bullion-live-map/audio/voice_sample/user_voice.wav` (Task 2), the `.venv-narration` environment (Task 1).
- Produces: 8 files at `bullion-live-map/audio/narration/node-fed.mp3`, `node-gold.mp3`, `node-vix.mp3`, `node-sec.mp3`, `node-repo.mp3`, `node-yield.mp3`, `link-credit-equit.mp3`, `link-usd-oil.mp3`. Tasks 4 and 5's front-end manifests reference these exact filenames.

- [ ] **Step 1: Write the generation script**

Create `bullion-live-map/scripts/generate_narration.py`:

```python
#!/usr/bin/env python3
"""One-time offline generation of the 8 pilot narration MP3s, in the user's
cloned voice, for the Bullion voice-narration pilot. Texts below are
copy-pasted verbatim from the `beginner`/`fieldNote` fields in
bullion_mk18.html / bullion_mkultra.html as of 2026-07-30 — this script does
not read the HTML files, per the design spec's YAGNI call on a full-blown
extractor for 8 fixed strings."""
import subprocess
import sys
from pathlib import Path

import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

ROOT = Path(__file__).resolve().parent.parent
VOICE_SAMPLE = ROOT / "audio" / "voice_sample" / "user_voice.wav"
OUTPUT_DIR = ROOT / "audio" / "narration"

NARRATIONS = {
    "node-fed.mp3": (
        "The central bank that controls interest rates and money supply. "
        "It keeps prices stable, supports jobs, and lends as a last resort in crises."
    ),
    "node-gold.mp3": (
        "A 'safe haven' asset bought when people fear inflation or crashes. "
        "Its price often moves opposite to the dollar."
    ),
    "node-vix.mp3": (
        "The 'fear index', measuring how nervous options traders are. "
        "Above 30 signals panic and a rush out of stocks."
    ),
    "node-sec.mp3": (
        "The main watchdog for the stock market and public companies. "
        "Forces honest financial disclosure and punishes fraud and insider trading."
    ),
    "node-repo.mp3": (
        "The overnight market where banks and funds borrow cash using bonds as collateral. "
        "It is the plumbing of short-term funding, and the Fed steps in when it seizes."
    ),
    "node-yield.mp3": (
        "A chart of government borrowing rates across different time lengths. "
        "When short-term rates exceed long-term (inverted), recession risk rises."
    ),
    "link-credit-equit.mp3": (
        "I originally had wider credit spreads lifting stocks — which, looking back, "
        "never made sense. Once I actually measured it, spreads widening tracks equities "
        "falling, the way you’d expect."
    ),
    "link-usd-oil.mp3": (
        "I had this coded as dollar up → oil down — the textbook FX-pricing story "
        "everyone learns. The data disagreed. Over this window it’s actually positive. "
        "I’m leaving that in and telling you it’s weird rather than hiding it."
    ),
}


def main():
    if not VOICE_SAMPLE.exists():
        sys.exit(f"Voice sample not found: {VOICE_SAMPLE}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model = ChatterboxTTS.from_pretrained(device="cpu")

    for filename, text in NARRATIONS.items():
        wav_tmp = OUTPUT_DIR / (filename[:-4] + ".wav")
        mp3_out = OUTPUT_DIR / filename

        wav = model.generate(text, audio_prompt_path=str(VOICE_SAMPLE))
        ta.save(str(wav_tmp), wav, model.sr)

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_tmp), "-codec:a", "libmp3lame",
             "-qscale:a", "2", str(mp3_out)],
            check=True,
        )
        wav_tmp.unlink()
        print(f"wrote {mp3_out}")


if __name__ == "__main__":
    main()
```

(WAV is generated first and converted via `ffmpeg` rather than asking `torchaudio.save` to write MP3 directly — `torchaudio`'s MP3 encoder support depends on which backend is installed and isn't guaranteed, while `ffmpeg -codec:a libmp3lame` is a well-known reliable path.)

- [ ] **Step 2: Run the script**

```bash
bullion-live-map/.venv-narration/bin/python3 bullion-live-map/scripts/generate_narration.py
```

Expected: 8 `wrote ...` lines, no traceback.

- [ ] **Step 3: Verify the 8 output files exist and are plausible**

```bash
bullion-live-map/.venv-narration/bin/python3 -c "
from pathlib import Path
import torchaudio as ta

expected = ['node-fed.mp3','node-gold.mp3','node-vix.mp3','node-sec.mp3',
            'node-repo.mp3','node-yield.mp3','link-credit-equit.mp3','link-usd-oil.mp3']
out_dir = Path('bullion-live-map/audio/narration')
for name in expected:
    p = out_dir / name
    assert p.exists(), f'missing {p}'
    assert p.stat().st_size > 0, f'empty {p}'
    info = ta.info(str(p))
    duration = info.num_frames / info.sample_rate
    assert 1 < duration < 60, f'{name} duration looks wrong: {duration:.1f}s'
    print(f'{name}: {duration:.1f}s, {p.stat().st_size} bytes')
print('OK: all 8 files present and plausible')
"
```

Expected: 8 lines of duration/size info, then `OK: all 8 files present and plausible`. No leftover `.wav` files should remain in `audio/narration/` (Step 1's script deletes them after conversion) — confirm with `ls bullion-live-map/audio/narration/` showing only the 8 `.mp3` files.

- [ ] **Step 4: Commit the script and the generated audio**

```bash
git add bullion-live-map/scripts/generate_narration.py bullion-live-map/audio/narration/*.mp3
git commit -m "Add narration generation script and 8 pilot MP3 clips"
```

---

### Task 4: Front-end wiring in `bullion_mk18.html`

**Files:**
- Modify: `bullion-live-map/bullion_mk18.html`

**Interfaces:**
- Consumes: the 8 filenames from Task 3 (only the 6 `node-*.mp3` ones apply here — `mk18.html` has no field notes).
- Produces: `NARRATION_MANIFEST` (object, node id → filename) and `playNarration(file)` (function), both referenced identically in Task 5's `mkultra.html` wiring — keep the implementation of `playNarration` byte-for-byte identical across both files.

- [ ] **Step 0: Capture the freeze-check baseline**

Before making any edit in this task, record the current hashes of the files this plan must never touch, for Task 6 to diff against:

```bash
cd bullion-live-map
shasum -a 256 bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html | tee /tmp/bullion-freeze-baseline.txt
```

Expected: 7 lines of `<hash>  <filename>` written both to the terminal and to `/tmp/bullion-freeze-baseline.txt`.

- [ ] **Step 1: Add CSS for the narrate button**

In `bullion_mk18.html`, find this existing rule (around line 183):
```css
  #detail-close { background: none; border: none; color: var(--text-dim); font-size: 20px; cursor: pointer; line-height: 1; padding: 2px 6px; }
  #detail-close:hover { color: var(--text); }
```
Replace it with (adds a flex wrapper for the two header buttons plus the new button's own style):
```css
  .detail-header-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
  .narrate-btn { background: none; border: 1px solid var(--border); border-radius: 6px; color: var(--gold-dim); font-size: 14px; cursor: pointer; line-height: 1; padding: 3px 7px; }
  .narrate-btn:hover { color: var(--gold); border-color: var(--gold-dim); }
  #detail-close { background: none; border: none; color: var(--text-dim); font-size: 20px; cursor: pointer; line-height: 1; padding: 2px 6px; }
  #detail-close:hover { color: var(--text); }
```

- [ ] **Step 2: Add the button markup**

Find (around line 524-531):
```html
<div id="detail-panel">
  <div id="detail-header">
    <div>
      <div id="detail-title">—</div>
      <div id="detail-layer">—</div>
    </div>
    <button id="detail-close">&times;</button>
  </div>
```
Replace with:
```html
<div id="detail-panel">
  <div id="detail-header">
    <div>
      <div id="detail-title">—</div>
      <div id="detail-layer">—</div>
    </div>
    <div class="detail-header-actions">
      <button id="detail-narrate" class="narrate-btn" title="Play narration" hidden>&#128266;</button>
      <button id="detail-close">&times;</button>
    </div>
  </div>
```
(`&#128266;` is the 🔊 emoji — used as an HTML entity here since the surrounding markup in this file favors entities like `&times;` over raw Unicode.)

- [ ] **Step 3: Add the manifest and helper function**

Find (around line 3291, the line right after the closing `};` of `NODE_LIVE_FIELD` and before `function updateMetrics() {`):
```js
  nfp: ['nfp_mom'], cpi: ['cpi_yoy'], ffr: ['ffr'],
};
function updateMetrics() {
```
Replace with:
```js
  nfp: ['nfp_mom'], cpi: ['cpi_yoy'], ffr: ['ffr'],
};
// Pilot voice narration: node id -> pre-generated MP3 filename under
// audio/narration/. No entry means no button — see
// docs/superpowers/specs/2026-07-30-bullion-voice-narration-design.md.
const NARRATION_MANIFEST = {
  fed:   'node-fed.mp3',
  gold:  'node-gold.mp3',
  vix:   'node-vix.mp3',
  sec:   'node-sec.mp3',
  repo:  'node-repo.mp3',
  yield: 'node-yield.mp3',
};
function playNarration(file) {
  new Audio('audio/narration/' + file).play().catch(function(err) {
    console.warn('Narration playback failed:', err);
  });
}
function updateMetrics() {
```

- [ ] **Step 4: Wire the button into `openDetail()`**

Find (around line 1942-1945):
```js
function openDetail(d) {
  openDetailNode = d;
  document.getElementById('detail-title').textContent = d.label;
  document.getElementById('detail-layer').textContent = LAYER_LABELS[d.group] || '';
```
Replace with:
```js
function openDetail(d) {
  openDetailNode = d;
  document.getElementById('detail-title').textContent = d.label;
  document.getElementById('detail-layer').textContent = LAYER_LABELS[d.group] || '';
  const narrateBtn = document.getElementById('detail-narrate');
  if (narrateBtn) {
    if (NARRATION_MANIFEST[d.id]) {
      narrateBtn.hidden = false;
      narrateBtn.onclick = function() { playNarration(NARRATION_MANIFEST[d.id]); };
    } else {
      narrateBtn.hidden = true;
      narrateBtn.onclick = null;
    }
  }
```

- [ ] **Step 5: Headless-Chrome DOM probe**

```bash
rm -rf /tmp/bullion-narr-mk18-probe && mkdir -p /tmp/bullion-narr-mk18-probe
cp bullion-live-map/bullion_mk18.html bullion-live-map/data.json /tmp/bullion-narr-mk18-probe/
```

Write the probe injection to a temp file, then insert it before the last `</body>` (use `str.rfind`, not `find` — there is an earlier decoy `</body>` inside a JS string literal in this file):

```bash
python3 -c "
path = '/tmp/bullion-narr-mk18-probe/bullion_mk18.html'
html = open(path, encoding='utf-8').read()
probe = '''<script>
try {
  const pilot = ['fed','gold','vix','sec','repo','yield'];
  const results = [];
  for (const n of NODES) {
    openDetail(n);
    const btn = document.getElementById('detail-narrate');
    const shouldShow = pilot.includes(n.id);
    const isShown = !btn.hidden;
    results.push(n.id + ':' + (shouldShow === isShown ? 'PASS' : 'FAIL(expected show=' + shouldShow + ' got ' + isShown + ')'));
  }
  console.log('PROBE_RESULTS ' + results.join(' '));
  console.log('PROBE_DONE');
} catch (e) {
  console.log('PROBE_ERROR ' + e.message);
}
</script>'''
idx = html.rfind('</body>')
html = html[:idx] + probe + html[idx:]
open(path, 'w', encoding='utf-8').write(html)
"

rm -rf /tmp/bullion-narr-mk18-profile && mkdir -p /tmp/bullion-narr-mk18-profile
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --allow-file-access-from-files --virtual-time-budget=15000 \
  --enable-logging=stderr --v=1 \
  --user-data-dir=/tmp/bullion-narr-mk18-profile \
  --disable-gpu \
  "file:///tmp/bullion-narr-mk18-probe/bullion_mk18.html" 2>/tmp/bullion-narr-mk18-chrome.log

grep "PROBE_\|SyntaxError\|Uncaught\|ReferenceError" /tmp/bullion-narr-mk18-chrome.log
```

Expected: one line starting `PROBE_RESULTS` containing 39 `id:PASS` entries (no `FAIL`), followed by `PROBE_DONE`, and no `SyntaxError`/`Uncaught`/`ReferenceError` lines. If any `FAIL` appears, fix the wiring in Steps 1-4 before proceeding — do not report this task done on a probe that shows a FAIL.

---

### Task 5: Front-end wiring in `bullion_mkultra.html`

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html`

**Interfaces:**
- Consumes: all 8 filenames from Task 3. Reuses the identical `playNarration(file)` implementation from Task 4.
- Produces: `NARRATION_MANIFEST` and `NARRATION_LINKS` (object, `"<source>-<target>"` → filename), both local to this file (this app is a separate standalone HTML file from `mk18.html`, not a shared module — duplication across the two files is intentional per the spec's architecture, not a bug to dedupe).

- [ ] **Step 1: Add CSS for both narrate buttons**

Find (around line 212):
```css
  #detail-close { background: none; border: none; color: var(--text-dim); font-size: 20px; cursor: pointer; line-height: 1; padding: 2px 6px; }
```
Replace with:
```css
  .detail-header-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
  .narrate-btn { background: none; border: 1px solid var(--border); border-radius: 6px; color: var(--gold-dim); font-size: 14px; cursor: pointer; line-height: 1; padding: 3px 7px; }
  .narrate-btn:hover { color: var(--gold); border-color: var(--gold-dim); }
  #detail-close { background: none; border: none; color: var(--text-dim); font-size: 20px; cursor: pointer; line-height: 1; padding: 2px 6px; }
```

Find (around line 244-245):
```css
  .rel-field-note { display: block; margin-top: 6px; padding-top: 6px; border-top: 1px dashed rgba(212,184,105,0.4); font-family: var(--font-display); font-style: italic; color: var(--text); font-size: 12px; line-height: 1.45; }
  .rel-field-note::before { content: "— "; color: var(--gold-dim); }
```
Replace with:
```css
  .rel-field-note { display: block; margin-top: 6px; padding-top: 6px; border-top: 1px dashed rgba(212,184,105,0.4); font-family: var(--font-display); font-style: italic; color: var(--text); font-size: 12px; line-height: 1.45; }
  .rel-field-note::before { content: "— "; color: var(--gold-dim); }
  .rel-field-note-narrate { background: none; border: none; color: var(--gold-dim); font-size: 12px; cursor: pointer; margin-left: 6px; padding: 0 2px; vertical-align: middle; }
  .rel-field-note-narrate:hover { color: var(--gold); }
```

- [ ] **Step 2: Add the button markup in `#detail-header`**

Find (around line 574-581):
```html
<div id="detail-panel">
  <div id="detail-header">
    <div>
      <div id="detail-title">—</div>
      <div id="detail-layer">—</div>
    </div>
    <button id="detail-close">&times;</button>
  </div>
```
Replace with:
```html
<div id="detail-panel">
  <div id="detail-header">
    <div>
      <div id="detail-title">—</div>
      <div id="detail-layer">—</div>
    </div>
    <div class="detail-header-actions">
      <button id="detail-narrate" class="narrate-btn" title="Play narration" hidden>&#128266;</button>
      <button id="detail-close">&times;</button>
    </div>
  </div>
```

- [ ] **Step 3: Add both manifests and the helper function**

Find (around line 3949, right after `NODE_LIVE_FIELD`'s closing `};`):
```js
  nfp: ['nfp_mom'], cpi: ['cpi_yoy'], ffr: ['ffr'],
};

// Metric cell id suffix -> data.json field name.
```
Replace with:
```js
  nfp: ['nfp_mom'], cpi: ['cpi_yoy'], ffr: ['ffr'],
};
// Pilot voice narration: node id -> pre-generated MP3 filename, and
// "<source>-<target>" link id -> field-note MP3 filename, both under
// audio/narration/. No entry means no button — see
// docs/superpowers/specs/2026-07-30-bullion-voice-narration-design.md.
const NARRATION_MANIFEST = {
  fed:   'node-fed.mp3',
  gold:  'node-gold.mp3',
  vix:   'node-vix.mp3',
  sec:   'node-sec.mp3',
  repo:  'node-repo.mp3',
  yield: 'node-yield.mp3',
};
const NARRATION_LINKS = {
  'credit-equit': 'link-credit-equit.mp3',
  'usd-oil':      'link-usd-oil.mp3',
};
function playNarration(file) {
  new Audio('audio/narration/' + file).play().catch(function(err) {
    console.warn('Narration playback failed:', err);
  });
}

// Metric cell id suffix -> data.json field name.
```

- [ ] **Step 4: Wire the node button into `openDetail()`**

Find (around line 2579-2587):
```js
function openDetail(d) {
  openDetailNode = d;
  document.getElementById('detail-title').textContent = d.label;
  // Group = what kind of thing it is; stage = where it sits in the causal flow
  // (the classification that used to float on the 3D globe, now shown here).
  const _group = LAYER_LABELS[d.group] || '';
  const _stage = COLUMN_TITLES[d.col] || '';
  document.getElementById('detail-layer').innerHTML =
    _group + (_stage ? ' <span class="detail-stage">· ' + _stage + '</span>' : '');
```
Replace with:
```js
function openDetail(d) {
  openDetailNode = d;
  document.getElementById('detail-title').textContent = d.label;
  // Group = what kind of thing it is; stage = where it sits in the causal flow
  // (the classification that used to float on the 3D globe, now shown here).
  const _group = LAYER_LABELS[d.group] || '';
  const _stage = COLUMN_TITLES[d.col] || '';
  document.getElementById('detail-layer').innerHTML =
    _group + (_stage ? ' <span class="detail-stage">· ' + _stage + '</span>' : '');
  const narrateBtn = document.getElementById('detail-narrate');
  if (narrateBtn) {
    if (NARRATION_MANIFEST[d.id]) {
      narrateBtn.hidden = false;
      narrateBtn.onclick = function() { playNarration(NARRATION_MANIFEST[d.id]); };
    } else {
      narrateBtn.hidden = true;
      narrateBtn.onclick = null;
    }
  }
```

- [ ] **Step 5: Wire the field-note button into the relationship row renderer**

Find (around line 2546):
```js
          (r.l.fieldNote ? '<div class="rel-field-note">' + enrichText(r.l.fieldNote) + '</div>' : '') +
```
Replace with:
```js
          (r.l.fieldNote ? '<div class="rel-field-note">' + enrichText(r.l.fieldNote) +
            (NARRATION_LINKS[r.l.s + '-' + r.l.t] ? ' <button class="rel-field-note-narrate" title="Play narration" onclick="playNarration(\'' + NARRATION_LINKS[r.l.s + '-' + r.l.t] + '\')">&#128266;</button>' : '') +
            '</div>' : '') +
```

- [ ] **Step 6: Headless-Chrome DOM probe**

```bash
rm -rf /tmp/bullion-narr-mkultra-probe && mkdir -p /tmp/bullion-narr-mkultra-probe
cp bullion-live-map/bullion_mkultra.html bullion-live-map/data.json /tmp/bullion-narr-mkultra-probe/

python3 -c "
path = '/tmp/bullion-narr-mkultra-probe/bullion_mkultra.html'
html = open(path, encoding='utf-8').read()
probe = '''<script>
try {
  const pilotNodes = ['fed','gold','vix','sec','repo','yield'];
  const pilotLinks = ['credit-equit','usd-oil'];
  const results = [];
  for (const n of NODES) {
    openDetail(n);
    const btn = document.getElementById('detail-narrate');
    const shouldShow = pilotNodes.includes(n.id);
    const isShown = !btn.hidden;
    results.push('node:' + n.id + ':' + (shouldShow === isShown ? 'PASS' : 'FAIL'));
  }
  const allLinks = LINKS.concat(PLUMBING_LINKS);
  let fieldNoteLinksSeen = 0;
  for (const l of allLinks) {
    if (!l.fieldNote) continue;
    fieldNoteLinksSeen++;
    const key = l.s + '-' + l.t;
    const shouldHaveClip = pilotLinks.includes(key);
    const hasClip = !!NARRATION_LINKS[key];
    results.push('link:' + key + ':' + (shouldHaveClip === hasClip ? 'PASS' : 'FAIL'));
  }
  results.push('fieldNoteLinksSeen:' + fieldNoteLinksSeen);
  console.log('PROBE_RESULTS ' + results.join(' '));
  console.log('PROBE_DONE');
} catch (e) {
  console.log('PROBE_ERROR ' + e.message);
}
</script>'''
idx = html.rfind('</body>')
html = html[:idx] + probe + html[idx:]
open(path, 'w', encoding='utf-8').write(html)
"

rm -rf /tmp/bullion-narr-mkultra-profile && mkdir -p /tmp/bullion-narr-mkultra-profile
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --allow-file-access-from-files --virtual-time-budget=15000 \
  --enable-logging=stderr --v=1 \
  --user-data-dir=/tmp/bullion-narr-mkultra-profile \
  --disable-gpu \
  "file:///tmp/bullion-narr-mkultra-probe/bullion_mkultra.html" 2>/tmp/bullion-narr-mkultra-chrome.log

grep "PROBE_\|SyntaxError\|Uncaught\|ReferenceError" /tmp/bullion-narr-mkultra-chrome.log
```

Expected: `PROBE_RESULTS` containing 39 `node:*:PASS` entries, 2 `link:*:PASS` entries (`credit-equit` and `usd-oil`), `fieldNoteLinksSeen:2`, then `PROBE_DONE`. No `SyntaxError`/`Uncaught`/`ReferenceError`. Do not proceed to Task 6 on any `FAIL`.

**Do not call `openAuditLog()`** in this or any probe — its animated modal stalls headless virtual-time and hangs the run (known issue in this project).

- [ ] **Step 7: Commit both files**

```bash
git add bullion-live-map/bullion_mk18.html bullion-live-map/bullion_mkultra.html
git commit -m "Wire pilot voice narration into mk18 and mkultra front ends"
```

---

### Task 6: Full verification pass

**Files:** none created/modified — this task only runs checks.

**Interfaces:** none — terminal task.

- [ ] **Step 1: Freeze-check unrelated files**

```bash
cd bullion-live-map
shasum -a 256 bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html | diff /tmp/bullion-freeze-baseline.txt -
```
Expected: no output (empty diff) against the baseline captured in Task 4, Step 0 — these files must be byte-identical to their state at the start of this plan, since nothing in this plan should touch them. If the diff shows any change, stop and investigate before continuing; something outside this plan's intended scope changed.

- [ ] **Step 2: Run the existing Python suite**

```bash
cd bullion-live-map && python3 -m unittest discover -s tests && python3 -m unittest test_calibrate
```
Expected: all tests pass. This is unrelated to the JS/audio work but is cheap to re-run per project convention, and confirms this effort didn't collaterally break the Python side.

- [ ] **Step 3: Confirm CSP allows same-origin audio playback (real browser)**

Open `bullion-live-map/bullion_mk18.html` directly in real (non-headless) Chrome — e.g. via `open bullion-live-map/bullion_mk18.html` — click a pilot node (e.g. "Federal Reserve"), click the 🔊 button, and open DevTools → Console. Confirm there is **no** `Content-Security-Policy` violation logged and that audio is audible. This resolves the spec's open "CSP: assumed, not yet confirmed" risk. Repeat once for `bullion_mkultra.html`, testing one node clip and one field-note clip (open the "Credit Markets" node's relationships panel to find the `credit → equit` field note).

- [ ] **Step 4: Manual full audio check (real Chrome, both files)**

Click through all 6 pilot node 🔊 buttons in `bullion_mk18.html` and confirm each plays and sounds correct (matches the node's beginner text, audible, not corrupted). Repeat for all 6 pilot nodes plus both field-note 🔊 buttons in `bullion_mkultra.html` (8 clips total per file for nodes, 2 additional for mkultra's field notes). Headless Chrome cannot verify audible sound, so this step must be done in a real browser session — report explicitly which clips you personally listened to and confirmed, don't infer this from the DOM probes in Tasks 4/5.

- [ ] **Step 5: Confirm no non-pilot node or link shows a button**

While in real Chrome from Step 4, click through at least 3 non-pilot nodes (e.g. "SEC" — wait, `sec` IS pilot; use e.g. "FDIC", "CFTC", "Treasury") and confirm no 🔊 button appears, and check a non-pilot link's relationship detail (e.g. any link without a `fieldNote`) shows no 🔊 button either. This is a spot-check on top of the headless probes' exhaustive 39-node sweep in Tasks 4/5.

---

## Execution Handoff

Once this plan is saved, the two options are:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, with review between tasks.
2. **Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Note for whichever is chosen: **Task 2 requires a real pause for user input** (the voice recording) — it cannot be delegated to a subagent that has no way to ask the user directly and wait for a reply out-of-band. If subagent-driven execution is chosen, Task 2 should either be run in the orchestrating session directly, or the subagent given clear instructions to stop and report back once it needs the recording, rather than attempting to synthesize/fake one.
