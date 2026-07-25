# Mk Ultra — Classification-in-node + 2D Overview board — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the 7 classification-stage labels off the 3D globe into each node's detail-panel header, and add a 2D "Overview" kanban tab (7 stage columns of node cards that open the same detail panel).

**Architecture:** Pure HTML/CSS/DOM edits inside the single file `bullion_mkultra.html`. Part 1 deletes the Three.js label-projection code for stage labels and edits `openDetail()`. Part 2 adds two header tabs, a `#board-view` flex container built once from `nodesData`, and a `showView()` toggler. No new libraries; the board reuses the existing detail panel via `openDetail()`.

**Tech Stack:** Vanilla JS, HTML, CSS. Three.js is already loaded for the 3D view but is NOT used by the board. Verification is via a local `http.server` + Chrome MCP (this project has no unit-test framework).

## Global Constraints

- Edit **only** `bullion-live-map/bullion_mkultra.html`. `bullion_mk15.html` must stay byte-identical (`shasum -a 256` == `ebfaaaf60a63d573…`). `index.html`, `release.sh`, `data.json` unchanged.
- **No new external dependencies.** No new CDN/importmap entries.
- `d.col` is guaranteed present on every node (`buildGraph()` sets it, defaulting to `5`/Markets); `COLUMN_TITLES` has exactly 7 entries indexed `0..6`; `LAYER_LABELS[group]` and `GROUP_COLOR[group]` exist for every group.
- Commits go directly to a working state; push only when the user asks. End commit messages with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.
- Serve for verification: `cd bullion-live-map && python3 -m http.server 8755`, open `http://localhost:8755/bullion_mkultra.html?cb=$RANDOM` (http only; `file://` is blocked by the Chrome extension).

---

### Task 1: Classification off the 3D map, into the detail-panel header

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` (CSS `~154`; `openDetail` `~2492`; label code `~1473`, `~1669–1690`, `~1730`, `~1733–~1762`, `~1902`, `~2119`)

**Interfaces:**
- Consumes: `COLUMN_TITLES` (array of 7 strings), `LAYER_LABELS`, node objects `d` with `d.group` and `d.col`.
- Produces: nothing new for later tasks (Task 2 independently calls the existing `openDetail`).

- [ ] **Step 1: Add the stage-facet CSS.** After the `#detail-layer { … }` rule (line ~154), add a rule so the stage half of the header line reads as a distinct facet:

```css
  #detail-layer .detail-stage { color: var(--gold-dim); font-weight: 600; }
```

- [ ] **Step 2: Compose the two-part header line in `openDetail()`.** Replace the single line at ~2495:

```js
  document.getElementById('detail-layer').textContent = LAYER_LABELS[d.group] || '';
```

with:

```js
  // Group = what kind of thing it is; stage = where it sits in the causal flow
  // (the classification that used to float on the 3D globe, now shown here).
  const _group = LAYER_LABELS[d.group] || '';
  const _stage = COLUMN_TITLES[d.col] || '';
  document.getElementById('detail-layer').innerHTML =
    _group + (_stage ? ' <span class="detail-stage">· ' + _stage + '</span>' : '');
```

- [ ] **Step 3: Remove the `buildStageLabels()` call in `build()`.** Delete the line at ~2119:

```js
    buildStageLabels();
```

(Leave the adjacent `buildLabels(nodesArr);` and `buildA11yList(nodesArr);` calls intact.)

- [ ] **Step 4: Remove the `updateStageLabels()` call in `updateLabels()`.** Delete the line at ~1730 (the last line inside `updateLabels`, just before its closing `}`):

```js
    updateStageLabels(w, h);
```

- [ ] **Step 5: Delete the `buildStageLabels()` function** (entire block, ~1669–1690) — from `function buildStageLabels() {` through its closing `}` immediately before the `// Projects a world point…` comment.

- [ ] **Step 6: Delete the `updateStageLabels()` function** (entire block, ~1733 through its closing `}`) — from `function updateStageLabels(w, h) {` through the closing `}` that precedes the `// ── Animation tweens (Phase 6) ──` comment. Remove the whole function body including the `sideOffset` stagger logic.

- [ ] **Step 7: Remove the two remaining `stageLabelEls` references.**
  - In the declaration at ~1473, change:

```js
  let labelContainer = null, labelEls = {}, stageLabelEls = [];
```
    to:
```js
  let labelContainer = null, labelEls = {};
```
  - In `disposeScene()` at ~1902, change:

```js
    labelContainer = null; labelEls = {}; stageLabelEls = [];
```
    to:
```js
    labelContainer = null; labelEls = {};
```

- [ ] **Step 8: Verify no orphan references.** Run:

```bash
grep -n "stageLabelEls\|buildStageLabels\|updateStageLabels" bullion-live-map/bullion_mkultra.html
```
Expected: **no output** (all references removed).

