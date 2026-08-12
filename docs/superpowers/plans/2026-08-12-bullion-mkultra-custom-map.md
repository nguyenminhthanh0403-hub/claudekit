# Mk Ultra — User-Customizable Map (Shareable Node Selection) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a viewer of `bullion_mkultra.html` hide any combination of individual nodes (not just whole layers) and get a URL that reproduces exactly that view.

**Architecture:** Replace the existing in-memory-only `activeLayers` group filter with a single `excludedNodes: Set<string>` of node ids, serialized to/from a `?hide=` URL query param via `history.replaceState`. The renderer's group-based `setLayerFilter` becomes an id-based `setNodeFilter`, combined via the *same* `&&` pattern the codebase already uses to AND the layer filter with hub/satellite expand-collapse visibility — nothing about that existing mechanism changes. A small number of low-degree (≤3-neighbor) hidden nodes get synthetic dashed "indirect" connectors between their kept neighbors, precomputed once at load time since candidate pairs are static (derived from the fixed `LINKS`/`PLUMBING_LINKS` graph, not from runtime hide-state). The composite health score gains an `excludedNodes` parameter that routes a stress field into the existing "missing" path when its backing node is hidden.

**Tech Stack:** Vanilla JS (ES2017+), Three.js (already vendored inline in `bullion_mkultra.html`), Python `unittest` + `node` subprocess for JS-parity tests (existing project pattern, see `tests/test_macro_engine_js_parity.py`), headless Chrome via the `headless-chrome-verification` skill for browser/WebGL verification.

## Global Constraints

- Single file touched for all product code: `bullion-live-map/bullion_mkultra.html`. No Python pipeline files (`fetch_bullion_data.py`, `backfill_baseline.py`), no workflow files, no `data.json` schema changes — this is a client-side render/score-input filter only (spec Non-goals).
- `bullion_mk11.html` through `bullion_mk18.html` must stay byte-unchanged (verify via `sha256sum` before/after, per this project's existing frozen-file convention).
- No new third-party JS dependencies — build on what's already vendored (Three.js, D3 — both already inline in the file).
- New pure/testable JS functions get JS↔Python parity tests following the exact pattern in `bullion-live-map/tests/test_macro_engine_js_parity.py`: extract the real shipped JS out of `bullion_mkultra.html` by string markers, run it via a real `node` subprocess against synthetic fixtures, assert in Python. Skip (not fail) if `node` isn't on `PATH`.
- **Task order matters here more than usual**, because several tasks call functions another task creates: Tasks 1-3 are pure/standalone (no cross-task calls). Task 4 (renderer) must land *before* Task 6 (legend) and Task 7 (picker), because both of those call `Renderer.setNodeFilter` in their own browser-verification steps — landing the renderer late would leave every earlier UI task's own verification unrunnable. Do not reorder tasks.
- Indirect-link synthesis: only for a hidden node with ≤3 kept neighbors; one hop only; hub nodes (>3 neighbors) just drop their links, no synthesis (spec Design §2).
- Composite score: only the 6 nodes backing its 7 fields (`credit`, `vix`, `equit`, `fed`, `repo`, `yield`) affect the score when hidden; every other node hide is a pure visual/link filter with no score effect (spec Design §3, spec Non-goals).

---

## File Structure

- **`bullion-live-map/bullion_mkultra.html`** (modified in place, no new files):
  - `computeIndirectCandidates` (Task 2) inserted near line 1670, right after the existing `neighborsOf` adjacency-list construction — chosen because it needs nothing but `NODES`/`LINKS`, both already defined by that point, and it's needed early by Task 4's renderer work.
  - `excludedNodes` + `serializeExcludedIds`/`parseExcludedIds` (Task 1) replace `activeLayers` at line 1733.
  - `FIELD_TO_NODE` + the `computeCompositeScore` signature change (Task 3) go right before `computeCompositeScore` itself, line 3987.
  - Renderer changes (Task 4): `buildLinkObjects()` (line 1983) gains a sibling `buildIndirectLinkObjects()`; `setLayerFilter` (line 2691) becomes `setNodeFilter`; `setVisibility` (line 2609) gains one block for indirect-connector visibility.
  - `loadExcludedFromURL`/`syncExcludedToURL`/Copy Link button (Task 5) go near the `excludedNodes` declaration and near `#legend-box` (line 802).
  - `buildLegend()`/`applyLayerFilter()` (lines 3231-3263, Task 6) become bulk-exclude operations on `excludedNodes` with a new partial-state visual.
  - New per-node picker drawer (Task 7), following the exact markup/JS pattern of the existing `trends-toggle`/`glossary-toggle` drawers (lines 909-917, 3525-3547).
- **`bullion-live-map/tests/test_custom_map_js_parity.py`** (new file): parity tests for the new pure functions (`computeIndirectCandidates`, `serializeExcludedIds`, `parseExcludedIds`) and the `FIELD_TO_NODE`/`NODE_LIVE_FIELD` consistency check.
- **`bullion-live-map/tests/test_macro_engine_js_parity.py`** (modified): extended with tests for `computeCompositeScore`'s new `excludedNodes` parameter; one brittle string marker fixed (Task 3).

---

### Task 1: Pure URL state helpers (serialize/parse excluded ids)

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` (insert at line 1733, replacing `let activeLayers = new Set(LAYER_ORDER);`)
- Create: `bullion-live-map/tests/test_custom_map_js_parity.py`

**Interfaces:**
- Produces: `serializeExcludedIds(excludedNodes: Set<string>) -> string` — comma-joined, ids sorted ascending for deterministic output.
- Produces: `parseExcludedIds(hideParam: string|null|undefined, validIds: string[]) -> Set<string>` — splits `hideParam` on commas, keeps only ids present in `validIds`, silently drops everything else (including `null`/empty input, which returns an empty Set).
- Produces: `excludedNodes` — module-scope `let`, the state every later task reads/writes. Default: empty Set (nothing hidden).

- [ ] **Step 1: Write the failing parity test**

Create `bullion-live-map/tests/test_custom_map_js_parity.py`:

```python
"""JS<->Python parity guard for the Mk Ultra custom-map feature's pure functions.

Mirrors test_macro_engine_js_parity.py: extracts the real shipped JS out of
bullion_mkultra.html, runs it via a real `node` process against synthetic
fixtures, and checks the result matches a hand-computed expectation. Skipped
(not failed) if `node` isn't on PATH.
"""
import json
import os
import shutil
import subprocess
import unittest

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "bullion_mkultra.html")


