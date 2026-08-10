# Bullion Mk Ultra — Chain-Reaction Hypothesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user pick two nodes in `bullion_mkultra.html`'s causal graph and see every real,
already-verified path ≤3 hops connecting them — e.g. `mortgage ↔ yield ↔ dealers ↔ repo` — with
each hop's mechanism, confidence tier, sign, and citation, and each hop honestly labeled forward
or backward relative to its stored direction.

**Architecture:** Pure client-side JS. A traversal layer (`findChains`) does undirected BFS/DFS
over the page's existing, already-merged `LINKS` array (no new data file, no precomputation) and
reuses the page's existing `neighborsOf` adjacency structure. A render layer turns found paths
into result cards. A small, independent Python test (mirroring this project's existing
`test_freshness_parity.py`/`test_generate_narration.py` drift-detection pattern) re-parses the
same graph data via regex and re-implements the same BFS, asserting known pairs — this is the
project's only automated coverage for the traversal logic, since there's no browser-based JS
test runner in this repo.

**Tech Stack:** Vanilla JS (no new libraries), existing CSS custom-property theme, Python
`unittest` (existing test suite).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-08-bullion-mkultra-chain-reaction-hypothesis-design.md`
  — every task below implements a specific section of that spec; consult it for the "why" behind
  any requirement restated here.
- Scope is `bullion_mkultra.html` only. Do not touch `bullion_mk18.html`, `mk16`, or `mk17`.
- Hop cap is exactly 3. Show all simple paths within that cap, not just the shortest.
- Search is undirected (edges walkable either way), but every hop must record and display its
  actual stored `s`→`t` direction as forward/backward — never imply a one-way causal flow that
  isn't there.
- Net sign is computed and shown only when *every* hop in a path is forward. Mixed-direction
  paths get no net-sign badge.
- No new unverified content anywhere — this feature only surfaces edges that already exist in
  `LINKS`/`PLUMBING_LINKS`. A pair with no path within 3 hops gets an honest "not meaningfully
  connected" message, never an invented mechanism.
- This project's project-wide JS-string convention: avoid literal straight apostrophes inside
  single-quoted JS string literals (they terminate the string) — use `’` or a literal curly
  `’` character instead, matching existing code. This plan's JS snippets below already follow
  that rule; preserve it in any new prose you add.

---

### Task 1: Python graph-traversal test (independent verification)

**Files:**
- Create: `bullion-live-map/tests/test_chain_reaction.py`

**Interfaces:**
- Consumes: nothing from other tasks — this test independently re-parses `bullion_mkultra.html`'s
  `LINKS`/`PLUMBING_LINKS` arrays via regex, exactly as verified during planning (see Step 1).
- Produces: nothing other tasks depend on. This is a standalone regression guard, run via the
  existing `python3 -m unittest discover -s tests` sweep.

This task has no dependency on the JS work in Tasks 2-3, so it can be built and verified first,
against the graph data that already exists in the file today.

- [ ] **Step 1: Write the test file**

```python
"""Independent structural check for the chain-reaction traversal feature.

findChains() (bullion_mkultra.html, JS) does undirected BFS over the merged
LINKS array to find paths <=3 hops between two nodes. There is no browser-based
JS test runner in this repo, so this file re-implements the same algorithm in
Python against the same source data (parsed via regex, not a full JS parser --
only the s/t/w/sign fields are needed for topology, not why/stat/conf) and
asserts it against known pairs. This is the only automated regression guard
for the traversal logic: if a future edit renames, removes, or re-signs a
link such that these known chains break, this test catches it the same way
test_freshness_parity.py catches Python<->JS table drift.

Mirrors the project's existing supersede-or-append merge rule (see
bullion_mkultra.html's "MERGE PLUMBING INTO THE GRAPH" comment block): a
PLUMBING_LINKS entry with the same (s, t) pair as an existing LINKS entry
replaces it; otherwise it's appended.
"""
import os
import re
import unittest

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "bullion_mkultra.html")

_EDGE_RE = re.compile(r"\{s:'(\w+)', t:'(\w+)', w:(\d+), sign:(-?\d+)")