- [ ] **Step 9: Browser verify.** Serve, then load `http://localhost:8755/bullion_mkultra.html?cb=$RANDOM` in Chrome MCP:
  - Screenshot the 3D map: **no floating stage pills** (`GLOBAL SHOCKS`, `PLUMBING`, etc.) anywhere on the globe; node labels (e.g. "Repo Market") still appear.
  - `read_console_messages` with `onlyErrors:true`: **zero errors**.
  - Click a node (or run in the page console: `openDetail(nodesDataIndex['fed'])`), then read the header:

```js
document.getElementById('detail-layer').textContent
```
    Expected: a two-part string like `"Central Bank · Policy & Fiscal"` (group · stage). Check a second node in a different column (e.g. `'repo'` → `… · Plumbing`).
  - Confirm the four prior fixes still work: click a minor node → it highlights; orbs look translucent; click a related row → globe redirects.

- [ ] **Step 10: Commit.**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: move classification stage off globe into detail header

Remove the floating stage-label projection (buildStageLabels/updateStageLabels)
from the 3D view and show the causal stage in the detail-panel header as
'Group · Stage' instead, driven by d.col.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 2D "Overview" board tab

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` (header HTML `~471`; `#app` body `~490`; CSS after `~103`; JS near `openDetail` `~2490` and `buildGraph` tail `~2341`)

**Interfaces:**
- Consumes: `nodesData` (array set in `buildGraph`, each item has `id,label,group,col,isHub`), `COLUMN_TITLES`, `GROUP_COLOR`, `openDetail(node)`.
- Produces: `buildBoard()` (build DOM once), `showView('3d' | 'board')` (toggle visibility + tab state). Both are module-scoped functions; not called by any other task.

- [ ] **Step 1: Add the two tab buttons to the header.** In `#header-controls` (opens at ~471), insert as its **first** children, immediately after `<div id="header-controls">`:

```html
      <div id="view-tabs" role="tablist" aria-label="View">
        <button class="btn tab active" id="tab-3d" role="tab" aria-selected="true">&#9673; 3D Map</button>
        <button class="btn tab" id="tab-board" role="tab" aria-selected="false">&#9638; Overview</button>
      </div>
```

- [ ] **Step 2: Add the board container.** Immediately after the `</div>` that closes `#stage` (line ~490) and **before** the `</div>` that closes `#app` (~491), insert:

```html
  <div id="board-view" role="tabpanel" aria-label="Overview board" hidden></div>
```

- [ ] **Step 3: Add the board + tab CSS.** After the `#network-svg:active { … }` rule (~103), add:

```css
  /* View tabs: a small segmented control in the header */
  #view-tabs { display: flex; margin-right: 4px; }
  #view-tabs .tab { border-radius: 0; }
  #view-tabs .tab:first-child { border-radius: 6px 0 0 6px; }
  #view-tabs .tab:last-child { border-radius: 0 6px 6px 0; border-left: none; }

  /* 2D Overview board: 7 stage columns of node cards */
  #board-view {
    flex: 1 1 auto; overflow: auto; padding: 16px;
    display: flex; gap: 12px; align-items: flex-start;
  }
  .board-col { flex: 1 0 150px; min-width: 150px; max-width: 240px; display: flex; flex-direction: column; gap: 8px; }
  .board-col-head {
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: var(--gold);
    text-align: center; padding: 5px 8px; border-radius: 999px; text-transform: uppercase;
    background: rgba(8,10,18,0.82); border: 1px solid rgba(212,184,105,0.35);
    position: sticky; top: 0; z-index: 1;
  }
  .board-card {
    display: block; width: 100%; text-align: left;
    background: var(--bg-panel2); color: var(--text);
    border: 1px solid var(--border); border-left-width: 4px;
    border-radius: 6px; padding: 7px 9px; font-size: 12px; cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }
  .board-card:hover { background: #182034; border-color: #2a3352; }
  .board-card.hub { font-weight: 700; }
```

- [ ] **Step 4: Add `buildBoard()` and `showView()` plus tab wiring.** Immediately after the `closeDetail` / `detail-close` block (after the `document.getElementById('detail-close').addEventListener('click', closeDetail);` line, ~2504), add:

