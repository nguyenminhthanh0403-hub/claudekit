# Mk Ultra — Classification-in-node + 2D "Overview" board — Design

**Date:** 2026-07-25
**File touched:** `bullion-live-map/bullion_mkultra.html` (only; `bullion_mk15.html` stays byte-identical)
**Status:** Approved design, ready for implementation plan.

## Problem

The 3D constellation floats seven classification-stage labels (`GLOBAL SHOCKS`,
`DATA & INPUTS`, `POLICY & FISCAL`, `OVERSIGHT`, `PLUMBING`, `MARKETS`,
`SECTORS & FX`) directly on the sphere. Because they project onto a rotating
globe, they drift over the orbs and read as clutter. Separately, a 3D orbital
sphere is a hard first read for a beginner who just wants to see "what's in this
system and how it's grouped."

## Goals

1. Take the classification stage **off** the 3D map and put it **into each
   node's description** so the information survives without cluttering the globe.
2. Add a **calm 2D "Overview" tab** — a plain-English, at-a-glance board of the
   whole system — as an easier on-ramp than the 3D view.

Non-goals (v1, YAGNI): the board does not live-recolor on scenario runs, does
not animate, and introduces no new libraries.

## Data already available (no new data needed)

- `COLUMN_OF[id] → 0..6`, indexing `COLUMN_TITLES` (the 7 classification stages,
  causal order). Node objects already carry `col`.
- `LAYER_LABELS[group]` — the layer group (color legend), e.g. "Central Bank".
- `GROUP_COLOR[group]` — the group's color.
- `HUB_IDS` — which nodes are hubs.
- `NODES` / `nodesData` — the 39 nodes.

## Part 1 — Classification in the node description

- **Remove the floating stage labels from the 3D map.** Delete/disable
  `buildStageLabels()` + `updateStageLabels()` and their per-frame call from
  `updateLabels()`, and drop `stageLabelEls`. Node labels and the projection
  logic for them are untouched.
- **Detail panel header gains the stage.** `#detail-layer` currently renders
  `LAYER_LABELS[d.group]`. It becomes a two-part line:

  > `LAYER_LABELS[d.group]` · `COLUMN_TITLES[d.col]`

  rendered as e.g. **"Central Bank · Policy & Fiscal"**. The stage half is
  visually distinct (its own class) so it reads as a second facet, not a
  duplicate. `d.col` is guaranteed present — `buildGraph()` sets it for every
  node, defaulting to `5` (Markets) when `COLUMN_OF` has no entry — so the same
  `col` drives both this line and which board column the node lands in (they can
  never disagree).
- Both the 3D map and the 2D board open this same `openDetail(d)`, so the
  classification appears wherever a node is described.

## Part 2 — 2D "Overview" board tab

### View switching

- Two tab buttons in `#header` (left of / near the existing controls):
  **`◎ 3D Map`** and **`▦ Overview`**. 3D is the default.
- The stage hosts two sibling containers: the existing `#stage` WebGL/SVG mount
  and a new `#board-view`. Switching tabs toggles which is visible
  (`display`/class), sets `aria-selected` on the tabs, and pauses nothing else —
  the detail panel, `#legend-box`, and Tools drawer are shared and keep working.
- The 3D render loop keeps running while hidden is acceptable (cheap, avoids
  teardown/rebuild churn); alternatively gate `renderLoop` when the board is
  active. Implementation plan picks one — default: keep it running for
  simplicity, revisit only if it costs measurably.

### Board structure

- `#board-view` is a horizontal flex row of **7 columns**, one per
  `COLUMN_TITLES` entry, in index order 0→6 (causal left→right).
- Each column: a **gold pill header** (reuse the stage-label pill styling from
  the fix that landed in `d34eb27`) + a vertical stack of node cards.
- **Node card:** the node's `label`, with a left color-bar / dot in
  `GROUP_COLOR[group]`. Hubs render **first within their column and bolder**
  (mirrors the 3D "hubs are the anchors" intent). Non-hubs follow.
- Card ordering within a column: hubs first, then the rest in `NODES` order
  (stable, no surprise reshuffles).
- **Click a card → `openDetail(node)`** — the same panel the 3D map uses.
  Cards are real `<button>`s (keyboard-focusable, `aria-label` = node label) so
  the board is accessible without the off-screen a11y list.

### Responsive

- Desktop: 7 columns side by side, the board scrolls vertically inside
  `#board-view` if a column is tall.
- Narrow/phone: columns keep their min-width and the row scrolls **horizontally**
  (`overflow-x:auto`) rather than crushing to unreadable widths.

## Files / functions touched (all in `bullion_mkultra.html`)

- **Remove:** `buildStageLabels`, `updateStageLabels`, `stageLabelEls`, and the
  `updateStageLabels(...)` call inside `updateLabels()`; the `buildStageLabels()`
  call in `build()`.
- **Edit:** `openDetail()` — compose the two-part `#detail-layer` line.
- **Add (HTML):** two tab buttons in `#header`; a `#board-view` container.
- **Add (CSS):** `.board-col`, `.board-card`, tab-button states — reusing the
  existing pill + `.btn` styling vocabulary.
- **Add (JS):** `buildBoard()` (build columns + cards from `nodesData` once
  after `buildGraph()`), `showView('3d' | 'board')` toggler wired to the tabs.
- Card click reuses existing `openDetail`; no new detail logic.

## Verification

- Serve `http://localhost:8755/bullion_mkultra.html`, cache-bust.
- 3D map: no floating stage pills anymore; node labels still show; 0 console
  errors; the four prior fixes (highlight, translucency, redirect) still work.
- Detail header shows "GROUP · STAGE" for several nodes across different columns.
- Overview tab: 7 columns in causal order, every one of the 39 nodes appears in
  exactly one column, hubs first/bold, color bars match the legend.
- Clicking any board card opens the correct detail panel; related-node clicks in
  the panel still work.
- Tab switching works both ways; narrow viewport scrolls horizontally, no
  body-level horizontal scroll.
- Regression: `shasum -a 256 bullion_mk15.html` == `ebfaaaf6…`;
  `index.html`/`release.sh`/`data.json` unchanged.

## Deferred (not v1)

- Scenario recolor sync (board tiles tint green/red when a shock runs).
- Board animations / reveal transitions.
- Making the Overview the shared/index link (index.html stays on mk15).