def _extract_block(html, array_name):
    start = html.index("const " + array_name + " = [")
    end = html.index("\n];", start)
    return html[start:end]


def _parse_edges(block):
    return [(s, t, int(w), int(sign)) for s, t, w, sign in _EDGE_RE.findall(block)]


def load_merged_edges():
    with open(MAP_PATH, encoding="utf-8") as f:
        html = f.read()
    links = _parse_edges(_extract_block(html, "LINKS"))
    plumbing = _parse_edges(_extract_block(html, "PLUMBING_LINKS"))
    by_pair = {}
    order = []
    for s, t, w, sign in links:
        by_pair[(s, t)] = (s, t, w, sign)
        order.append((s, t))
    for s, t, w, sign in plumbing:
        if (s, t) not in by_pair:
            order.append((s, t))
        by_pair[(s, t)] = (s, t, w, sign)
    return [by_pair[k] for k in order]


def build_graph(edges):
    from collections import defaultdict
    neighbors = defaultdict(set)
    edge_of = {}
    for s, t, w, sign in edges:
        neighbors[s].add(t)
        neighbors[t].add(s)
        edge_of[(s, t)] = (s, t, w, sign)
    return neighbors, edge_of


def find_link(edge_of, a, b):
    if (a, b) in edge_of:
        e = edge_of[(a, b)]
        return {"sign": e[3], "forward": True}
    if (b, a) in edge_of:
        e = edge_of[(b, a)]
        return {"sign": e[3], "forward": False}
    return None


def find_chains(neighbors, edge_of, start, end, max_hops=3):
    paths = []

    def dfs(current, visited, path):
        if len(path) > max_hops:
            return
        if current == end and path:
            paths.append(list(path))
            return
        for nxt in sorted(neighbors[current]):
            if nxt in visited:
                continue
            hop = find_link(edge_of, current, nxt)
            visited.add(nxt)
            path.append((current, nxt, hop))
            dfs(nxt, visited, path)
            path.pop()
            visited.discard(nxt)

    if start != end:
        dfs(start, {start}, [])
    return paths


def net_sign(path):
    if not path or not all(hop[2]["forward"] for hop in path):
        return None
    net = 1
    for hop in path:
        net *= hop[2]["sign"]
    return net


class TestChainReactionTraversal(unittest.TestCase):
    def setUp(self):
        self.edges = load_merged_edges()
        self.neighbors, self.edge_of = build_graph(self.edges)

    def test_total_live_edge_count(self):
        # Cross-check against the 2026-08-07 link-sourcing audit's own count
        # (93 live edges after the supersede-or-append merge) -- if this
        # drifts, the graph structure changed in a way this test should see.
        self.assertEqual(len(self.edges), 93)

    def test_mortgage_to_repo_finds_seven_paths(self):
        paths = find_chains(self.neighbors, self.edge_of, "mortgage", "repo", 3)
        sequences = {
            tuple([p[0][0]] + [hop[1] for hop in p]) for p in paths
        }
        expected = {
            ("mortgage", "credit", "banks", "repo"),
            ("mortgage", "ffr", "banks", "repo"),
            ("mortgage", "ffr", "mmf", "repo"),
            ("mortgage", "mbs", "banks", "repo"),
            ("mortgage", "mbs", "fed", "repo"),
            ("mortgage", "yield", "dealers", "repo"),
            ("mortgage", "yield", "hf", "repo"),
        }
        self.assertEqual(sequences, expected)
        # None of these 7 real paths happen to be all-forward, so none should
        # report a net sign -- a genuine property of this pair, not a bug.
        self.assertTrue(all(net_sign(p) is None for p in paths))

    def test_unconnected_pair_within_three_hops(self):
        paths = find_chains(self.neighbors, self.edge_of, "banks", "cftc", 3)
        self.assertEqual(paths, [])

    def test_same_node_returns_no_paths(self):
        paths = find_chains(self.neighbors, self.edge_of, "mortgage", "mortgage", 3)
        self.assertEqual(paths, [])

    def test_all_forward_path_computes_net_sign(self):
        paths = find_chains(self.neighbors, self.edge_of, "ffr", "tech", 3)
        direct = next(
            p for p in paths if [p[0][0]] + [hop[1] for hop in p] == ["ffr", "tech"]
        )
        self.assertEqual(net_sign(direct), -1)
        three_hop = next(
            p for p in paths
            if [p[0][0]] + [hop[1] for hop in p] == ["ffr", "credit", "equit", "tech"]
        )
        self.assertEqual(net_sign(three_hop), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it passes against the current graph**

Run: `cd bullion-live-map && python3 -m unittest tests.test_chain_reaction -v`

Expected: all 5 tests PASS. (These assertions were computed and verified against the actual
current file content during planning, not guessed — a failure here means the graph has changed
since this plan was written, not that the test is wrong. If it fails, re-derive the expected
values from the current file before changing the test.)

- [ ] **Step 3: Run the full existing suite to confirm no collateral breakage**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests`

Expected: all tests still PASS (this new file only reads `bullion_mkultra.html`, it doesn't
modify anything yet).

- [ ] **Step 4: Commit**

```bash
git add bullion-live-map/tests/test_chain_reaction.py
git commit -m "Mk Ultra: add independent graph-traversal test for chain-reaction feature"
```

---

### Task 2: JS traversal core (findChains, findLinkBetween, netSignForPath)

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` (insert after the `neighborsOf` population
  block)

**Interfaces:**
- Consumes: the page's existing `LINKS` (merged, live graph — already includes
  `PLUMBING_LINKS`'s supersede-or-append by the time this code runs) and `neighborsOf` (existing
  undirected adjacency-by-id map, already built from the same merged `LINKS`).