```js
// ── 2D Overview board ─────────────────────────────────────────────────────
// A calm, plain-English kanban of the whole system: one column per causal
// stage (COLUMN_TITLES, left→right), node cards tinted by their layer-group
// colour, hubs first + bold. Clicking a card opens the SAME detail panel the
// 3D map uses, so the board is just a second way to browse the same content.
function buildBoard() {
  const view = document.getElementById('board-view');
  view.innerHTML = '';
  COLUMN_TITLES.forEach((title, ci) => {
    const col = document.createElement('div');
    col.className = 'board-col';
    const head = document.createElement('div');
    head.className = 'board-col-head';
    head.textContent = title;
    col.appendChild(head);
    // Hubs first (isHub true→1), then the rest in NODES order. Array.sort is
    // stable in modern engines, so equal-isHub cards keep their source order.
    const inCol = nodesData.filter(n => n.col === ci).sort((a, b) => (b.isHub === true) - (a.isHub === true));
    inCol.forEach(n => {
      const card = document.createElement('button');
      card.className = 'board-card' + (n.isHub ? ' hub' : '');
      card.style.borderLeftColor = GROUP_COLOR[n.group] || '#8891a6';
      card.textContent = n.label;
      card.setAttribute('aria-label', n.label);
      card.addEventListener('click', () => openDetail(n));
      col.appendChild(card);
    });
    view.appendChild(col);
  });
}

function showView(which) {
  const is3d = which !== 'board';
  document.getElementById('stage').style.display = is3d ? '' : 'none';
  document.getElementById('board-view').hidden = is3d;
  const t3 = document.getElementById('tab-3d'), tb = document.getElementById('tab-board');
  t3.classList.toggle('active', is3d);  t3.setAttribute('aria-selected', String(is3d));
  tb.classList.toggle('active', !is3d); tb.setAttribute('aria-selected', String(!is3d));
  // The 3D canvas sizes itself from #stage; while hidden it can read 0 width,
  // so re-fit it the moment we come back to the map (redraw() no-ops if the
  // scene isn't ready yet).
  if (is3d) Renderer.redraw();
}
document.getElementById('tab-3d').addEventListener('click', () => showView('3d'));
document.getElementById('tab-board').addEventListener('click', () => showView('board'));
```

- [ ] **Step 5: Build the board once, after the graph data is ready.** In `buildGraph()`, change the tail (~2340–2341):

```js
  applyVisibility();
  applyLayerFilter();
}
```
to:
```js
  applyVisibility();
  applyLayerFilter();
  buildBoard(); // populate the 2D Overview tab from the same nodesData
}
```

- [ ] **Step 6: Browser verify — board content.** Serve + load in Chrome MCP, click the **Overview** tab (or run `showView('board')` in the console), screenshot:
  - **7 columns** with gold pill headers in causal order: Global Shocks, Data & Inputs, Policy & Fiscal, Oversight, Plumbing, Markets, Sectors & FX.
  - Every node appears in exactly one column. Verify count in the console:

```js
[...document.querySelectorAll('.board-card')].length
```
    Expected: **39**.
  - Hubs are bold and appear first in their column; each card has a left colour-bar matching its layer group.

- [ ] **Step 7: Browser verify — interaction + switching.**
  - Click a card (e.g. the "Fed" card): the detail panel opens with the correct title and the `Group · Stage` header from Task 1. Click a related row in the panel → it navigates (existing behavior) and stays usable.
  - Click **3D Map** tab → the globe is visible again and interactive (screenshot; drag/click a node works). Click **Overview** → board again. `aria-selected` flips correctly:

```js
[document.getElementById('tab-3d').getAttribute('aria-selected'), document.getElementById('tab-board').getAttribute('aria-selected')]
```
  - `read_console_messages` `onlyErrors:true` after all of the above: **zero errors**.

- [ ] **Step 8: Browser verify — responsive.** Narrow the viewport (set `#app` width ~390px via console `document.getElementById('app').style.width='390px'; window.dispatchEvent(new Event('resize'))`), switch to Overview, screenshot: columns keep their min-width and the board **scrolls horizontally** (no page-body horizontal scrollbar). Reset width afterward.

- [ ] **Step 9: Regression check.** Run:

```bash
shasum -a 256 bullion-live-map/bullion_mk15.html
git status --short bullion-live-map/
```
Expected: mk15 sha == `ebfaaaf60a63d573…`; only `bullion_mkultra.html` shows as modified.

- [ ] **Step 10: Commit.**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: add 2D Overview board tab

New '▦ Overview' header tab beside the 3D map: a 7-column kanban (one per
causal stage, left→right), node cards tinted by layer colour with hubs first,
each opening the shared detail panel. buildBoard() runs once from nodesData;
showView() toggles the views and re-fits the 3D canvas on return.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Remove floating stage labels from 3D → Task 1 Steps 3–8. ✓
- Classification in detail header as `Group · Stage` → Task 1 Steps 1–2, verified Step 9. ✓
- Two tabs, 3D default → Task 2 Steps 1, 4 (default `hidden`/`active`). ✓
- 7-column board in causal order, cards tinted by group, hubs first/bold → Task 2 Steps 3–4, verified Step 6. ✓
- Card click opens shared detail panel → Task 2 Step 4 (`openDetail(n)`), verified Step 7. ✓
- Shared detail/legend/drawer, responsive horizontal scroll → Task 2 Steps 2–3, verified Step 8. ✓
- No new deps; mk15 byte-identical → Global Constraints + Task 2 Step 9. ✓
- Deferred (scenario recolor, animation, index repoint) → correctly absent from tasks. ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code; verification steps give exact console expressions and expected values.

**Type consistency:** `buildBoard()`/`showView('3d'|'board')` names match between definition (Task 2 Step 4) and call sites (Steps 5, 6, 7). `openDetail(node)`, `Renderer.redraw()`, `nodesData`, `COLUMN_TITLES`, `GROUP_COLOR` all match existing signatures in the file. `d.col` usage matches the guaranteed-present constraint.
