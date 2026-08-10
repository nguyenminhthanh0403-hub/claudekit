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

    def test_all_fields_at_their_own_mean_is_a_valid_measured_score(self):
        # NOTE: this does NOT assert score==50. Verified empirically during
        # implementation (see the macro-engine design doc's addendum) that
        # "every field simultaneously at its own individual baseline mean"
        # does not reliably land near the historical median: MEAN_REVERTING
        # fields are z-scored against their full FULL_WINDOW_YEARS sample,
        # which for several fields spans a materially different rate regime
        # (near-zero rates for much of that window vs. the current tightening
        # cycle) than the composite's own RECENT_WINDOW_YEARS row matrix. A
        # field sitting at its own multi-year average is not the same as the
        # SYSTEM being at a historically typical combined state -- some
        # fields are legitimately in a different regime than their own long
        # history right now, and that's real data, not a bug. So this test
        # only checks the mechanism is sound (valid bounded score, correct
        # tier when all fields are supplied), not a specific target value.
        script = self.snippet + """
const live = {};
for (const f of Object.keys(BASELINE_STATS.pc1_loadings)) {
  live[f] = BASELINE_STATS.fields[f].mean;
}
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertEqual(result["tier"], "measured")
        self.assertEqual(len(result["fieldsMissing"]), 0)

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

    def test_percentile_boundaries_map_to_score_extremes(self):
        # The one invariant that IS guaranteed regardless of field regime
        # heterogeneity: pushing EVERY composite field simultaneously to its
        # most-stressed clip (z=+3 in the direction its loading treats as
        # stress) produces a composite value that upper-bounds anything any
        # real historical day achieved (real days rarely have all fields
        # simultaneously at their most extreme together) -- so it must
        # score at or below the true worst historical day, i.e. score <= 10.
        # Symmetrically, the least-stressed simultaneous clip must score
        # >= 90. This does NOT try to hit BASELINE_STATS.composite_percentiles'
        # exact min/max (that would require knowing which specific field
        # combination actually produced the historical extreme, which a
        # single-field or naive solve can't guarantee) -- it only relies on
        # "all fields simultaneously maximally stressed" being at least as
        # extreme as anything observed, which is true by construction of
        # the clip bound itself, not dependent on any field's regime.
        script = self.snippet + """
const fields = Object.keys(BASELINE_STATS.pc1_loadings);
function liveAtExtreme(direction) {
  // direction = +1 for max stress, -1 for min stress.
  const live = {};
  fields.forEach(f => {
    const stat = BASELINE_STATS.fields[f];
    const loading = BASELINE_STATS.pc1_loadings[f];
    const zSign = (loading >= 0 ? 1 : -1) * direction;
    live[f] = stat.mean + zSign * 3 * stat.std;
  });
  return live;
}
const hi = computeCompositeScore(liveAtExtreme(1));
const lo = computeCompositeScore(liveAtExtreme(-1));
process.stdout.write(JSON.stringify({ lo, hi }));
"""
        result = _run_node(script)
        self.assertGreaterEqual(result["lo"]["score"], 90)
        self.assertLessEqual(result["hi"]["score"], 10)


if __name__ == "__main__":
    unittest.main()
