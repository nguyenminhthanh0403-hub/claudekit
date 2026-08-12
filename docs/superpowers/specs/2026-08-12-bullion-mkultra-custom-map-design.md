# Mk Ultra — User-Customizable Map (Shareable Node Selection) — Design

**Written:** 2026-08-12 · **Status:** approved by user, ready for `superpowers:writing-plans`

## Background

`bullion_mkultra.html` already has a per-session layer filter: the legend (`buildLegend()` /
`applyLayerFilter()`, around line 3230) lets a viewer tap any of the 12 domain layers
(Regulators, Sovereign/Fiscal, Central Bank, Commercial Banking, Shadow/Non-bank, Capital
Markets, Equity Sectors, Economic Data, Sentiment/Vol, FX/Currency, Commodities, Geopolitics —
39 nodes total, verified via `grep -c "^  { id:'"`) on or off. It's in-memory only (`activeLayers`, a `Set`) — it resets on reload,
can't be bookmarked, and can't be handed to someone else.

The user wants to go further: build their own version of the map — e.g. "I don't want the
economy" — down to individual nodes, not just whole layers, and be able to keep/share that
specific version rather than re-toggling it every visit.

**Finding surfaced during brainstorming, load-bearing for scope below:** the composite health
score (`computeCompositeScore`, line 3987) only reads 7 fields (`hy_oas`, `ig_oas`, `vix`, `spx`,
`fed_bs`, `rrp`, derived `curve_slope`), which trace back to exactly 6 nodes (`credit`, `vix`,
`equit`, `fed`, `repo`, `yield`, via `NODE_LIVE_FIELD`, line 4609 — verified by resolving each
field through that map). Hiding the `indicator` layer
(the user's own "economy" example — CPI, NFP) or any of `geo`/`commodity`/`sectors` has **no
effect on the score today**, regardless of what this feature does — that's a pre-existing scope
limit, not something to fix here.

**Also surfaced:** the graph has real hub nodes — `equit` (14 links), `ffr` (12), `credit` (11),
`banks` (10), `yield` (9), `oil` (8), `tsy` (7) — measured by merging `PLUMBING_LINKS` into
`LINKS` via the same supersede-or-append rule the app itself runs at load time (a naive count of
`LINKS` alone undercounts and gives the wrong degree for several nodes — see
[[bullion-two-link-arrays]]), then computing degree over the merged 93-edge graph. Naive "reconnect
everything around a hidden node" logic would explode into a two-digit number of synthetic links for
a hub removal — addressed in the design below. Separately, 16 of the 39 nodes have degree ≤3 and
are the actual candidates for indirect-link synthesis (`cftc`, `nfp`, `etf` at degree 1 — these
produce zero synthetic pairs since a single edge has no pair to connect; `gse`, `fdic`, `sec`,
`tech`, `defn`, `dxy_fx`, `options`, `energy` at degree 2 — one synthetic pair each; `fins`, `hf`,
`russia`, `tbills`, `house` at degree 3 — up to three synthetic pairs each).

## Goal

Let a viewer hide any combination of individual nodes (not just whole layers) and get a URL that
reproduces exactly that view — so "my custom map without the economy layer" (or any other
combination) is a link they can bookmark or send, not a state they have to re-create by hand
every visit.

## Non-goals

- Does not change what `data.json` contains or how it's fetched — `fetch_bullion_data.py` and the
  GitHub Actions cron are untouched. This is a client-side render/score-input filter only.
- Does not fix the composite score's limited field coverage (6 of 39 nodes) — recorded as a known
  pre-existing limit, not in scope to expand.
- Does not support multi-hop indirect-link synthesis (chains through two or more hidden nodes) —
  one hop only, see below.
- Does not add curated/preset views (considered and rejected — see Alternatives).
- No change to `bullion_mk11.html` through `bullion_mk18.html` (frozen files) or to
  `financial-map.html` (the separate, non-live 108-node map) — scoped to `bullion_mkultra.html`
  only.

## Design

### State model & URL encoding

- **Single source of truth:** `excludedNodes`, a `Set<string>` of node ids, replacing the current
  `activeLayers` group-level set as the primitive everything else derives from.
- **Layer legend (existing UI, repurposed):** clicking a layer bulk-adds/removes every node id in
  that group to/from `excludedNodes`. A layer shows "off" when all its nodes are excluded, and a
  new partial/dimmed state when only some are.
- **New per-node picker:** a new drawer, matching this project's existing drawer pattern ("Set your
  own numbers", "Trends overview", "Acronym glossary" — each a labeled expandable section), listing
  every layer with its nodes as checkboxes underneath. Not crammed into the existing legend box,
  which is already dense with the causal-effect/evidence key.
- **URL sync:** every change serializes `excludedNodes` to `?hide=id1,id2,...` via
  `history.replaceState` (no reload, no new history entries). A "Copy link" button copies
  `window.location.href`; falls back to a pre-filled selectable text field if the Clipboard API is
  unavailable.
- **Load-time parsing:** read `?hide=` on boot, silently drop any id not present in the current
  `NODES` array (so a link shared before a future node rename/removal doesn't break — it just shows
  slightly more than intended, never fails), seed `excludedNodes` before the first render.

### Node/link visibility & indirect-link synthesis

- **Node visibility:** a node renders iff `!excludedNodes.has(id)` — replaces
  `layerVis[id] = activeLayersSet.has(d.group)` (line 2695) with a direct id check.
- **Direct link visibility:** a `LINKS`/`PLUMBING_LINKS` edge renders iff both endpoints are
  visible — same shape as today's `linkLayerVis`, keyed off node id instead of group.
- **Indirect (pass-through) synthesis:** when hidden node `h` has **≤3 kept neighbors**, synthesize
  a dashed connector between each pair of them (≤3 synthetic links per hidden node, never more).
  Label `"Indirect — via <label(h)>"`, no numeric weight/sign, always dashed, styled at the
  existing "unverified" opacity tier. Skip synthesizing a pair that already has a real direct link.
  When `h` has **>3 kept neighbors** (the hub case), its links simply drop — no synthesis, no
  partial/truncated set, so the rule stays predictable.
- **One hop only:** if two adjacent nodes are both hidden, the pair loses their connection — no
  chained synthesis through multiple hidden nodes. Keeps this a local computation instead of a
  general graph-reachability problem.

### Composite score & narrative

- Build a reverse map from `NODE_LIVE_FIELD` at load time (`field → node id`) covering the 7 fields
  `computeCompositeScore` uses.
- `computeCompositeScore(live, excludedNodes)` gains one parameter. For each of the 7 fields, if
  its backing node is in `excludedNodes`, route it into the existing `fieldsMissing` path — same
  `tier`/`leadingCategory` logic as a real data outage, no new branches.
- Narrative text already handles partial `fieldsMissing`; no changes needed there.
- As noted above, hiding any node outside that set of 6 has no effect on the score — expected, not
  a bug.

### Error handling & edge cases

- Unknown/stale ids in `?hide=`: dropped silently at parse time, never throws.
- Hiding every node: render an empty graph with an inline "Nothing to show — try clearing some
  hidden layers" message instead of a blank canvas.
- Clipboard API unavailable: fall back to a selectable pre-filled text field.
- No interaction with the live-data fetch/cron pipeline at all.

## Components / files touched

- **`bullion-live-map/bullion_mkultra.html`** only:
  - Replace `activeLayers` with `excludedNodes` as the filter primitive; update `buildLegend()`,
    `applyLayerFilter()` → node-aware equivalent, and the `Renderer.setLayerFilter` consumer
    (line ~2691) to filter by node id.
  - New per-node picker UI as a new drawer.
  - New URL read/write logic (`history.replaceState`, `?hide=` parse on boot).
  - New "Copy link" control with clipboard-unavailable fallback.
  - New indirect-link synthesis pass (≤3-neighbor rule) feeding the renderer.
  - `computeCompositeScore` gains the `excludedNodes` parameter and the field→node reverse map.
- No Python files, no workflow files, no `data.json` schema changes.

## Testing

- No Python test suite impact (`bullion-live-map/tests/`, currently 85 green, untouched).
- Browser verification via the `headless-chrome-verification` skill, headless Chrome over
  `http://localhost` (not `file://`, since the page fetches `data.json`):
  1. Toggling a layer bulk-hides its nodes and updates the URL.
  2. Toggling one node inside an otherwise-visible layer produces the partial/dimmed layer state.
  3. Hiding a ≤3-neighbor node produces the expected dashed indirect connectors with correct
     labels, skipping any pair that already has a real link.
  4. Hiding a hub node (`equit`) drops its links with no synthesis.
  5. A `?hide=` link with one stale id and one valid id loads correctly, dropping only the stale
     one.
  6. Hiding `credit` changes the composite score's `fieldsMissing`/tier; hiding `geo` does not
     change the score at all.
  7. "Copy link" round-trips: copy it, open in a fresh tab, confirm identical visible state.
  8. Hiding all nodes shows the empty-state message, not a blank canvas.
- `sha256sum` check confirming `bullion_mk11.html` through `bullion_mk18.html` stay byte-unchanged.

## Alternatives considered

1. **Curated presets only** (`?preset=id` selecting a handful of hand-built combos, e.g. "Macro &
   Rates", "No geopolitics"). Much less UI to build and easier to keep visually coherent, but
   doesn't give free-form per-node control — doesn't fulfill the user's stated want (picking
   specific things to drop, like "the economy," ad hoc). Not chosen, though it's a smaller-scoped
   fallback if the full picker proves too complex during implementation.
2. **localStorage-only persistence** (remembered per-device, no link). Simpler — no URL
   serialization, no stale-id handling. Rejected because the user specifically wants a shareable
   link, not just a remembered default.
3. **Two separate state sets** (keep `activeLayers` as-is, add a second `hiddenNodes` override set
   on top). Closer to a minimal diff on existing code, but creates two sources of truth with real
   edge cases (re-showing one node inside an "off" layer; toggling a layer off after individually
   hiding one of its nodes). Rejected in favor of the single unified `excludedNodes` set, which the
   layer legend becomes sugar over rather than a parallel mechanism.