def _extract_between(html, start_marker, end_marker):
    start = html.index(start_marker)
    end = html.index(end_marker, start)
    return html[start:end]


def _run_node(script):
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError("node script failed: " + proc.stderr[:2000])
    return json.loads(proc.stdout)


@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class TestExcludedIdsParity(unittest.TestCase):
    def setUp(self):
        with open(MAP_PATH) as f:
            html = f.read()
        # End marker is the very next existing line after this task's
        # insertion point (line 1733 today) -- self-contained, doesn't
        # depend on any other task having run yet.
        # _extract_between's slice already starts at start_marker, so no
        # re-prepending is needed here.
        self.snippet = _extract_between(
            html,
            "function serializeExcludedIds(",
            "let allExpanded = false;",
        )

    def test_serialize_sorts_and_joins(self):
        script = self.snippet + """
process.stdout.write(JSON.stringify(serializeExcludedIds(new Set(['zeta','alpha','mid']))));
"""
        result = _run_node(script)
        self.assertEqual(result, "alpha,mid,zeta")

    def test_serialize_empty_set_is_empty_string(self):
        script = self.snippet + """
process.stdout.write(JSON.stringify(serializeExcludedIds(new Set())));
"""
        result = _run_node(script)
        self.assertEqual(result, "")

    def test_parse_keeps_only_valid_ids(self):
        script = self.snippet + """
const s = parseExcludedIds('alpha,ghost,mid', ['alpha','mid','zeta']);
process.stdout.write(JSON.stringify([...s].sort()));
"""
        result = _run_node(script)
        self.assertEqual(result, ["alpha", "mid"])

    def test_parse_null_or_empty_returns_empty_set(self):
        script = self.snippet + """
const a = parseExcludedIds(null, ['alpha']);
const b = parseExcludedIds('', ['alpha']);
process.stdout.write(JSON.stringify([[...a], [...b]]));
"""
        result = _run_node(script)
        self.assertEqual(result, [[], []])

    def test_round_trip(self):
        script = self.snippet + """
const original = new Set(['b','a','c']);
const s = serializeExcludedIds(original);
const parsed = parseExcludedIds(s, ['a','b','c']);
process.stdout.write(JSON.stringify([...parsed].sort()));
"""
        result = _run_node(script)
        self.assertEqual(result, ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd bullion-live-map && python3 -m unittest tests.test_custom_map_js_parity -v`
Expected: FAIL / ERROR — `serializeExcludedIds` doesn't exist yet in `bullion_mkultra.html`, so `_extract_between` raises `ValueError: substring not found`.

- [ ] **Step 3: Implement the functions in `bullion_mkultra.html`**

Replace line 1733 (`let activeLayers = new Set(LAYER_ORDER); // layer filter state`) with:

```javascript
// ── Custom-map node filter (replaces the old activeLayers group filter) ───
// A node/link is hidden iff its id is in this set. Default: nothing hidden.
// Kept in sync with the URL's ?hide= param -- see syncExcludedToURL/
// loadExcludedFromURL (Task 5), wired up in the boot sequence.
let excludedNodes = new Set();

function serializeExcludedIds(excludedSet) {
  return [...excludedSet].sort().join(',');
}

function parseExcludedIds(hideParam, validIds) {
  const valid = new Set(validIds);
  const result = new Set();
  if (!hideParam) return result;
  hideParam.split(',').forEach(id => {
    if (valid.has(id)) result.add(id);
  });
  return result;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd bullion-live-map && python3 -m unittest tests.test_custom_map_js_parity -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html bullion-live-map/tests/test_custom_map_js_parity.py
git commit -m "Mk Ultra: add excludedNodes state + URL serialize/parse helpers"
```

---

### Task 2: Pure indirect-link candidate computation

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` (insert near line 1670, right after the existing `neighborsOf` adjacency-list construction, before the `// ── Chain-reaction hypothesis` comment block)
- Modify: `bullion-live-map/tests/test_custom_map_js_parity.py`

**Interfaces:**
- Consumes: nothing from Task 1 (fully standalone — takes its graph as plain arguments, not the module-scope `NODES`/`LINKS`, so it stays independently testable).
- Produces: `computeIndirectCandidates(nodeIds: string[], links: Array<{s: string, t: string}>) -> Array<{s: string, t: string, via: string}>` — for every node `via` with ≤3 total neighbors (computed from `links`), emits one entry per pair of `via`'s neighbors that does NOT already have a direct link between them (checked both directions). Zero entries for a degree-≤1 node (no pair to form) or a degree->3 node (hub, skipped entirely — no partial output).

- [ ] **Step 1: Write the failing test**

Append to `bullion-live-map/tests/test_custom_map_js_parity.py`, as a new test class in the same file:

```python
@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class TestIndirectCandidatesParity(unittest.TestCase):
    def setUp(self):
        with open(MAP_PATH) as f:
            html = f.read()
        # End marker is the existing comment immediately after this task's
        # insertion point -- self-contained, doesn't depend on Task 1.
        # _extract_between's slice already starts at start_marker, so no
        # re-prepending is needed here (same fix as Task 1's setUp).
        self.snippet = _extract_between(
            html,
            "function computeIndirectCandidates(",
            "function findLinkBetween(a, b) {",
        )

    def test_degree_one_node_produces_no_candidates(self):
        script = self.snippet + """
const nodes = ['a','b'];
const links = [{s:'a', t:'b'}];
process.stdout.write(JSON.stringify(computeIndirectCandidates(nodes, links)));
"""
        result = _run_node(script)
        self.assertEqual(result, [])

    def test_degree_two_node_produces_one_candidate(self):
        script = self.snippet + """
const nodes = ['a','hub','b'];
const links = [{s:'a', t:'hub'}, {s:'hub', t:'b'}];
process.stdout.write(JSON.stringify(computeIndirectCandidates(nodes, links)));
"""
        result = _run_node(script)
        self.assertEqual(len(result), 1)
        pair = {result[0]['s'], result[0]['t']}
        self.assertEqual(pair, {'a', 'b'})
        self.assertEqual(result[0]['via'], 'hub')

    def test_degree_three_node_produces_three_candidates(self):
        script = self.snippet + """
const nodes = ['a','hub','b','c'];
const links = [{s:'a', t:'hub'}, {s:'hub', t:'b'}, {s:'hub', t:'c'}];
process.stdout.write(JSON.stringify(computeIndirectCandidates(nodes, links)));
"""
        result = _run_node(script)
        self.assertEqual(len(result), 3)

    def test_degree_four_hub_produces_no_candidates(self):
        script = self.snippet + """
const nodes = ['a','hub','b','c','d'];
const links = [{s:'a',t:'hub'},{s:'hub',t:'b'},{s:'hub',t:'c'},{s:'hub',t:'d'}];
process.stdout.write(JSON.stringify(computeIndirectCandidates(nodes, links)));
"""
        result = _run_node(script)
        self.assertEqual(result, [])

    def test_existing_direct_link_is_not_duplicated(self):
        script = self.snippet + """
const nodes = ['a','hub','b'];
// a-b already has a real direct link, in addition to both routing through hub.
const links = [{s:'a', t:'hub'}, {s:'hub', t:'b'}, {s:'a', t:'b'}];
process.stdout.write(JSON.stringify(computeIndirectCandidates(nodes, links)));
"""
        result = _run_node(script)
        self.assertEqual(result, [])

    def test_reverse_direction_direct_link_is_also_not_duplicated(self):
        script = self.snippet + """
const nodes = ['a','hub','b'];
const links = [{s:'a', t:'hub'}, {s:'hub', t:'b'}, {s:'b', t:'a'}];
process.stdout.write(JSON.stringify(computeIndirectCandidates(nodes, links)));
"""
        result = _run_node(script)
        self.assertEqual(result, [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd bullion-live-map && python3 -m unittest tests.test_custom_map_js_parity -v`
Expected: FAIL — `computeIndirectCandidates` not yet defined (this new class fails; `TestExcludedIdsParity` from Task 1 still passes).

- [ ] **Step 3: Implement `computeIndirectCandidates` in `bullion_mkultra.html`**

Insert immediately after the existing block that ends at line 1670 (`LINKS.forEach(l => { neighborsOf[l.s].add(l.t); neighborsOf[l.t].add(l.s); });`), and immediately before the existing `// ── Chain-reaction hypothesis:` comment:

```javascript
// ── Indirect-link candidates for the custom-map feature ────────────────────
// Static and precomputable: the pairs a hidden low-degree node WOULD connect
// don't depend on which nodes happen to be hidden right now, only on the
// fixed LINKS/PLUMBING_LINKS graph. Computed once at load; the renderer just
// toggles which of these are visible based on the live excludedNodes state.
// Hub nodes (>3 neighbors) are skipped entirely -- a hub's full neighbor-pair
// closure would be a two-digit-plus link explosion, not a helpful "indirect
// connection" visual (see the design doc's degree count).
function computeIndirectCandidates(nodeIds, links) {
  const neighbors = {};
  nodeIds.forEach(id => { neighbors[id] = new Set(); });
  links.forEach(l => {
    if (!neighbors[l.s] || !neighbors[l.t]) return;
    neighbors[l.s].add(l.t);
    neighbors[l.t].add(l.s);
  });
  const hasDirectLink = (a, b) => links.some(l =>
    (l.s === a && l.t === b) || (l.s === b && l.t === a));
  const candidates = [];
  nodeIds.forEach(via => {
    const nbrs = [...neighbors[via]];
    if (nbrs.length === 0 || nbrs.length > 3) return;
    for (let i = 0; i < nbrs.length; i++) {
      for (let j = i + 1; j < nbrs.length; j++) {
        const a = nbrs[i], b = nbrs[j];
        if (hasDirectLink(a, b)) continue;
        candidates.push({ s: a, t: b, via });
      }
    }
  });
  return candidates;
}
```

- [ ] **Step 4: Run both test classes to verify they pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_custom_map_js_parity -v`
Expected: PASS (11 tests total between both classes).

- [ ] **Step 5: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html bullion-live-map/tests/test_custom_map_js_parity.py
git commit -m "Mk Ultra: add computeIndirectCandidates for low-degree hidden-node connectors"
```

---

### Task 3: Composite score honors excludedNodes

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html:3987` (`computeCompositeScore`) and the area just above it (insert `FIELD_TO_NODE` after `COMPOSITE_MIN_FIELDS_FOR_MEASURED`/`_clip3` at lines 3983-3985)
- Modify: `bullion-live-map/tests/test_macro_engine_js_parity.py`

**Interfaces:**
- Consumes: `excludedNodes` (Task 1's state variable) at call sites elsewhere in the file.
- Produces: `computeCompositeScore(live, excludedNodes)` — same return shape as before (`{score, tier, leadingCategory, categoryContributions, fieldsUsed, fieldsMissing}`); a field whose `FIELD_TO_NODE[f]` is present in `excludedNodes` is now routed into `fieldsMissing` exactly like a numerically-missing field.

- [ ] **Step 1: Find every existing call site of `computeCompositeScore`**

Run: `grep -n "computeCompositeScore(" bullion-live-map/bullion_mkultra.html`

Expected output includes the function definition at line 3987 plus one or more call sites elsewhere (e.g. inside the "Run macro analysis" handler). Note each call site's line number — every one needs `excludedNodes` added as the second argument in Step 6.

- [ ] **Step 2: Write the failing parity test**

Append to `bullion-live-map/tests/test_macro_engine_js_parity.py`, inside `TestComputeCompositeScoreParity`:

```python
    def test_hiding_a_backing_node_drops_its_field_from_fieldsUsed(self):
        # credit backs both hy_oas and ig_oas (NODE_LIVE_FIELD: credit -> ['hy_oas','ig_oas']).
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
fields.forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
const withoutCredit = computeCompositeScore(live, new Set(['credit']));
process.stdout.write(JSON.stringify(withoutCredit));
"""
        result = _run_node(script)
        self.assertNotIn('hy_oas', result['fieldsUsed'])
        self.assertNotIn('ig_oas', result['fieldsUsed'])
        self.assertIn('hy_oas', result['fieldsMissing'])
        self.assertIn('ig_oas', result['fieldsMissing'])

    def test_hiding_a_non_backing_node_has_no_effect(self):
        # 'geo' backs no composite field at all.
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
fields.forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
const withGeoHidden = computeCompositeScore(live, new Set(['geo']));
const withNothingHidden = computeCompositeScore(live, new Set());
process.stdout.write(JSON.stringify([withGeoHidden.fieldsUsed.sort(), withNothingHidden.fieldsUsed.sort()]));
"""
        result = _run_node(script)
        self.assertEqual(result[0], result[1])

    def test_no_excludedNodes_argument_behaves_as_before(self):
        # Backward-compatible: an omitted second arg must not throw and must
        # behave identically to an empty set.
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
fields.forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertEqual(len(result['fieldsMissing']), 0)
```

Also add, as a standalone test class in the same file (checks `FIELD_TO_NODE` against the real `NODE_LIVE_FIELD`, catching future drift between the two):

```python
@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class TestFieldToNodeConsistency(unittest.TestCase):
    def test_field_to_node_matches_node_live_field(self):
        with open(MAP_PATH) as f:
            html = f.read()
        ftn_start = html.index("const FIELD_TO_NODE = ")
        ftn_end = html.index("};", ftn_start) + 2
        field_to_node_src = html[ftn_start:ftn_end]

        nlf_start = html.index("const NODE_LIVE_FIELD = {")
        nlf_end = html.index("};", nlf_start) + 2
        node_live_field_src = html[nlf_start:nlf_end]

        script = field_to_node_src + "\n" + node_live_field_src + """
const reverseFromNodeLiveField = {};
Object.entries(NODE_LIVE_FIELD).forEach(([node, fields]) => {
  fields.forEach(f => { reverseFromNodeLiveField[f] = node; });
});
const mismatches = [];
Object.entries(FIELD_TO_NODE).forEach(([field, node]) => {
  if (reverseFromNodeLiveField[field] !== node) {
    mismatches.push({field, expected: node, actual: reverseFromNodeLiveField[field]});
  }
});
process.stdout.write(JSON.stringify(mismatches));
"""
        result = _run_node(script)
        self.assertEqual(result, [], f"FIELD_TO_NODE drifted from NODE_LIVE_FIELD: {result}")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd bullion-live-map && python3 -m unittest tests.test_macro_engine_js_parity -v`
Expected: FAIL — `FIELD_TO_NODE` doesn't exist, `computeCompositeScore` doesn't accept a second argument's semantics yet.

- [ ] **Step 4: Implement `FIELD_TO_NODE`**

Insert immediately before line 3987 (`function computeCompositeScore(live) {`), i.e. right after the existing `function _clip3(z) { return Math.max(-3, Math.min(3, z)); }` line:

```javascript
// Explicit, hand-kept map from a composite-score field to the node whose
// visibility should gate it -- kept local (not derived from NODE_LIVE_FIELD,
// which is defined ~700 lines later) so this function stays self-contained
// and doesn't create a forward-reference. TestFieldToNodeConsistency in
// tests/test_macro_engine_js_parity.py cross-checks this against the real
// NODE_LIVE_FIELD map on every test run, so drift between the two is caught,
// not silent.
const FIELD_TO_NODE = {
  hy_oas: 'credit', ig_oas: 'credit', vix: 'vix', spx: 'equit',
  fed_bs: 'fed', rrp: 'repo', curve_slope: 'yield',
};
```

- [ ] **Step 5: Update `computeCompositeScore`'s signature and field-missing check**

Change the function signature and the first check inside the `fields.forEach` loop:

```javascript
function computeCompositeScore(live, excludedNodes) {
  const excluded = excludedNodes || new Set();
  const fields = Object.keys(BASELINE_STATS.stress_sign);
  const liveWithSlope = Object.assign({}, live);
  if (typeof live.us10y === 'number' && typeof live.us2y === 'number') {
    liveWithSlope.curve_slope = live.us10y - live.us2y;
  }
  const fieldsUsed = [], fieldsMissing = [];
  const categorySums = {}, categoryCounts = {};
  fields.forEach(f => {
    const stat = BASELINE_STATS.fields[f];
    const v = liveWithSlope[f];
    const backingNode = FIELD_TO_NODE[f];
    if (backingNode && excluded.has(backingNode)) { fieldsMissing.push(f); return; }
    if (typeof v !== 'number' || !stat || !stat.std) { fieldsMissing.push(f); return; }
    fieldsUsed.push(f);
    const z = _clip3((v - stat.mean) / stat.std);
    const signedZ = BASELINE_STATS.stress_sign[f] * z;
    const cat = BASELINE_STATS.category[f];
    categorySums[cat] = (categorySums[cat] || 0) + signedZ;
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  });
```

Leave everything from `const categoryContributions = {};` through the end of the function exactly as it is today — only the signature line and the field-loop's first check change.

- [ ] **Step 6: Fix the brittle extraction marker in the other test helper**

In `_extract_js_snippet_through_node_mults` (same test file, around line 57), the line:

```python
    composite_start = html.index("function computeCompositeScore(live)")
```

now fails to match, since the real signature is `function computeCompositeScore(live, excludedNodes)`. Change it to a signature-independent prefix match:

```python
    composite_start = html.index("function computeCompositeScore(")
```

- [ ] **Step 7: Update every existing call site to pass `excludedNodes`**

For each call site found in Step 1 (other than the function definition itself), add `, excludedNodes` as the second argument — e.g. `computeCompositeScore(live)` becomes `computeCompositeScore(live, excludedNodes)`. Since `excludedNodes` is declared at module (script) scope by Task 1, it's in scope at every call site without any import/threading needed.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd bullion-live-map && python3 -m unittest tests.test_macro_engine_js_parity -v`
Expected: PASS (all existing + new tests, including `TestFieldToNodeConsistency`).

- [ ] **Step 9: Run the full Python suite to confirm nothing else broke**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests -v`
Expected: all green (85+ tests, per the latest handoff's baseline count, plus this task's additions).

- [ ] **Step 10: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html bullion-live-map/tests/test_macro_engine_js_parity.py
git commit -m "Mk Ultra: composite score routes hidden backing nodes into fieldsMissing"
```

---

### Task 4: Renderer — id-based node/link filter and indirect-connector geometry

This lands *before* the legend/picker UI tasks (5-7 come after it) specifically so that `Renderer.setNodeFilter` exists by the time any UI code tries to call it. Verification here is via direct DevTools-protocol calls to the Renderer's exposed functions, not via clicking UI that doesn't exist yet.

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html:1983-2048` (`buildLinkObjects`), `:2609-2618` (`setVisibility`), `:2691-2704` (`setLayerFilter`), `:2729-2738` (Renderer's returned public surface)

**Interfaces:**
- Consumes: `computeIndirectCandidates` (Task 2), `NODES`, `LINKS` (merged), `ID_TO_LABEL` (existing, line 3338 — defined after the Renderer IIFE in file order, but only referenced when `build()` actually runs at boot time, by which point it's assigned — same safe pattern the file already relies on elsewhere for forward-declared top-level consts). Not yet consumed by anything outside the Renderer in this task.
- Produces: `Renderer.setNodeFilter(excludedNodes: Set<string>)` — replaces `Renderer.setLayerFilter`; Task 6 (legend) will be the first real caller.

- [ ] **Step 1: Add `buildIndirectLinkObjects()`, a sibling of `buildLinkObjects()`**

Immediately after the existing `buildLinkObjects()` function (ends at line 2048), add:

```javascript
  // Synthetic dashed connectors for hidden low-degree nodes (Task 2's
  // computeIndirectCandidates). Built once, same as real links -- visibility
  // toggles per setNodeFilter call, geometry never rebuilt at runtime.
  // Deliberately simpler than buildLinkObjects: no arrowhead (not a causal
  // claim, just "these are still connected"), always dashed, neutral color,
  // fixed opacity matching the existing UNVERIFIED tier.
  let indirectLinkObjs = [];
  function buildIndirectLinkObjects(candidates) {
    indirectLinkObjs = [];
    const RADIAL_SEGS = 6;
    const color = new THREE.Color('#8891a6'); // same neutral fallback recolor() uses for untinted nodes
    const tubeR = 0.45; // matches w:1 real links
    const baseOpacity = 0.40; // matches CONF.UNVERIFIED's baseOpacity in buildLinkObjects
    candidates.forEach((c, idx) => {
      const s = nodesDataIndex[c.s], t = nodesDataIndex[c.t];
      if (!s || !t) return;
      const srcPos = new THREE.Vector3(s.x, s.y, s.z);
      const tgtPos = new THREE.Vector3(t.x, t.y, t.z);
      const chordLen = srcPos.distanceTo(tgtPos);
      const midDir = srcPos.clone().add(tgtPos).multiplyScalar(0.5).normalize();
      const avgR = (srcPos.length() + tgtPos.length()) / 2;
      const bulge = Math.min(chordLen * 0.32, SPHERE_R * 0.9);
      const control = midDir.multiplyScalar(avgR + bulge);
      const curve = new THREE.QuadraticBezierCurve3(srcPos, control, tgtPos);
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: baseOpacity });
      const group = new THREE.Group();
      const DASHES = 7;
      for (let i = 0; i < DASHES; i += 2) {
        const t0 = i / DASHES, t1 = Math.min((i + 0.7) / DASHES, 1);
        const sub = subCurve(curve, t0, t1, 4);
        group.add(new THREE.Mesh(new THREE.TubeGeometry(sub, 4, tubeR, RADIAL_SEGS, false), mat));
      }
      scene.add(group);
      indirectLinkObjs.push({
        group, mat, baseOpacity, source: c.s, target: c.t, via: c.via, index: idx,
      });
    });
  }
```

- [ ] **Step 2: Call `buildIndirectLinkObjects` from `build()`**

Run: `grep -n "buildLinkObjects();" bullion-live-map/bullion_mkultra.html` to find where `buildLinkObjects()` is invoked inside `async function build(nodesArr)` (line 2439). Immediately after that call, add:

```javascript
    buildIndirectLinkObjects(computeIndirectCandidates(nodesArr.map(n => n.id), LINKS));
```

- [ ] **Step 3: Add Renderer-internal state tracking for the current excluded set**

Near the other module-scoped `let` declarations at the top of the Renderer IIFE (alongside `let linkObjs = [];`), add:

```javascript
  let currentExcludedNodesSet = new Set();
```

- [ ] **Step 4: Replace `setLayerFilter` with `setNodeFilter`**

Replace the existing `setLayerFilter` function (lines 2691-2704) entirely:

```javascript
  function setNodeFilter(excludedNodesSet) {
    if (!ready) return;
    currentExcludedNodesSet = excludedNodesSet;
    Object.keys(meshById).forEach(id => {
      const d = nodesDataIndex[id];
      layerVis[id] = !d || !excludedNodesSet.has(id);
      applyMeshVisibility(id);
    });
    linkObjs.forEach(lo => {
      linkLayerVis[lo.index] = !excludedNodesSet.has(lo.source) && !excludedNodesSet.has(lo.target);
      applyLinkVisibility(lo);
    });
    applyIndirectVisibility();
  }

  // An indirect connector shows only when its `via` node is hidden AND both
  // its real endpoints are currently visible per BOTH the node filter and the
  // hub/satellite expand-collapse state (`baseVisible`, populated by
  // setVisibility) -- so it never appears pointing at a node that's merely
  // collapsed, not actually excluded.
  function applyIndirectVisibility() {
    indirectLinkObjs.forEach(lo => {
      const filterVisible = currentExcludedNodesSet.has(lo.via)
        && !currentExcludedNodesSet.has(lo.source)
        && !currentExcludedNodesSet.has(lo.target);
      const baseVis = !!(baseVisible[lo.source] && baseVisible[lo.target]);
      lo.group.visible = filterVisible && baseVis;
    });
  }
```

- [ ] **Step 5: Call `applyIndirectVisibility()` from `setVisibility` too**

`setVisibility` (line 2609) updates `baseVisible` (the hub/satellite expand-collapse state) but doesn't currently touch indirect connectors, which also depend on `baseVisible`. Add one line at the end of `setVisibility`, right after its existing `linkObjs.forEach(...)` block:

```javascript
    applyIndirectVisibility();
```

- [ ] **Step 6: Update the Renderer's public return surface**

At line 2729-2738 (the `return { ... }` object), change `setLayerFilter,` to `setNodeFilter,`.

- [ ] **Step 7: Browser-verify via direct console calls (no UI exists yet)**

Using the `headless-chrome-verification` skill (isolated `--user-data-dir`, served over `http://localhost`, not `file://`), load the page, then drive it entirely via DevTools-protocol `eval`:

1. `Renderer.setNodeFilter(new Set(['dxy_fx']))` (a degree-2 node) — read back `indirectLinkObjs` and confirm exactly one has `group.visible === true` (assuming its neighbors are within the current hub-expand visible set; if not, first call whatever exposes "Expand All" — check for a global toggle function or simulate a click on `#expand-all-btn` if one exists — to put `baseVisible` in a state where the test is meaningful).
2. `Renderer.setNodeFilter(new Set(['equit']))` (14-neighbor hub) — confirm every `indirectLinkObjs` entry has `group.visible === false`, and confirm every real `linkObjs` entry touching `equit` also has `group.visible === false`.
3. `Renderer.setNodeFilter(new Set(['dxy_fx', <one of dxy_fx's two neighbors>]))` — confirm the indirect connector for that pair does NOT become visible (both-real-endpoints-visible rule).
4. `Renderer.setNodeFilter(new Set())` — confirm everything returns to its prior (pre-filter) visibility, i.e. this task introduced no regression to the unfiltered state.

- [ ] **Step 8: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: renderer supports id-based node filter and indirect-link connectors"
```

---

### Task 5: excludedNodes boot-load, URL sync, and Copy Link button

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` — new functions near the Task 1 `excludedNodes` declaration; new button wired near the existing `#legend-box` (line 802); boot-sequence call added wherever the app's existing startup code runs (search for where `buildLegend()` is first invoked).

**Interfaces:**
- Consumes: `excludedNodes`, `serializeExcludedIds`/`parseExcludedIds` (Task 1), global `NODES` array (existing).
- Produces: `loadExcludedFromURL()` — call once at boot, seeds `excludedNodes` from `location.search`. `syncExcludedToURL()` — call after every mutation of `excludedNodes`, writes `?hide=...` via `history.replaceState`. `copyShareLink()` — click handler for the new button.

- [ ] **Step 1: Find the boot sequence's call to `buildLegend()`**

Run: `grep -n "buildLegend();" bullion-live-map/bullion_mkultra.html`

Note its line number — `loadExcludedFromURL()` must run *before* that call, since Task 6's reworked `buildLegend()` needs `excludedNodes` already seeded to render the correct initial `.off`/partial state.

- [ ] **Step 2: Implement `loadExcludedFromURL` and `syncExcludedToURL`**

Add right after the `excludedNodes`/`serializeExcludedIds`/`parseExcludedIds` block from Task 1:

```javascript
function loadExcludedFromURL() {
  const params = new URLSearchParams(location.search);
  excludedNodes = parseExcludedIds(params.get('hide'), NODES.map(n => n.id));
}

function syncExcludedToURL() {
  const params = new URLSearchParams(location.search);
  const serialized = serializeExcludedIds(excludedNodes);
  if (serialized) params.set('hide', serialized); else params.delete('hide');
  const newSearch = params.toString();
  const newUrl = location.pathname + (newSearch ? '?' + newSearch : '') + location.hash;
  history.replaceState(null, '', newUrl);
}
```

- [ ] **Step 3: Call `loadExcludedFromURL()` at boot, before `buildLegend()`**

At the call site found in Step 1, insert `loadExcludedFromURL();` on the line immediately before the existing `buildLegend();` call.

- [ ] **Step 4: Add the Copy Link button markup**

In the HTML, immediately after `<div id="legend-box"></div>` (line 802), add:

```html
<button class="btn" id="copy-link-btn" title="Copy a link to this exact custom view">Copy link</button>
<input type="text" id="copy-link-fallback" class="hidden" readonly
       style="width:100%;margin-top:4px;font-size:11px"
       aria-label="Copy this link manually">
```

- [ ] **Step 5: Implement the click handler with clipboard fallback**

Add near the other button-wiring `addEventListener` calls (e.g. near line 5863-5865, alongside `trends-toggle`/`metricguide-toggle`/`manual-toggle`):

```javascript
function copyShareLink() {
  const url = location.href;
  const fallback = document.getElementById('copy-link-fallback');
  const btn = document.getElementById('copy-link-btn');
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(() => {
      const original = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = original; }, 1500);
    }).catch(() => showFallback(url, fallback));
  } else {
    showFallback(url, fallback);
  }
}
function showFallback(url, fallback) {
  fallback.value = url;
  fallback.classList.remove('hidden');
  fallback.focus();
  fallback.select();
}
document.getElementById('copy-link-btn').addEventListener('click', copyShareLink);
```

- [ ] **Step 6: Browser-verify boot load and copy link**

Using `headless-chrome-verification`:
1. Load `http://localhost:<port>/bullion_mkultra.html?hide=cpi,nfp,ghost-id` — confirm via DevTools-protocol eval that `excludedNodes` equals `Set{'cpi','nfp'}` (the stale `ghost-id` silently dropped).
2. Load with no `?hide=` param — confirm `excludedNodes` is an empty Set.
3. Click "Copy link" — confirm (via a `document.execCommand('paste')`-style check or by re-reading the clipboard through the DevTools protocol) that the copied text equals `location.href`.

- [ ] **Step 7: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: wire excludedNodes to ?hide= URL param, add Copy Link button"
```

---

### Task 6: Legend layer-toggle becomes bulk node exclusion, with partial state

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html:3231-3263` (`buildLegend`, `applyLayerFilter`)
- Modify: CSS near line 322-328 (`.legend-item` rules)

**Interfaces:**
- Consumes: `excludedNodes`, `syncExcludedToURL()` (Task 5), `Renderer.setNodeFilter` (Task 4), `NODES`, `GROUP_COLOR`, `LAYER_LABELS`, `LAYER_ORDER` (all existing).
- Produces: `applyNodeFilter()` — replaces `applyLayerFilter()`; calls `Renderer.setNodeFilter(excludedNodes)`. `legendLayerClass(group)`, `toggleLayerExcluded(group)`, `refreshLegendClasses()` — the last one is consumed by Task 7's picker.

- [ ] **Step 1: Add the `.partial` CSS rule**

Immediately after the existing `.legend-item.off { opacity: 0.35; }` rule (around line 323), add:

```css
  .legend-item.partial { opacity: 0.65; }
```

- [ ] **Step 2: Rewrite `buildLegend()` to reflect and toggle `excludedNodes`**

Replace the existing `buildLegend()` function body (lines 3231-3260) — keep the `causalKey` HTML block's first two `<div class="legend-causal">...</div>` sections byte-for-byte identical to today, only change the final layers line and the per-layer item markup/click handler:

```javascript
function buildLegend() {
  const el = document.getElementById('legend-box');
  const causalKey =
    `<div class="legend-causal">
       <div class="legend-causal-title">Link effect</div>
       <div class="legend-item static"><span class="legend-line" style="background:#7bbf8e"></span>Amplifies</div>
       <div class="legend-item static"><span class="legend-line" style="background:#e0654f"></span>Dampens</div>
       <div class="legend-item static"><span class="legend-line" style="background:#e0b15a"></span>Conditional</div>
     </div>
     <div class="legend-causal">
       <div class="legend-causal-title">Evidence</div>
       <div class="legend-item static"><span class="legend-line" style="background:var(--text-dim);opacity:0.95"></span>Measured &mdash; fitted on live data</div>
       <div class="legend-item static"><span class="legend-line" style="background:var(--text-dim);opacity:0.55"></span>Directional &mdash; sourced mechanism</div>
       <div class="legend-item static"><span class="legend-line" style="background:repeating-linear-gradient(90deg,var(--text-dim) 0 4px,transparent 4px 8px);opacity:0.55"></span>Dashed = unverified</div>
     </div>
     <div class="legend-causal-title">Layers (tap to hide)</div>`;
  el.innerHTML = causalKey + LAYER_ORDER.map(g => {
    const cls = legendLayerClass(g);
    return `<div class="legend-item ${cls}" data-group="${g}">
       <div class="legend-dot" style="background:${GROUP_COLOR[g]}"></div>${LAYER_LABELS[g]}
     </div>`;
  }).join('');
  el.querySelectorAll('.legend-item[data-group]').forEach(item => {
    item.addEventListener('click', () => {
      const g = item.getAttribute('data-group');
      toggleLayerExcluded(g);
      item.className = 'legend-item ' + legendLayerClass(g);
      applyNodeFilter();
      syncExcludedToURL();
      if (typeof refreshNodePickerCheckboxes === 'function') refreshNodePickerCheckboxes(); // Task 7
    });
  });
}

// A layer is "off" when every one of its nodes is excluded, "partial" when
// some (but not all) are, and unstyled (full opacity) when none are.
function legendLayerClass(group) {
  const layerNodeIds = NODES.filter(n => n.group === group).map(n => n.id);
  const excludedCount = layerNodeIds.filter(id => excludedNodes.has(id)).length;
  if (excludedCount === 0) return '';
  if (excludedCount === layerNodeIds.length) return 'off';
  return 'partial';
}

// Bulk-toggle: if the layer is currently fully or partially visible, hide
// every node in it; if it's fully hidden, show every node in it. (A partial
// layer's click always goes to "hide the rest", not "show the rest" -- one
// click, one predictable direction, no separate three-state cycle to learn.)
function toggleLayerExcluded(group) {
  const layerNodeIds = NODES.filter(n => n.group === group).map(n => n.id);
  const allExcluded = layerNodeIds.every(id => excludedNodes.has(id));
  if (allExcluded) {
    layerNodeIds.forEach(id => excludedNodes.delete(id));
  } else {
    layerNodeIds.forEach(id => excludedNodes.add(id));
  }
}

function applyNodeFilter() {
  Renderer.setNodeFilter(excludedNodes);
}

// Re-reads excludedNodes into the already-built legend DOM -- called by
// Task 7's picker after a single-node change, so the legend's off/partial
// styling stays correct without a full rebuild.
function refreshLegendClasses() {
  document.querySelectorAll('.legend-item[data-group]').forEach(item => {
    const g = item.getAttribute('data-group');
    item.className = 'legend-item ' + legendLayerClass(g);
  });
}
```

(The `typeof refreshNodePickerCheckboxes === 'function'` guard exists because this task runs before Task 7 creates that function — it becomes a real call once Task 7 lands, with zero further edits needed here.)

- [ ] **Step 3: Update the boot sequence's call from `applyLayerFilter()` to `applyNodeFilter()`**

Run: `grep -n "applyLayerFilter()" bullion-live-map/bullion_mkultra.html` to find any call sites beyond the definition itself, and rename them to `applyNodeFilter()`.

- [ ] **Step 4: Browser-verify layer toggle behavior**

Via `headless-chrome-verification`:
1. Click a layer with all nodes visible — confirm every node in that layer disappears, the legend item gets `.off`, and the URL's `?hide=` now lists exactly that layer's node ids.
2. Individually re-show one node from that layer via DevTools-protocol eval (simulating what Task 7's picker will do: `excludedNodes.delete('cpi'); applyNodeFilter(); syncExcludedToURL();`) — confirm the legend item's class becomes `partial`.
3. Click the same (now-partial) legend item again — confirm it goes fully `off` (hides the rest), not back to fully visible.

- [ ] **Step 5: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: legend layer toggle bulk-edits excludedNodes with partial-state styling"
```

---

### Task 7: Per-node picker drawer

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` — new drawer HTML near line 917 (after the existing glossary drawer), new JS near the Task 6 legend functions.

**Interfaces:**
- Consumes: `excludedNodes`, `applyNodeFilter()`, `syncExcludedToURL()`, `legendLayerClass()`, `refreshLegendClasses()` (Task 5/6), `NODES`, `LAYER_ORDER`, `LAYER_LABELS`, `GROUP_COLOR` (existing).
- Produces: `buildNodePicker()` — call once at boot, right after `buildLegend()`. `refreshNodePickerCheckboxes()` — called by Task 6's legend click handler so both UIs stay in sync. `toggleNodeExcluded(id)`.

- [ ] **Step 1: Add the drawer markup**

Immediately after the existing glossary drawer block (after line 917's closing `</div>`), add:

```html
    <div>
      <div class="drawer-label">Customize your map <span class="drawer-tag" id="node-picker-toggle">show</span></div>
      <div class="glossary-view hidden" id="node-picker-box"></div>
    </div>
```

- [ ] **Step 2: Add the drawer's CSS**

Near the existing `.legend-item` rules, add styling for the picker's per-node rows (reuses the `.legend-item`/`.legend-dot` look for visual consistency):

```css
  .node-picker-layer-title { font-weight:600; margin:10px 0 4px; color:var(--text-dim); font-size:12px; }
  .node-picker-layer-title:first-child { margin-top:0; }
  .node-picker-row { display:flex; align-items:center; gap:6px; padding:2px 0; cursor:pointer; }
  .node-picker-row input { cursor:pointer; }
```

- [ ] **Step 3: Implement `buildNodePicker`, `refreshNodePickerCheckboxes`, `toggleNodeExcluded`, and the drawer's own toggle function**

Add near the Task 6 legend functions:

```javascript
function buildNodePicker() {
  const box = document.getElementById('node-picker-box');
  box.innerHTML = LAYER_ORDER.map(g => {
    const layerNodes = NODES.filter(n => n.group === g);
    if (layerNodes.length === 0) return '';
    const rows = layerNodes.map(n => `
      <label class="node-picker-row" data-node-row="${n.id}">
        <input type="checkbox" data-node-id="${n.id}" ${excludedNodes.has(n.id) ? '' : 'checked'}>
        <span class="legend-dot" style="background:${GROUP_COLOR[g]}"></span>${n.label}
      </label>`).join('');
    return `<div class="node-picker-layer-title">${LAYER_LABELS[g]}</div>${rows}`;
  }).join('');
  box.querySelectorAll('input[data-node-id]').forEach(cb => {
    cb.addEventListener('change', () => {
      toggleNodeExcluded(cb.getAttribute('data-node-id'));
    });
  });
}

function toggleNodeExcluded(id) {
  if (excludedNodes.has(id)) excludedNodes.delete(id); else excludedNodes.add(id);
  applyNodeFilter();
  syncExcludedToURL();
  refreshLegendClasses();
}

// Re-reads excludedNodes into the already-built checkbox DOM (cheaper than a
// full buildNodePicker() rebuild) -- called whenever the legend's bulk layer
// toggle changes excludedNodes out from under this drawer.
function refreshNodePickerCheckboxes() {
  const box = document.getElementById('node-picker-box');
  if (!box) return;
  box.querySelectorAll('input[data-node-id]').forEach(cb => {
    cb.checked = !excludedNodes.has(cb.getAttribute('data-node-id'));
  });
}

function toggleNodePickerDrawer() {
  const box = document.getElementById('node-picker-box');
  const btn = document.getElementById('node-picker-toggle');
  box.classList.toggle('hidden');
  btn.textContent = box.classList.contains('hidden') ? 'show' : 'hide';
}
document.getElementById('node-picker-toggle').addEventListener('click', toggleNodePickerDrawer);
```

- [ ] **Step 4: Call `buildNodePicker()` at boot**

At the same boot-sequence location as Task 5 Step 3, add `buildNodePicker();` immediately after `buildLegend();`.

- [ ] **Step 5: Browser-verify the picker drawer**

Via `headless-chrome-verification`:
1. Open the drawer, uncheck one node's checkbox — confirm that node disappears from the map, the URL updates, and the node's layer's legend item becomes `.partial`.
2. Click that layer's legend item to bulk-hide the rest — confirm the drawer's remaining checkboxes for that layer become unchecked too (via `refreshNodePickerCheckboxes`, now actually wired since this task exists).
3. Re-check a box — confirm the node reappears and the legend item updates accordingly.

- [ ] **Step 6: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: add per-node picker drawer, kept in sync with the legend"
```

---

### Task 8: Empty-state message, final whole-feature verification, frozen-file check

**Files:**
- Modify: `bullion-live-map/bullion_mkultra.html` — small addition to `applyNodeFilter()` (Task 6) for the empty-state message; no other product changes.

**Interfaces:**
- Consumes: everything from Tasks 1-7.
- Produces: nothing new — this task is verification plus one small UX guard.

- [ ] **Step 1: Add the empty-state message element**

In the HTML, near `<div id="legend-box"></div>` (same area touched in Task 5), add:

```html
<div id="all-hidden-message" class="hidden sim-note" style="margin-top:8px">Nothing to show — try clearing some hidden layers.</div>
```

- [ ] **Step 2: Show/hide it from `applyNodeFilter()`**

In `applyNodeFilter()` (Task 6), add after the `Renderer.setNodeFilter(excludedNodes);` line:

```javascript
  const msg = document.getElementById('all-hidden-message');
  if (msg) msg.classList.toggle('hidden', excludedNodes.size < NODES.length);
```

- [ ] **Step 3: Browser-verify the empty state**

Via `headless-chrome-verification`: use the node picker to uncheck every single node (or click every legend layer to `.off`) — confirm the message appears, and confirm re-checking any one node hides the message again.

- [ ] **Step 4: Run the full spec Testing checklist end-to-end**

Using `headless-chrome-verification`, walk through all 8 scenarios from the spec's Testing section as one continuous pass (most were already verified per-task above; this step is the integration re-check with everything landed together, not new logic):
1. Layer toggle bulk-hides + URL updates.
2. Single node toggle inside a layer produces partial state.
3. Degree-≤3 node hide produces correct dashed connectors with correct via-labels, skipping pairs with a real direct link.
4. Hub node hide drops links, no synthesis.
5. `?hide=` link with one stale + one valid id loads correctly.
6. Hiding `credit` changes the score's `fieldsMissing`/tier; hiding `geo` does not change the score.
7. Copy Link round-trips into a fresh tab with identical visible state.
8. Hiding all nodes shows the empty-state message.

- [ ] **Step 5: Run the full Python test suite**

Run: `cd bullion-live-map && python3 -m unittest discover -s tests -v`
Expected: all green.

- [ ] **Step 6: Frozen-file check**

Run: `cd bullion-live-map && sha256sum bullion_mk11.html bullion_mk12.html bullion_mk13.html bullion_mk14.html bullion_mk15.html bullion_mk16.html bullion_mk17.html bullion_mk18.html`

Compare against a checksum taken before this plan's first commit (capture one now if not already recorded) — expected: byte-identical, since no task in this plan touches these files.

- [ ] **Step 7: Commit**

```bash
git add bullion-live-map/bullion_mkultra.html
git commit -m "Mk Ultra: empty-state message when every node is hidden"
```
