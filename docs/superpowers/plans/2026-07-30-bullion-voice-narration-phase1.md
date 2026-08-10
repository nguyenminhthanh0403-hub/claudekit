# Bullion Voice Narration Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Expand voice narration from the 6-node pilot to all 39 nodes, replacing
`scripts/generate_narration.py`'s hardcoded `NARRATIONS` dict with an HTML-extraction
step, and expanding `NARRATION_MANIFEST` to 39 entries in both `bullion_mk18.html` and
`bullion_mkultra.html`.

**Architecture:** The generation script injects a small probe `<script>` into a
temp copy of `bullion_mk18.html` (before the real closing `</body>`, not the decoy one
inside a JS string), runs it in isolated headless Chrome to get
`JSON.stringify(NODES.map(...))` out via `document.title`, generates one MP3 per node
through the existing Chatterbox pipeline, and both HTML files' manifests are hand-edited
to the resulting 39-entry map (both files share the audio directory and both `NODES`
arrays are byte-identical, so one extraction pass covers both).

**Tech Stack:** Python (`torchaudio`, `chatterbox`, unchanged from the pilot), real
Chrome in headless mode via `subprocess` (no Selenium/Playwright dependency added),
`ffmpeg` for MP3 encoding (unchanged from the pilot).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-30-bullion-voice-narration-phase1-design.md` —
  read it before starting; this plan implements it exactly.
- Pilot spec (background/pattern reference, not modified by this plan):
  `docs/superpowers/specs/2026-07-30-bullion-voice-narration-design.md`.
- The narration Python env already exists at `bullion-live-map/.venv-narration` (used by
  the pilot) — activate it (`source bullion-live-map/.venv-narration/bin/activate`)
  rather than creating a new one.
- Chrome binary on this Mac: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- **Always use an isolated `--user-data-dir=$(mktemp -d)` for every headless Chrome
  invocation** — this project's standing convention, never launch against a shared
  profile.
- `bullion_mk18.html` has a decoy `</body>` at line 3864 inside a JS template string
  (`'</style></head><body>' + html + '</body></html>'`) — the real closing tag is at
  line 4459. Any script-injection step MUST use `text.rfind('</body>')`
  (Python: `str.rfind`), never `str.find`, or the probe script will be inserted into the
  wrong place and silently never run.
- Never call `openAuditLog()` inside a probe script — its animated modal stalls headless
  Chrome's virtual time and hangs the process.
- Freeze-check: `bullion_mk11.html` through `bullion_mk17.html` must stay byte-identical
  — this plan touches only `mk18`, `mkultra`, `scripts/generate_narration.py`, and
  `audio/narration/*.mp3`.
- Never `git add .` / `git add -A` — see the pre-existing untracked-file list in the
  UI-fixes plan's Global Constraints (same repo, same list applies). Stage only the
  exact files each task modifies.
- No `--no-verify`, no skipping hooks.

---

### Task 1: Rewrite `generate_narration.py` to extract text from the HTML

**Files:**
- Modify: `bullion-live-map/scripts/generate_narration.py` (currently 81 lines, hardcoded
  `NARRATIONS` dict at lines 22-53)
- Test: `bullion-live-map/scripts/test_generate_narration.py` (new)

**Interfaces:**
- Produces: `extract_node_texts(html_path: Path) -> list[dict]` — each dict is
  `{"id": str, "text": str}`, one per node, in `NODES` array order. Raises
  `RuntimeError` on any extraction failure (Chrome fails to launch, no `<title>` found
  in the dumped DOM, or the extracted JSON doesn't parse) — no silent fallback.
- Consumes: nothing from other tasks (this task is self-contained).
- Task 3 consumes: the fact that after this task, `generate_narration.py` writes one
  `node-<id>.mp3` per entry returned by `extract_node_texts`, plus the 2 pre-existing
  `link-*.mp3` files untouched.

- [x] **Step 1: Write the failing test for `extract_node_texts`**

  ```python
  # bullion-live-map/scripts/test_generate_narration.py
  import sys
  import unittest
  from pathlib import Path

  sys.path.insert(0, str(Path(__file__).resolve().parent))
  import generate_narration as gn

  ROOT = Path(__file__).resolve().parent.parent

  class TestExtractNodeTexts(unittest.TestCase):
      def test_extracts_all_39_nodes(self):
          nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
          self.assertEqual(len(nodes), 39)

      def test_each_node_has_id_and_nonempty_text(self):
          nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
          for n in nodes:
              self.assertIn("id", n)
              self.assertIn("text", n)
              self.assertTrue(n["text"].strip())

      def test_known_pilot_node_text_matches_pilot_wording(self):
          nodes = {n["id"]: n["text"] for n in gn.extract_node_texts(ROOT / "bullion_mk18.html")}
          self.assertEqual(
              nodes["fed"],
              "The central bank that controls interest rates and money supply. "
              "It keeps prices stable, supports jobs, and lends as a last resort in crises."
          )

  if __name__ == "__main__":
      unittest.main()
  ```

- [x] **Step 2: Run it to verify it fails**

  ```bash
  cd bullion-live-map && source .venv-narration/bin/activate
  python3 -m unittest scripts.test_generate_narration -v
  ```

  Expected: FAIL — `AttributeError: module 'generate_narration' has no attribute
  'extract_node_texts'`.

- [x] **Step 3: Implement `extract_node_texts`**

  Replace the top of `generate_narration.py` (imports + the hardcoded `NARRATIONS`
  dict) with:

  ```python
  #!/usr/bin/env python3
  """Phase 1: generates all 39 node narration MP3s in the user's cloned voice.
  Text is extracted from bullion_mk18.html's live NODES array at generation
  time (never hardcoded), so narration can't silently drift from the on-page
  text the way a hand-copied dict could."""
  import json
  import re
  import subprocess
  import sys
  import tempfile
  from pathlib import Path

  import torchaudio as ta
  from chatterbox.tts import ChatterboxTTS

  ROOT = Path(__file__).resolve().parent.parent
  VOICE_SAMPLE = ROOT / "audio" / "voice_sample" / "user_voice.wav"
  OUTPUT_DIR = ROOT / "audio" / "narration"
  SOURCE_HTML = ROOT / "bullion_mk18.html"
  CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

  PROBE_SCRIPT = (
      "<script>document.title = 'NODE_TEXT_JSON:' + "
      "JSON.stringify(NODES.map(function(n){"
      "return {id: n.id, text: n.beginner.join(' ')};"
      "}));</script>"
  )


  def extract_node_texts(html_path):
      """Injects a probe script before html_path's REAL closing </body> (there is
      a decoy </body> inside a JS string mid-file — must use rfind, never
      find), runs it in isolated headless Chrome, and returns the node list.
      Raises RuntimeError on any failure; never falls back to stale text."""
      html_text = html_path.read_text()
      idx = html_text.rfind("</body>")
      if idx == -1:
          raise RuntimeError(f"No </body> found in {html_path}")
      patched = html_text[:idx] + PROBE_SCRIPT + html_text[idx:]

      with tempfile.TemporaryDirectory() as tmp:
          tmp_path = Path(tmp)
          probe_html = tmp_path / "probe.html"
          probe_html.write_text(patched)
          user_data_dir = tmp_path / "chrome-profile"

          result = subprocess.run(
              [
                  CHROME, "--headless=new", "--disable-gpu",
                  f"--user-data-dir={user_data_dir}",
                  "--virtual-time-budget=5000",
                  "--dump-dom",
                  f"file://{probe_html}",
              ],
              capture_output=True, text=True, timeout=60,
          )
          if result.returncode != 0:
              raise RuntimeError(f"headless Chrome failed: {result.stderr}")

          match = re.search(r"<title>NODE_TEXT_JSON:(.*?)</title>", result.stdout, re.S)
          if not match:
              raise RuntimeError(
                  "Probe script never ran or NODES was empty — no NODE_TEXT_JSON "
                  "title found in dumped DOM."
              )
          try:
              return json.loads(match.group(1))
          except json.JSONDecodeError as e:
              raise RuntimeError(f"Extracted JSON failed to parse: {e}")
  ```

- [x] **Step 4: Run the test to verify it passes**

  ```bash
  cd bullion-live-map && source .venv-narration/bin/activate
  python3 -m unittest scripts.test_generate_narration -v
  ```

  Expected: 3 tests PASS.

- [x] **Step 5: Rewrite `main()` to use extraction instead of the hardcoded dict**

  Replace the rest of `generate_narration.py` (the old `main()` that iterated
  `NARRATIONS.items()`) with:

  ```python
  def main():
      if not VOICE_SAMPLE.exists():
          sys.exit(f"Voice sample not found: {VOICE_SAMPLE}")
      OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

      nodes = extract_node_texts(SOURCE_HTML)
      print(f"Extracted {len(nodes)} node texts from {SOURCE_HTML.name}")

      model = ChatterboxTTS.from_pretrained(device="cpu")

      for node in nodes:
          filename = f"node-{node['id']}.mp3"
          text = node["text"]
          wav_tmp = OUTPUT_DIR / (filename[:-4] + ".wav")
          mp3_out = OUTPUT_DIR / filename

          wav = model.generate(text, audio_prompt_path=str(VOICE_SAMPLE))
          ta.save(str(wav_tmp), wav, model.sr)

          subprocess.run(
              ["ffmpeg", "-y", "-i", str(wav_tmp), "-af", "afftdn=nf=-25",
               "-codec:a", "libmp3lame", "-qscale:a", "2", str(mp3_out)],
              check=True,
          )
          wav_tmp.unlink()
          print(f"wrote {mp3_out}")


  if __name__ == "__main__":
      main()
  ```

  Note: this intentionally does NOT touch `link-credit-equit.mp3` /
  `link-usd-oil.mp3` — those are the pilot's field-note clips, out of scope for this
  Phase 1 (node-only) effort.

- [x] **Step 6: Commit**

  ```bash
  git add bullion-live-map/scripts/generate_narration.py bullion-live-map/scripts/test_generate_narration.py
  git commit -m "$(cat <<'EOF'
  Extract node narration text from bullion_mk18.html instead of hardcoding it

  Phase 1 needs all 39 nodes covered, not the pilot's fixed 6, so a
  hand-copied dict risks drifting from the on-page text. generate_narration.py
  now injects a probe script into an isolated headless Chrome tab and reads
  NODES directly.

  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  EOF
  )"
  ```

---

### Task 2: Generate all 39 node MP3s and expand both manifests

**Files:**
- Modify: `bullion-live-map/audio/narration/*.mp3` (regenerates the 6 existing files,
  adds 33 new ones — 39 total)
- Modify: `bullion-live-map/bullion_mk18.html` (`NARRATION_MANIFEST`, currently lines
  3309-3317)
- Modify: `bullion-live-map/bullion_mkultra.html` (`NARRATION_MANIFEST`, currently lines
  3972-3980 — confirm exact lines with `grep -n "NARRATION_MANIFEST" bullion_mkultra.html`
  before editing)

**Interfaces:**
- Consumes: `extract_node_texts` from Task 1 (run via `python3 scripts/generate_narration.py`,
  not called directly).
- Produces: 39 files under `audio/narration/node-<id>.mp3`, one per `NODES[i].id`; both
  HTML files' `NARRATION_MANIFEST` objects with exactly those 39 keys.

- [x] **Step 1: Get the full list of node ids in `NODES` order**

  ```bash
  cd bullion-live-map && source .venv-narration/bin/activate
  python3 -c "
  import sys; sys.path.insert(0, 'scripts')
  import generate_narration as gn
  nodes = gn.extract_node_texts(gn.SOURCE_HTML)
  print(len(nodes))
  for n in nodes: print(n['id'])
  "
  ```

  Expected: `39` printed first, followed by 39 unique ids. Save this list — Step 4
  compares against it.

- [x] **Step 2: Run the generation script**

  ```bash
  cd bullion-live-map && source .venv-narration/bin/activate
  python3 scripts/generate_narration.py
  ```

  This is expected to take substantially longer than the pilot's 8-clip run (unverified
  scaling per the spec's risk note — do not assume a proportional 39/8 multiplier,
  just let it run to completion). Confirm it exits 0 and prints 39 `wrote ...` lines.

- [x] **Step 3: Confirm 39 files exist and none are empty**

  ```bash
  cd bullion-live-map
  ls audio/narration/node-*.mp3 | wc -l
  find audio/narration/node-*.mp3 -size 0
  ```

  Expected: `39` for the count, empty output for the size-0 check (no zero-byte files).

- [x] **Step 4: Expand `NARRATION_MANIFEST` in `bullion_mk18.html`**

  Replace the existing 6-entry object:

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

  with one entry per id from Step 1's list, each pointing at `node-<id>.mp3`. Generate
  the object body programmatically rather than hand-typing 39 lines, e.g.:

  ```bash
  cd bullion-live-map && source .venv-narration/bin/activate
  python3 -c "
  import sys; sys.path.insert(0, 'scripts')
  import generate_narration as gn
  nodes = gn.extract_node_texts(gn.SOURCE_HTML)
  print('const NARRATION_MANIFEST = {')
  for n in nodes:
      print(f\"  {n['id']}: 'node-{n['id']}.mp3',\")
  print('};')
  "
  ```

  Paste this generated block over the old 6-entry object at
  `bullion_mk18.html`'s `NARRATION_MANIFEST` location, keeping the existing comment
  above it (update the comment to note Phase 1 full coverage instead of "Pilot").

- [x] **Step 5: Mirror the same manifest into `bullion_mkultra.html`**

  Same generated block from Step 4, replacing `bullion_mkultra.html`'s own
  `NARRATION_MANIFEST` (confirm its current line range with
  `grep -n "NARRATION_MANIFEST" bullion_mkultra.html` first — it duplicates the same 6
  entries independently and needs the same 39-entry replacement).

- [x] **Step 6: Commit**

  ```bash
  git add bullion-live-map/audio/narration bullion-live-map/bullion_mk18.html bullion-live-map/bullion_mkultra.html
  git commit -m "$(cat <<'EOF'
  Generate all 39 node narration clips and expand both manifests

  Regenerates the 6 pilot clips plus 33 new ones through the new
  extraction-based pipeline, and expands NARRATION_MANIFEST in both
  bullion_mk18.html and bullion_mkultra.html from 6 to 39 entries.

  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  EOF
  )"
  ```

---

### Task 3: Completeness check + browser verification + regression

**Files:**
- Test: `bullion-live-map/scripts/test_generate_narration.py` (extend from Task 1)

**Interfaces:**
- Consumes: `NARRATION_MANIFEST` (39 entries) from Task 2 in both HTML files;
  `extract_node_texts` from Task 1.

- [x] **Step 1: Write the failing completeness test**

  Add to `bullion-live-map/scripts/test_generate_narration.py`:

  ```python
  class TestManifestCompleteness(unittest.TestCase):
      def _manifest_ids(self, html_path):
          text = html_path.read_text()
          start = text.index("const NARRATION_MANIFEST = {")
          end = text.index("};", start)
          body = text[start:end]
          import re
          return set(re.findall(r"^\s*(\w+):", body, re.M))

      def test_mk18_manifest_covers_every_node(self):
          nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
          node_ids = {n["id"] for n in nodes}
          manifest_ids = self._manifest_ids(ROOT / "bullion_mk18.html")
          self.assertEqual(node_ids, manifest_ids)

      def test_mkultra_manifest_covers_every_node(self):
          nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
          node_ids = {n["id"] for n in nodes}
          manifest_ids = self._manifest_ids(ROOT / "bullion_mkultra.html")
          self.assertEqual(node_ids, manifest_ids)

      def test_every_manifest_file_exists_and_nonempty(self):
          nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
          for n in nodes:
              f = ROOT / "audio" / "narration" / f"node-{n['id']}.mp3"
              self.assertTrue(f.exists(), f"missing {f}")
              self.assertGreater(f.stat().st_size, 0, f"empty {f}")
  ```

- [x] **Step 2: Run it to verify current state**

  ```bash
  cd bullion-live-map && source .venv-narration/bin/activate
  python3 -m unittest scripts.test_generate_narration -v
  ```

  Expected: all tests PASS (Task 2 already produced complete coverage — this test
  exists to catch future regressions, e.g. someone adding a 40th node without
  regenerating audio).

- [x] **Step 3: Verify the 🔊 button appears for all 39 nodes in a real browser tab**

  ```bash
  cd bullion-live-map && lsof -i :8791 || python3 -m http.server 8791 > /tmp/bullion-http-server.log 2>&1 &
  ```

  Using the claude-in-chrome tools, navigate to
  `http://localhost:8791/bullion_mk18.html`, then via the JavaScript tool run:

  ```js
  NODES.map(n => [n.id, !!NARRATION_MANIFEST[n.id]]).filter(([,has]) => !has)
  ```

  Expected: `[]` (empty array — every node has a manifest entry). Repeat for
  `http://localhost:8791/bullion_mkultra.html`.

- [x] **Step 4: Manual listen-through spot-check**

  Pick 6-8 node ids spanning different `group` values (e.g. one regulator, one
  commercial-banking, one shadow-banking, one infrastructure, one crypto/fintech node,
  plus 2-3 more). For each, open its detail panel in a real (non-automated, focused)
  Chrome tab and click the 🔊 button — confirm it's audible and sounds correct. This
  cannot be verified by headless automation (Chrome throttles audio byte-fetch in
  background/automated tabs even though `.play()` resolves without error) — this step
  requires the user in a real focused tab.

- [x] **Step 5: Freeze-check mk11–mk17 are untouched**

  ```bash
  cd bullion-live-map
  shasum -a 256 bullion_mk{11,12,13,14,15,16,17}.html
  ```

  Compare against the pre-Task-1 commit — all 7 must be identical.

- [x] **Step 6: Run the Python suite**

  ```bash
  cd bullion-live-map && python3 -m unittest discover -s tests && python3 -m unittest test_calibrate
  ```

  Expected: same pass count as before this effort (41/41 + 33/33 as of the originating
  handoff) — plus the new `test_generate_narration` tests from this plan.

- [x] **Step 7: Commit the completeness test**

  ```bash
  git add bullion-live-map/scripts/test_generate_narration.py
  git commit -m "$(cat <<'EOF'
  Add manifest-completeness regression test for node narration

  Asserts every NODES id has a NARRATION_MANIFEST entry in both HTML
  files and that the corresponding audio file exists and is non-empty —
  catches a future node addition that forgets to regenerate narration.

  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  EOF
  )"
  ```

- [x] **Step 8: Push**

  ```bash
  GIT_TERMINAL_PROMPT=0 git push origin main
  ```

  Confirm with `git rev-list --left-right --count origin/main...main` reads `0 0`
  afterward.