- Produces: `findChains(startId, endId, maxHops)` → `Array<Array<{from, to, link, forward}>>`
  (array of paths, each path an array of hop objects); `netSignForPath(path)` → `number | null`.
  Task 3 calls both of these by name.

Locate the anchor: search `bullion_mkultra.html` for this exact existing block (originally at
line ~1626-1627, may have shifted slightly if other work has landed since this plan was written
— search for the text, not the line number):

```js
// Adjacency list for neighbor lookups (hub reveal + detail panel "connected to")
const neighborsOf = {};
NODES.forEach(n => neighborsOf[n.id] = new Set());
LINKS.forEach(l => { neighborsOf[l.s].add(l.t); neighborsOf[l.t].add(l.s); });
```

Insert the new code immediately after that block's closing line, before the next line
(`let expandedHubs = new Set();`).

- [ ] **Step 1: Insert the traversal functions**

```js

// ── Chain-reaction hypothesis: multi-hop connections between two nodes ─────
// Pure traversal over the already-merged LINKS array (PLUMBING_LINKS has
// already superseded/appended into it above this point). Undirected search --
// an edge is walkable either way -- but each hop records the edge's actual
// stored s/t direction so callers can label it forward/backward rather than
// implying a one-way causal flow that isn't there. See
// docs/superpowers/specs/2026-08-08-bullion-mkultra-chain-reaction-hypothesis-design.md.
function findLinkBetween(a, b) {
  const link = LINKS.find(l => (l.s === a && l.t === b) || (l.s === b && l.t === a));
  if (!link) return null;
  return { link, forward: link.s === a };
}

function findChains(startId, endId, maxHops = 3) {
  const paths = [];
  function dfs(current, visited, path) {
    if (path.length > maxHops) return;
    if (current === endId && path.length > 0) {
      paths.push(path.slice());
      return;
    }
    for (const next of neighborsOf[current] || []) {
      if (visited.has(next)) continue;
      const hop = findLinkBetween(current, next);
      if (!hop) continue;
      visited.add(next);
      path.push({ from: current, to: next, link: hop.link, forward: hop.forward });
      dfs(next, visited, path);
      path.pop();
      visited.delete(next);
    }
  }
  if (startId !== endId) dfs(startId, new Set([startId]), []);
  return paths;
}

// Net sign is only meaningful when every hop follows its edge's stored
// direction -- a path with any backward hop has no single honest "effect of
// A on B" to report, so this returns null rather than a fabricated number.
function netSignForPath(path) {
  if (path.length === 0 || !path.every(hop => hop.forward)) return null;
  return path.reduce((acc, hop) => acc * (hop.link.sign || 0), 1);
}
```

