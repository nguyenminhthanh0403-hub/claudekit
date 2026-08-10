# Bullion UI Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add scenario-highlighting (which preset/dropdown is currently active) to
`bullion_mk18.html` and `bullion_mkultra.html`, and confirm the already-shipped
manual-drivers toggle fix actually resolves the user's original complaint.

**Architecture:** One new pure-DOM function, `setActiveScenario(type)`, toggles an
`active` class across the 5 preset `[data-shock]` buttons and the `#scenario-select`
dropdown. It's called from 3 existing functions (`triggerShock`, `resetState`,
`runManual`) — no new event listeners. A new CSS custom property,
`--scenario-active: #8b0000`, gives the dropdown a border/glow distinct from the
buttons' existing `.btn.active` gold fill.

**Tech Stack:** Vanilla JS, vanilla CSS, no build step, no test framework — this
project verifies DOM/JS behavior via a local HTTP server + a real/headless Chrome tab
(see Global Constraints), and has a separate unrelated Python `unittest` suite for
data-fetching logic.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-30-bullion-ui-fixes-design.md` — read it before
  starting; this plan implements it exactly.
- Both `bullion_mk18.html` and `bullion_mkultra.html` get the identical CSS/JS change,
  independently, at their own line numbers (they are separate standalone files, no
  shared module — this project's established duplicated-file pattern).
- `file://` URLs do NOT work with the claude-in-chrome browser tool. Always serve
  locally first: `cd bullion-live-map && python3 -m http.server <port>` (check
  `lsof -i :<port>` before starting a second server), then navigate to
  `http://localhost:<port>/bullion_mk18.html`.
- Freeze-check: `bullion_mk11.html` through `bullion_mk17.html` must stay byte-identical
  (`shasum -a 256`) — this plan touches only `mk18` and `mkultra`.
- Never `git add .` / `git add -A` — this repo has pre-existing untracked files
  (`docs/chrome-mcp-setup.md`, `docs/project-overview.md`, `.claude/`, `.agents/`,
  `.codex/`, `AGENTS.md`, `CLAUDE.md`, `.DS_Store` files, `bullion-live-map/__pycache__/`,
  `docs/superpowers/archive/`, others) that must NOT be staged. Stage only the exact
  files each task modifies.
- No `--no-verify`, no skipping hooks.

---

### Task 1: Add scenario-highlighting CSS + JS to `bullion_mk18.html`

**Files:**
- Modify: `bullion-live-map/bullion_mk18.html`
  - CSS: `:root` block (currently lines 24-38, ends with `--warn: #e0b15a;`)
  - CSS: near the existing `select.scenario-select` rules (currently lines 321-327)
  - JS: new function, placed immediately before `function triggerShock(type)`
    (currently line 3527)
  - JS: inside `triggerShock(type)` (currently lines 3527-3541)
  - JS: inside `resetState()` (currently lines 3543-3548)
  - JS: inside `runManual()` (currently lines 4074-4097), in the dirty branch (after the
    early-return guard on line 4075)

**Interfaces:**
- Produces: `function setActiveScenario(type)` — `type` is either a string matching one
  of the 5 `data-shock` values (`'rate_hike'`, `'vix_spike'`, `'cpi_rise'`,
  `'usd_shock'`, `'bank_stress'`) or a dropdown value, or `null` to clear all highlights.
  No return value. Task 2 (`bullion_mkultra.html`) implements its own independent copy
  of this same function — they do not share code.

- [x] **Step 1: Add the `--scenario-active` CSS custom property**

  In the `:root` block, add one line after the existing `--warn` line:

  ```css
  :root {
    --bg-deep:    #05060a;
    --bg-panel:   #0b0e16;
    --border:     #1e2436;
    --text:       #d8dce6;
    --text-dim:   #8891a6;
    --gold:       #d4b869;
    --gold-dim:   #a8925a;
    --green:      #7bbf8e;
    --red:        #e0654f;
    --amber:      #e0b15a;
    --up:         #e0654f;
    --down:       #7bbf8e;
    --warn:       #e0b15a;
    --scenario-active: #8b0000; /* deep blood-red, deliberately darker/more saturated
                                    than --red (used elsewhere for negative shock
                                    direction) so the two are never visually confused */
  }
  ```

