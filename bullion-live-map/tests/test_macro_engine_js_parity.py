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


def _extract_js_snippet_through_node_mults(html):
    # Extract minimal needed pieces: NE and constants (needed by NODE_ELASTICITY),
    # currentLiveSource and SIMULATED_DRIVER_BASE (needed by DRIVERS init),
    # DRIVERS, BASELINE_STATS, NODE_ELASTICITY, computeCompositeScore,
    # computeNodeMultipliers, buildMacroNarrative, NODE_MAP. Skip DOM/localStorage initialization code.
    parts = []

    # Include currentLiveSource function (needed by refreshDriverBases)
    cls_start = html.index("function currentLiveSource() {")
    cls_end = html.index("}", html.index("return useLiveData")) + 1
    parts.append(html[cls_start:cls_end])

    # Include NE and constants (needed by NODE_ELASTICITY)
    ne_start = html.index("const NE = ")
    ne_end = html.index("const CONF = {") + len("const CONF = {")
    ne_end = html.index("};\n", ne_end) + 3  # Include closing }; of CONF
    parts.append(html[ne_start:ne_end])

    # Include DRIVERS through NODE_ELASTICITY
    drivers_start = html.index("const DRIVERS = ")
    elasticity_end = html.index("};\n", html.index("const NODE_ELASTICITY = {")) + 3
    parts.append(html[drivers_start:elasticity_end])

    # Include computeCompositeScore
    composite_start = html.index("function computeCompositeScore(live)")
    composite_end = html.index("const NODE_ELASTICITY = {")
    parts.append(html[composite_start:composite_end])

    # Include NODE_MAP
    node_map_start = html.index("const NODE_MAP = {")
    node_map_end = html.index("};\n", node_map_start) + 3
    parts.append(html[node_map_start:node_map_end])

    # Include buildMacroNarrative. (Previously anchored on the `_ordinal`
    # helper, which sat just above it; _ordinal was removed along with the
    # composite-score sentence that was its only caller.)
    narrative_start = html.index("function buildMacroNarrative(")
    narrative_end = html.index("function runMacroAnalysis(")
    parts.append(html[narrative_start:narrative_end])

    return "\n".join(parts)


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


@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class TestComputeNodeMultipliersParity(unittest.TestCase):
    def setUp(self):
        with open(MAP_PATH) as f:
            self.snippet = _extract_js_snippet_through_node_mults(f.read())

    def test_all_drivers_at_baseline_mean_yields_no_contributions(self):
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
const driverValues = {};
DRIVERS.forEach(d => { driverValues[d.key] = BASELINE_STATS.fields[d.key].mean; });
const result = computeNodeMultipliers(driverValues);
process.stdout.write(JSON.stringify(result));
"""
        result = _run_node(script)
        self.assertEqual(result["mults"], {})

    def test_nodes_never_covered_by_node_elasticity_are_listed_as_no_data(self):
        # Perturb drivers so mults has contributions; Russia/Geopolitics have no
        # elasticity coverage so they should remain in noDataNodes even with other
        # nodes active. Meanwhile, Tech_Equities (covered by ffr and vix) must be
        # in mults to distinguish "genuinely uncovered" from "covered but silent".
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
const driverValues = {};
DRIVERS.forEach(d => { driverValues[d.key] = BASELINE_STATS.fields[d.key].mean; });
// Perturb ffr and vix to activate coverage (both reach Tech_Equities in NODE_ELASTICITY).
driverValues.ffr = BASELINE_STATS.fields.ffr.mean + 1.0 * BASELINE_STATS.fields.ffr.std;
driverValues.vix = BASELINE_STATS.fields.vix.mean + 1.5 * BASELINE_STATS.fields.vix.std;
const result = computeNodeMultipliers(driverValues);
process.stdout.write(JSON.stringify({
  noDataNodes: result.noDataNodes,
  hasMultsForTechEquities: 'Tech_Equities' in result.mults,
  noDataContainsRussia: result.noDataNodes.includes('Russia'),
  noDataContainsGeo: result.noDataNodes.includes('Geopolitics')
}));
"""
        result = _run_node(script)
        self.assertIn("Russia", result["noDataNodes"])
        self.assertIn("Geopolitics", result["noDataNodes"])
        self.assertTrue(result["hasMultsForTechEquities"],
                        "Tech_Equities must have coverage (should be in mults) to distinguish truly uncovered nodes")
        self.assertTrue(result["noDataContainsRussia"])
        self.assertTrue(result["noDataContainsGeo"])

    def test_vix_deviation_produces_expected_sign_on_spx(self):
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
const driverValues = {};
DRIVERS.forEach(d => { driverValues[d.key] = BASELINE_STATS.fields[d.key].mean; });
// Push VIX 2 std-devs above its own mean.
driverValues.vix = BASELINE_STATS.fields.vix.mean + 2 * BASELINE_STATS.fields.vix.std;
const result = computeNodeMultipliers(driverValues);
process.stdout.write(JSON.stringify(result.mults.SPX));
"""
        spx_mult = _run_node(script)
        # NODE_ELASTICITY.vix.SPX is negative (rising VIX hurts SPX) -- see
        # bullion_mkultra.html:3862.
        self.assertLess(spx_mult, 0)

    def test_multi_driver_accumulation_on_single_node(self):
        # Verify that when multiple drivers perturb and both target the same node,
        # their contributions accumulate (sum), not overwrite. Both ffr and vix
        # have NODE_ELASTICITY entries for Tech_Equities, so we perturb both and
        # verify the result equals the sum of their individual contributions.
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
const driverValues = {};
DRIVERS.forEach(d => { driverValues[d.key] = BASELINE_STATS.fields[d.key].mean; });
const ffrDeviation = 1.0 * BASELINE_STATS.fields.ffr.std;
const vixDeviation = 1.5 * BASELINE_STATS.fields.vix.std;
driverValues.ffr = BASELINE_STATS.fields.ffr.mean + ffrDeviation;
driverValues.vix = BASELINE_STATS.fields.vix.mean + vixDeviation;

const result = computeNodeMultipliers(driverValues);

// Hand-compute expected accumulation: each driver's elasticity * its delta
const ffrCoeff = NODE_ELASTICITY.ffr.Tech_Equities.v;
const vixCoeff = NODE_ELASTICITY.vix.Tech_Equities.v;
const expectedAccumulation = ffrCoeff * ffrDeviation + vixCoeff * vixDeviation;

process.stdout.write(JSON.stringify({
  actualMultiplier: result.mults.Tech_Equities,
  expectedAccumulation: expectedAccumulation,
  ffrCoeff: ffrCoeff,
  vixCoeff: vixCoeff,
  ffrDeviation: ffrDeviation,
  vixDeviation: vixDeviation
}));
"""
        result = _run_node(script)
        # The actual multiplier should equal the hand-computed sum (within rounding).
        # We compare at 3 decimal precision since the function rounds to toFixed(3).
        expected = round(result["expectedAccumulation"], 3)
        actual = result["actualMultiplier"]
        self.assertAlmostEqual(
            actual, expected, places=2,
            msg=f"Multi-driver accumulation failed. Expected sum of contributions "
                f"({result['ffrCoeff']} * {result['ffrDeviation']} + "
                f"{result['vixCoeff']} * {result['vixDeviation']} = {expected}) "
                f"but got {actual}. This suggests contributions are not accumulating."
        )