- [ ] **Step 2: Verify parity with the Python test via a Node smoke check**

This project has no browser-based JS test runner, so verify correctness the same way prior
sessions verified hand-edited JS in this exact file: extract the relevant script content and
`eval()` it in an isolated Node process (a naive full-file parse false-positives on this file, so
don't attempt that).

Run this from `bullion-live-map/`:

```bash
node -e "
const fs = require('fs');
const html = fs.readFileSync('bullion_mkultra.html', 'utf8');
// Extract everything from 'const NODES = [' (needed because neighborsOf's
// construction references NODES) through just before 'let expandedHubs',
// which covers NODES, PLUMBING_LINKS, LINKS, the merge block, neighborsOf,
// and the three functions this task just added -- then eval it all as ONE
// string so the const/let bindings inside stay visible to the assertions
// appended below (a separate eval() call would NOT see them: direct eval's
// let/const bindings are scoped to that eval call, confirmed while writing
// this plan -- do not split this into multiple eval() calls).
const start = html.indexOf('const NODES = [');
const end = html.indexOf('let expandedHubs = new Set();');
const snippet = html.slice(start, end);
const check = snippet + \`
const mortgageRepo = findChains('mortgage', 'repo', 3);
console.assert(mortgageRepo.length === 7, 'expected 7 mortgage->repo paths, got ' + mortgageRepo.length);
console.assert(mortgageRepo.every(p => netSignForPath(p) === null), 'expected no all-forward mortgage->repo paths');

const bankscftc = findChains('banks', 'cftc', 3);
console.assert(bankscftc.length === 0, 'expected banks<->cftc unconnected within 3 hops');

const ffrTech = findChains('ffr', 'tech', 3);
const direct = ffrTech.find(p => p.length === 1);
console.assert(netSignForPath(direct) === -1, 'expected ffr->tech direct net sign -1, got ' + netSignForPath(direct));
const threeHop = ffrTech.find(p => p.length === 3 && p.map(h=>h.to).join(',') === 'credit,equit,tech');
console.assert(netSignForPath(threeHop) === 1, 'expected ffr->credit->equit->tech net sign 1, got ' + netSignForPath(threeHop));

console.log('All JS/Python parity checks passed.');
\`;
eval(check);
"
```

Expected output: `All JS/Python parity checks passed.` with no assertion failures printed above
it. These are the exact same fixtures Task 1's Python test checks — if both pass, the JS and
Python implementations agree. (This exact extraction approach — slicing `NODES` through
`expandedHubs` and eval'ing as one string — was run and verified working during planning; a
naive attempt with a separate `eval()` per statement will fail with `ReferenceError` since
direct eval's `const`/`let` bindings don't leak to the outer scope.)

- [ ] **Step 3: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: add chain-reaction traversal core (findChains/netSignForPath)"
```

---

### Task 3: UI — node pickers, result cards, CSS, wiring

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` (three separate insertion points: CSS, HTML,
  JS render/wiring)

**Interfaces:**
- Consumes: `findChains(startId, endId, maxHops)` and `netSignForPath(path)` from Task 2; the
  page's existing `NODES` array (`{id, label, ...}`) and `ID_TO_LABEL` map (`{[id]: label}`,
  already built elsewhere in the file).
- Produces: a working UI. No later task depends on this one.

**Part A — CSS.** Locate the anchor (search for this exact existing rule, originally around line
585):

```css
  .glossary-view { padding: 9px 11px; font-size: 11px; color: var(--text-dim); background: var(--bg-deep); overflow-y: auto; touch-action: pan-y; border-radius: 6px; max-height: 240px; border: 1px solid var(--border); }
```

- [ ] **Step 1: Insert new CSS rules immediately after that line**

