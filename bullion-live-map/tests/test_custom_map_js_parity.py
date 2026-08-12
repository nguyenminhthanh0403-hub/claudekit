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


if __name__ == "__main__":
    unittest.main()