- [x] **Step 2: Add the dropdown's active-state CSS rule**

  Immediately after the existing `select.scenario-select option { ... }` rule, add:

  ```css
  select.scenario-select.active {
    border-color: var(--scenario-active);
    box-shadow: 0 0 0 2px rgba(139,0,0,0.35);
  }
  ```

- [x] **Step 3: Add the `setActiveScenario` function**

  Immediately before `function triggerShock(type) {`, add:

  ```js
  function setActiveScenario(type) {
    const dropdown = document.getElementById('scenario-select');
    document.querySelectorAll('#control-drawer [data-shock]').forEach(function(b) {
      b.classList.toggle('active', type !== null && b.getAttribute('data-shock') === type);
    });
    dropdown.classList.toggle('active', type !== null && dropdown.value === type);
  }
  ```

- [x] **Step 4: Wire the 3 call sites**

  In `triggerShock(type)`, add the call as the first line of the function body:

  ```js
  function triggerShock(type) {
    setActiveScenario(type);
    state = buildBaseState(); state.shock = type;
    const ex = document.getElementById('scenario-explain');
    // ...rest of function unchanged
  ```

  In `resetState()`, add the call as the first line of the function body:

  ```js
  function resetState() {
    setActiveScenario(null);
    state = buildBaseState(); nodeMultipliers = {};
    // ...rest of function unchanged
  ```

  In `runManual()`, add the call immediately after the early-return guard line (so it
  only runs on the "dirty" path):

  ```js
  function runManual() {
    if (!manualIsDirty()) { resetState(); syncManualUI(); return; }
    setActiveScenario(null);
    state = buildBaseState();
    // ...rest of function unchanged
  ```

- [x] **Step 5: Verify via a real browser tab**

  Start a local server if one isn't already running on the port you pick:

  ```bash
  cd bullion-live-map && lsof -i :8791 || python3 -m http.server 8791 > /tmp/bullion-http-server.log 2>&1 &
  ```

  Using the claude-in-chrome tools, navigate to
  `http://localhost:8791/bullion_mk18.html`, then via the JavaScript tool run:

  ```js
  document.querySelector('[data-shock="rate_hike"]').click();
  [...document.querySelectorAll('#control-drawer [data-shock]')].map(b => [b.getAttribute('data-shock'), b.classList.contains('active')])
  ```

  Expected: exactly the `rate_hike` button reports `true`, the other 4 report `false`.

  Then run:

  ```js
  document.getElementById('scenario-select').value = 'rate_hike';
  document.getElementById('scenario-select').dispatchEvent(new Event('change'));
  document.getElementById('scenario-select').classList.contains('active')
  ```

  Expected: `true`.

  Then run `document.getElementById('reset-shock-btn').click()` and confirm all 6
  controls (5 buttons + dropdown) report `classList.contains('active') === false`.

  Then move a manual-driver slider (any `#manual-box input[type=range]`) enough to make
  `manualIsDirty()` true, click the manual Run button, and confirm all 6 controls again
  report `active === false`.

- [x] **Step 6: Commit**

  ```bash
  git add bullion-live-map/bullion_mk18.html
  git commit -m "$(cat <<'EOF'
  Highlight the active scenario in bullion_mk18.html

  Neither the preset buttons nor the dropdown previously showed which
  scenario was currently selected. setActiveScenario() now toggles an
  active class from triggerShock/resetState/runManual; the dropdown uses
  a new --scenario-active red distinct from the existing negative-shock
  red so the two aren't visually confused.

  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  EOF
  )"
  ```

---