```css
  .chain-picker-row { display: flex; align-items: center; gap: 8px; }
  .chain-static-arrow { color: var(--text-dim); font-size: 14px; }
  .chain-results { display: flex; flex-direction: column; gap: 8px; }
  .chain-empty { font-size: 12px; color: var(--text-dim); padding: 8px; }
  .chain-card { border: 1px solid var(--border); border-radius: 6px; padding: 9px 11px; background: var(--bg-panel2); }
  .chain-path-header { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 6px; }
  .chain-node { color: var(--gold); }
  .chain-arrow { color: var(--text-dim); }
  .chain-net-badge { margin-left: 6px; font-size: 10px; padding: 1px 6px; border-radius: 10px; font-weight: 700; }
  .chain-net-pos { background: rgba(123,191,142,0.18); color: var(--green); }
  .chain-net-neg { background: rgba(224,101,79,0.18); color: var(--red); }
  .chain-net-zero { background: rgba(136,145,166,0.18); color: var(--text-dim); }
  .chain-hop { padding: 6px 0; border-top: 1px solid var(--border); }
  .chain-hop:first-child { border-top: none; padding-top: 0; }
  .chain-hop-label { font-size: 11px; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .chain-badge { font-size: 9px; padding: 1px 5px; border-radius: 8px; text-transform: uppercase; letter-spacing: 0.03em; }
  .chain-conf-measured { background: rgba(212,184,105,0.18); color: var(--gold); }
  .chain-conf-directional { background: rgba(136,145,166,0.18); color: var(--text-dim); }
  .chain-conf-unverified { background: rgba(224,101,79,0.18); color: var(--red); }
  .chain-sign-pos { background: rgba(123,191,142,0.18); color: var(--green); }
  .chain-sign-neg { background: rgba(224,101,79,0.18); color: var(--red); }
  .chain-sign-zero { background: rgba(136,145,166,0.18); color: var(--text-dim); }
  .chain-hop-why { font-size: 11px; color: var(--text-dim); margin-top: 3px; line-height: 1.5; }
  .chain-hop-stat { font-size: 10px; color: var(--text-dim); margin-top: 3px; line-height: 1.5; opacity: 0.85; }
```

**Part B — HTML.** Locate the anchor (search for this exact existing block, originally around
line 884-887, the glossary section — the last section in the sidebar drawer):

```html
    <div>
      <div class="drawer-label">Acronym glossary <span class="drawer-tag" id="glossary-toggle">show</span></div>
      <div class="glossary-view hidden" id="glossary-box"></div>
    </div>
```

- [ ] **Step 2: Insert the new section immediately after that block (still before the sidebar's
  closing `</div></div>`)**

```html

    <div>
      <div class="drawer-label">Chain reaction</div>
      <div class="chain-picker-row">
        <select class="scenario-select" id="chain-start"></select>
        <span class="chain-static-arrow">&#8596;</span>
        <select class="scenario-select" id="chain-end"></select>
      </div>
      <button class="run-btn" id="chain-trace-btn" style="margin-top:8px">Trace connection</button>
      <div id="chain-results" class="chain-results" style="margin-top:8px"></div>
    </div>
```

**Part C — JS render + wiring.** Locate the anchor (search for this exact existing line, near
the bottom of the script where other buttons get wired):

```js
document.getElementById('run-ai-btn').addEventListener('click', runAIAnalysis);
```

- [ ] **Step 3: Insert the render functions and wiring immediately after that line**

