# Bullion Mk Ultra — Chain-Reaction Hypothesis — Design

## Problem

The causal graph in `bullion_mkultra.html` (`LINKS` merged with `PLUMBING_LINKS` at load
time — 93 live edges across 39 nodes) only shows *direct* relationships. A user asking "what
if mortgage rate affects the repo market?" gets no answer today, even when the graph already
encodes a real, verified indirect connection — e.g. `mortgage ↔ yield ↔ dealers ↔ repo` is a
genuine 3-hop path through already-cited mechanisms, but nothing surfaces it.

**Status: design only.** The user explicitly asked for this to be planned thoroughly before
any implementation — this spec is the planning artifact; no code changes are in scope yet.

## Decision: surface existing paths only, never invent new ones

A field note or a `stat` figure can be added because someone did the verification work. A
hypothesized new causal mechanism between two nodes with no real path would have none of that
— it would be the kind of unverified claim this project has spent real effort this week
removing (the whole audit-followup pass). So this feature does pure graph traversal over
already-verified edges. If two nodes aren't connected within the hop cap, the honest answer is
"not meaningfully connected in this model" — not a fabricated story.

## Traversal semantics

- **Graph:** the live, already-merged `LINKS` array, read *after* the existing
  `PLUMBING_LINKS.forEach(...)` supersede-or-append block runs (`bullion_mkultra.html:~1522-1532`).
  No separate merge logic needed — by the time any UI code runs, `LINKS` already reflects the
  "PLUMBING_LINKS supersedes same-(s,t)-pair LINKS entries, appends the rest" rule.
- **Direction:** search is undirected (an edge is traversable either way), but each hop records
  its *actual* stored direction so the UI can label it "forward" (following the arrow) or
  "backward" (against it) — never presented as a clean one-way causal flow unless every hop in
  a given path happens to be forward.
- **Net sign:** computed (by multiplying hop signs) for paths where every hop is *consistently*
  forward or *consistently* backward — an all-backward path is a legitimate chain, just read
  end-to-start, and is labeled "(reverse)" wherever it renders so it's never mistaken for the
  forward-direction answer. Mixed-direction paths (some hops forward, some backward) still get
  no net-sign badge — there's no honest single number to show. (Amended post-launch, 2026-08-09,
  after a QC review found the original all-forward-only rule discarded 11.3% of paths — 686 of
  6,076 across all node pairs — that had an equally honest reversed-direction answer.)
- **Hop cap:** 3 hops maximum. Beyond that, real path counts explode (confirmed empirically:
  mortgage→repo has 7 simple paths ≤3 hops, 46 at ≤4, 191 at ≤5) and a longer chain reads as a
  stretch, not a story.
- **Path selection:** show *all* simple paths within the 3-hop cap, not just the shortest — at
  this cap, counts stay small enough (single digits to low tens) to show in full without a
  ranking heuristic.

## UI

A new, dedicated section — not nested inside existing per-node detail panels. Confirmed: no
node-search/autocomplete pattern exists anywhere else on the page to reuse, so v1 uses two plain
`<select>` dropdowns listing all 39 node labels, plus a "Trace" button. Submitting runs the
traversal and renders results below.

**Out of scope for v1:** highlighting the found path(s) on the D3/3D graph canvas itself. That's
a real, separate piece of work (translating a path into the renderer's existing
focus/dim/highlight machinery) and isn't needed to deliver the core value — a fast-follow if
wanted later, not bundled into this spec.

## Output format

**No path found:** an explicit message — "Not meaningfully connected within 3 hops in this
model" — styled as a real answer, not an error state.

**Path(s) found:** one card per path. Each card shows:
- The hop sequence as node labels joined by `→` (forward hop) or `←` (backward hop) arrows.
- Per hop: the edge's `why` text (mechanism), a compact badge showing `conf` tier
  (directional/measured/unverified) and `sign` (+/−/0), and the full `stat` field (citation-backed
  detail).
- A net-sign badge at the top of the card, shown when every hop in that path is consistently
  forward or consistently backward — labeled "(reverse)" in the backward case.

## Testing (hybrid approach)

No baked/shipped lookup table — the traversal always runs live against the current `LINKS`, so
there's no separate data file that can drift out of sync with edits to the graph (the exact
failure mode this project hit this week with `bullion_mk18.html`'s narration-script copy).

Instead: a new Python test in `bullion-live-map/tests/` that independently re-parses
`LINKS`/`PLUMBING_LINKS` out of `bullion_mkultra.html` via regex (the same technique used ad hoc
in this session to confirm the mortgage→repo example — `re.findall(r"\{s:'(\w+)', t:'(\w+)'", html)`
plus the supersede-or-append rule), reimplements the same bounded BFS in Python, and asserts
against a handful of known pairs (at minimum: `mortgage`→`repo` finds the `yield`/`dealers` path;
some clearly-unconnected pair returns no result within 3 hops). This runs in the existing
`python3 -m unittest discover -s tests` sweep — no new test runner, no new CI wiring — and
catches graph-structure regressions (a link renamed, removed, or resigned) the same way
`test_freshness_parity.py` and `test_generate_narration.py` already catch other classes of
drift in this project.

## Scope boundary

`bullion_mkultra.html` only. Not `bullion_mk18.html`, `mk16`, or `mk17` — consistent with this
week's other mkultra-only feature work (field-note bar, audit-followup fixes). No narration
changes are implied by this feature (nothing here is spoken-word content).

## Out of scope

- Hypothesizing new mechanisms for unconnected pairs (see "Decision" above) — a fundamentally
  different, much riskier feature if ever wanted; would need its own separate brainstorm.
- D3/3D graph canvas highlighting of found paths (see "UI" above) — possible fast-follow, not
  bundled here.
- Any hop cap other than 3, or any path-count ranking/truncation logic — not needed given the
  3-hop cap keeps counts small.
- Directed-only traversal (a "true causal chain" mode) — considered and explicitly rejected in
  favor of undirected-with-per-hop-direction-labels, since a directed-only search returns far
  fewer answers (many real pairs have no directed path at all, or only a long, weak one).