### Task 2: Mirror the same change to `bullion_mkultra.html`

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html`
  - CSS: `:root` block (currently lines 24-38 equivalent — confirm exact lines with
    `grep -n ":root" bullion-live-map/bullion_mkultra.html` before editing, since this
    file's line numbers differ from `mk18.html`)
  - CSS: near `select.scenario-select` rules (currently lines 355-361)
  - JS: new function, placed immediately before `function triggerShock(type)`
    (currently line 4147)
  - JS: inside `triggerShock(type)` (currently lines 4147-4162)
  - JS: inside `resetState()` (currently lines 4163-4168ish — confirm with
    `sed -n '4163,4172p' bullion-live-map/bullion_mkultra.html`)
  - JS: inside `runManual()` (currently starts line 4674), in the dirty branch (after
    the early-return guard on line 4675)

**Interfaces:**
- Produces: its own independent `function setActiveScenario(type)`, identical in body to
  Task 1's — this file does not import or share code with `mk18.html`.
- Consumes: nothing from Task 1 (fully independent duplicate).

- [x] **Step 1: Confirm current line numbers**

  ```bash
  cd bullion-live-map
  grep -n "^  :root\|--warn:\|select.scenario-select option\|function triggerShock\|function resetState\|function runManual" bullion_mkultra.html
  ```

  Use these to locate the exact insertion points — do not assume Task 1's `mk18.html`
  line numbers apply here.

- [x] **Step 2: Add the `--scenario-active` CSS custom property**

  Same CSS line as Task 1 Step 1, added to `bullion_mkultra.html`'s `:root` block.

- [x] **Step 3: Add the dropdown's active-state CSS rule**

  Same CSS rule as Task 1 Step 2, added immediately after
  `bullion_mkultra.html`'s `select.scenario-select option { ... }` rule.

- [x] **Step 4: Add the `setActiveScenario` function**

  Same function body as Task 1 Step 3, placed immediately before this file's
  `function triggerShock(type) {`.

- [x] **Step 5: Wire the 3 call sites**

  Same 3 edits as Task 1 Step 4 (`triggerShock`, `resetState`, `runManual`'s dirty
  branch), applied to this file's copies of those functions.

- [x] **Step 6: Verify via a real browser tab**

  Same verification script as Task 1 Step 5, navigated instead to
  `http://localhost:8791/bullion_mkultra.html`.

  Additional note for this file specifically: if any click target sits near the 3D
  WebGL globe, pixel-coordinate clicks are unreliable there (OrbitControls can hook
  global mouse listeners and deselect a panel). If a coordinate click doesn't land, do
  one real coordinate click anywhere safe first to establish user-activation, then use
  `document.querySelector(...).click()` via the JavaScript tool for the actual target.

- [x] **Step 7: Commit**

  ```bash
  git add bullion-live-map/bullion_mkultra.html
  git commit -m "$(cat <<'EOF'
  Highlight the active scenario in bullion_mkultra.html

  Mirrors the mk18.html scenario-highlighting fix in this file's
  independent copy of the same UI.

  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  EOF
  )"
  ```

---

### Task 3: Regression checks + freeze-check

**Files:** none modified — verification only.

**Interfaces:**
- Consumes: the finished state of Task 1 and Task 2.

- [x] **Step 1: Freeze-check mk11–mk17 are untouched**

  ```bash
  cd bullion-live-map
  shasum -a 256 bullion_mk{11,12,13,14,15,16,17}.html
  ```

  Compare each hash against `git show HEAD~2:bullion-live-map/bullion_mk<N>.html |
  shasum -a 256` (adjust `HEAD~2` to whatever commit predates Task 1 if other commits
  landed in between) — all 7 must be identical. If any differ, stop and investigate
  before proceeding; this plan should not have touched them.

- [x] **Step 2: Run the Python suite**

  ```bash
  cd bullion-live-map && python3 -m unittest discover -s tests && python3 -m unittest test_calibrate
  ```

  Expected: same pass count as before this effort started (41/41 + 33/33 as of the
  handoff this plan originated from) — this effort doesn't touch Python code, so any
  change in pass count means something else broke.

- [x] **Step 3: Ask the user to confirm the manual-box toggle fix**

  This isn't new code from this plan — commit `d225580` (already shipped, prior
  session) added the missing `#manual-box.hidden { display: none }` rule. Ask the user
  directly: "Can you reload the live page and confirm the 'Set your own numbers' toggle
  now shows/hides the sliders correctly?" Record their answer; no code change is
  expected regardless of the answer (if it's still broken, that's a new bug report, not
  a regression in this plan).

- [x] **Step 4: Push**

  ```bash
  GIT_TERMINAL_PROMPT=0 git push origin main
  ```

  Confirm with `git rev-list --left-right --count origin/main...main` reads `0 0`
  afterward.