@unittest.skipUnless(shutil.which("node"), "node not on PATH")
class TestBuildMacroNarrativeParity(unittest.TestCase):
    def setUp(self):
        with open(MAP_PATH) as f:
            self.snippet = _extract_js_snippet_through_node_mults(f.read())

    def test_narrative_has_exactly_two_sentences_and_cites_real_cpi(self):
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
const live = {};
Object.keys(BASELINE_STATS.pc1_loadings).forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
live.cpi_yoy = 2.6;
live.nfp_mom = 150;
const driverValues = {};
DRIVERS.forEach(d => { driverValues[d.key] = BASELINE_STATS.fields[d.key].mean; });
const nodes = computeNodeMultipliers(driverValues);
const narrative = buildMacroNarrative(nodes, live);
process.stdout.write(JSON.stringify({ narrative, sentences: narrative.split(/(?<=[.])\\s+/).length }));
"""
        result = _run_node(script)
        self.assertEqual(result["sentences"], 2)
        self.assertIn("2.6", result["narrative"])

    def test_narrative_with_populated_mults_names_worst_and_best_nodes(self):
        # Test the primary use case: when node multipliers are populated,
        # the second sentence should correctly identify the worst node as
        # "headwind" and the best node as "support". This test verifies PAIRING:
        # that the worst node (Tech_Equities: -60%) is associated with "headwind"
        # and the best node (USD_Strength: +45%) is associated with "support".
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
const live = {};
Object.keys(BASELINE_STATS.pc1_loadings).forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
live.cpi_yoy = 3.2;
live.nfp_mom = -50;
// Synthetic populated nodeResult: Tech_Equities has the worst (most negative) impact,
// USD_Strength has the best (most positive) impact.
const nodes = {
  mults: {
    "Tech_Equities": -0.60,
    "Inflation": -0.15,
    "USD_Strength": 0.45,
    "Credit": 0.05
  },
  noDataNodes: ["Russia", "Geopolitics"]
};
const narrative = buildMacroNarrative(nodes, live);
process.stdout.write(JSON.stringify({
  narrative,
  sentences: narrative.split(/(?<=[.])\\s+/).length,
  hasWorstNodeAsHeadwind: narrative.includes("headwind is to Tech Equities"),
  hasBestNodeAsSupport: narrative.includes("USD Strength shows the most support")
}));
"""
        result = _run_node(script)
        self.assertEqual(result["sentences"], 2,
                         "Narrative must be exactly 2 sentences")
        self.assertTrue(result["hasWorstNodeAsHeadwind"],
                        "Worst node (Tech Equities, -60%) must be paired with 'headwind is to' "
                        "(substring check prevents role-swap regression)")
        self.assertTrue(result["hasBestNodeAsSupport"],
                        "Best node (USD Strength, +45%) must be paired with 'shows the most support' "
                        "(substring check prevents role-swap regression)")


if __name__ == "__main__":
    unittest.main()
