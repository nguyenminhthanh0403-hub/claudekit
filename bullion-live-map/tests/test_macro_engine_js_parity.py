"""JS<->Python parity guard for the Mk Ultra macro engine's pure functions.

Mirrors test_chain_reaction_js_parity.py: extracts the real shipped JS
(BASELINE_STATS + the 3 macro-engine functions) out of bullion_mkultra.html,
runs it via a real `node` process against synthetic fixtures, and checks the
result matches a hand-computed expectation. Skipped (not failed) if `node`
isn't on PATH.
"""
import json
import os
import shutil
import subprocess
import unittest

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "bullion_mkultra.html")


def _extract_js_snippet(html):
    start = html.index("const BASELINE_STATS = ")
    end = html.index("const NODE_ELASTICITY = ")
    return html[start:end]


def _run_node(script):
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError("node script failed: " + proc.stderr[:2000])
    return json.loads(proc.stdout)


@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class TestComputeCompositeScoreParity(unittest.TestCase):
    def setUp(self):
        with open(MAP_PATH) as f:
            self.snippet = _extract_js_snippet(f.read())

    def test_all_fields_at_their_own_mean_scores_low_stress(self):
        # Feeding every composite field exactly its own baseline mean should
        # produce z-scores of 0 everywhere, i.e. a composite of 0, which is
        # above the historical median (and thus low-stress, low score).
        script = self.snippet + """
const live = {};
for (const f of Object.keys(BASELINE_STATS.pc1_loadings)) {
  live[f] = BASELINE_STATS.fields[f].mean;
}
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        # composite = 0 is at ~98th percentile -> score = 100 - 98 = 2
        self.assertAlmostEqual(result["score"], 2, delta=2)

    def test_missing_fields_degrade_tier_to_directional(self):
        script = self.snippet + """
const fields = Object.keys(BASELINE_STATS.pc1_loadings);
const live = {};
// Only supply 2 of the composite fields -> well under any reasonable
// completeness threshold.
live[fields[0]] = BASELINE_STATS.fields[fields[0]].mean;
live[fields[1]] = BASELINE_STATS.fields[fields[1]].mean;
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertEqual(result["tier"], "directional")


if __name__ == "__main__":
    unittest.main()