```js

// ── Chain-reaction hypothesis: UI ───────────────────────────────────────────
function signBadgeClass(sign) {
  return sign > 0 ? 'chain-sign-pos' : sign < 0 ? 'chain-sign-neg' : 'chain-sign-zero';
}
function signSymbol(sign) {
  return sign > 0 ? '+' : sign < 0 ? '−' : '0';
}

function renderChainCard(path) {
  const netSign = netSignForPath(path);
  const seqIds = [path[0].from, ...path.map(h => h.to)];
  const headerParts = seqIds.map((id, i) => {
    const label = '<span class="chain-node">' + (ID_TO_LABEL[id] || id) + '</span>';
    if (i === seqIds.length - 1) return label;
    const arrow = path[i].forward ? '→' : '←';
    return label + ' <span class="chain-arrow">' + arrow + '</span> ';
  }).join('');
  const netBadge = netSign === null ? '' :
    '<span class="chain-net-badge ' + signBadgeClass(netSign) + '">net ' + signSymbol(netSign) + '</span>';
  const hopsHtml = path.map(hop => {
    const l = hop.link;
    const dirLabel = (ID_TO_LABEL[hop.from] || hop.from) + (hop.forward ? ' → ' : ' ← ') + (ID_TO_LABEL[hop.to] || hop.to);
    return '<div class="chain-hop">' +
      '<div class="chain-hop-label">' + dirLabel +
        '<span class="chain-badge chain-conf-' + l.conf + '">' + l.conf + '</span>' +
        '<span class="chain-badge ' + signBadgeClass(l.sign) + '">' + signSymbol(l.sign) + '</span>' +
      '</div>' +
      '<div class="chain-hop-why">' + l.why + '</div>' +
      (l.stat ? '<div class="chain-hop-stat">' + l.stat + '</div>' : '') +
    '</div>';
  }).join('');
  return '<div class="chain-card"><div class="chain-path-header">' + headerParts + netBadge + '</div>' + hopsHtml + '</div>';
}

function renderChainResults(startId, endId) {
  const container = document.getElementById('chain-results');
  if (!startId || !endId || startId === endId) {
    container.innerHTML = '<div class="chain-empty">Pick two different nodes.</div>';
    return;
  }
  const paths = findChains(startId, endId, 3);
  if (paths.length === 0) {
    container.innerHTML = '<div class="chain-empty">Not meaningfully connected within 3 hops in this model.</div>';
    return;
  }
  container.innerHTML = paths.map(renderChainCard).join('');
}

function populateChainSelects() {
  const opts = NODES.slice().sort((a, b) => a.label.localeCompare(b.label))
    .map(n => '<option value="' + n.id + '">' + n.label + '</option>').join('');
  document.getElementById('chain-start').innerHTML = opts;
  document.getElementById('chain-end').innerHTML = opts;
  document.getElementById('chain-end').selectedIndex = 1;
}
populateChainSelects();
document.getElementById('chain-trace-btn').addEventListener('click', () => {
  renderChainResults(document.getElementById('chain-start').value, document.getElementById('chain-end').value);
});
```

- [ ] **Step 4: Verify via headless Chrome (this project's standing UI-verification method)**

Use the `headless-chrome-verification` skill. Load `bullion_mkultra.html`, then drive it via the
DevTools Protocol (isolated `--user-data-dir`, per this project's standing rule) to:

1. Confirm `#chain-start` and `#chain-end` are populated with 39 `<option>` elements each.
2. Set `#chain-start` to `mortgage`, `#chain-end` to `repo`, click `#chain-trace-btn`.
3. Confirm `#chain-results` now contains exactly 7 elements with class `chain-card`.
4. Confirm none of those 7 cards contain an element with class `chain-net-badge` (matches Task
   1's finding that no mortgage->repo path is all-forward).
5. Set `#chain-start` to `ffr`, `#chain-end` to `tech`, click `#chain-trace-btn` again. Confirm
   at least one `.chain-card` now contains a `.chain-net-badge`.
6. Set `#chain-start` and `#chain-end` to the same value (e.g. both `mortgage`), click trace.
   Confirm `#chain-results` shows the "Pick two different nodes." message, not an error.
7. Check the browser console for errors after all of the above — expect zero.

- [ ] **Step 5: Run the full test suite one more time**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests && python3 -m unittest test_calibrate && python3 -m unittest scripts.test_generate_narration -v`

Expected: all tests still PASS (this task didn't touch narration or data-pipeline code, so this
is a regression check, not expected to find anything task-specific).

- [ ] **Step 6: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: add chain-reaction UI (node pickers, result cards, wiring)"
```

---

## After all 3 tasks

Push per the project's established convention (rebase onto any GitHub Actions cron commits that
landed in the meantime, push, then verify the "pages build and deployment" run for the final
commit shows `completed`/`success` via the authenticated Actions API — a fast push is not proof
of a successful deploy, per this project's own hard-won lesson from a prior Pages outage).
