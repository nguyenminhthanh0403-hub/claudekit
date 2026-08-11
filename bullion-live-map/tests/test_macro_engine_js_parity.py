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

    def _synthetic_baseline_prelude(self):
        # The live BASELINE_STATS block spliced into bullion_mkultra.html
        # won't have stress_sign/category until Task 7 regenerates it, so
        # these tests inject a synthetic BASELINE_STATS-shaped object with
        # exactly the 7 composite fields, matching backfill_baseline.py's
        # EXPECTED_STRESS_SIGN/COMPOSITE_CATEGORY values.
        return """
BASELINE_STATS.stress_sign = {hy_oas:1, ig_oas:1, vix:1, spx:-1, fed_bs:-1, rrp:-1, curve_slope:-1};
BASELINE_STATS.category = {hy_oas:'Credit', ig_oas:'Credit', vix:'Volatility', spx:'Equity valuation', fed_bs:'Funding', rrp:'Funding', curve_slope:'Safe assets'};
"""

    def test_all_fields_at_their_own_mean_scores_near_neutral(self):
        # Unlike the old PCA version, every field independently sign-aligned
        # and z-scored against its own mean has no cross-field regime
        # heterogeneity concern -- "every field at its own baseline mean"
        # IS the neutral point by construction, so this can assert a
        # specific target (unlike the old test, which explicitly could not).
        script = self.snippet + self._synthetic_baseline_prelude() + """
const live = {};
for (const f of Object.keys(BASELINE_STATS.stress_sign)) {
  live[f] = BASELINE_STATS.fields[f].mean;
}
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertAlmostEqual(result["score"], 50, delta=1)
        self.assertEqual(result["tier"], "measured")
        self.assertEqual(len(result["fieldsMissing"]), 0)

    def test_missing_fields_degrade_tier_to_directional(self):
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
// Only supply 2 of the 7 composite fields -- well under the 6-of-7 bar.
live[fields[0]] = BASELINE_STATS.fields[fields[0]].mean;
live[fields[1]] = BASELINE_STATS.fields[fields[1]].mean;
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertEqual(result["tier"], "directional")

    def test_all_fields_at_max_stress_clip_scores_near_zero(self):
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
fields.forEach(f => {
  const stat = BASELINE_STATS.fields[f];
  const sign = BASELINE_STATS.stress_sign[f];
  // Push every field 3 std-devs in ITS OWN stress direction.
  live[f] = stat.mean + sign * 3 * stat.std;
});
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertLessEqual(result["score"], 5)

    def test_all_fields_at_min_stress_clip_scores_near_hundred(self):
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign);
const live = {};
fields.forEach(f => {
  const stat = BASELINE_STATS.fields[f];
  const sign = BASELINE_STATS.stress_sign[f];
  live[f] = stat.mean - sign * 3 * stat.std;
});
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertGreaterEqual(result["score"], 95)

    def test_category_with_zero_present_fields_is_skipped_not_zeroed(self):
        # Volatility's only member is vix. Omitting vix from `live` entirely
        # must drop Volatility from the average, not silently treat it as a
        # neutral (z=0) contributor -- a neutral synthetic vote would still
        # subtly pull the score, which is exactly the kind of unstated
        # imputation this fix's category-weighting was designed to avoid.
        script = self.snippet + self._synthetic_baseline_prelude() + """
const fields = Object.keys(BASELINE_STATS.stress_sign).filter(f => f !== 'vix');
const live = {};
fields.forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertNotIn("Volatility", result["categoryContributions"])
        self.assertAlmostEqual(result["score"], 50, delta=1)

    def test_synthetic_crisis_scores_low_not_high(self):
        # THE regression test for the original bug. VIX 45, HY spreads to
        # 8%, SPX -35% from mean must NOT score "Healthy" -- this exact
        # scenario scored 100/"Healthy" under the old PCA version. Verified
        # by hand during plan-writing (executed against this project's real
        # BASELINE_STATS.fields values, not just reasoned about): this
        # scenario now scores 6/"Elevated stress" under the new formula.
        script = self.snippet + self._synthetic_baseline_prelude() + """
const live = {
  hy_oas: 8.0,
  ig_oas: BASELINE_STATS.fields.ig_oas.mean + 3 * BASELINE_STATS.fields.ig_oas.std,
  vix: 45,
  spx: BASELINE_STATS.fields.spx.mean * 0.65,
  fed_bs: BASELINE_STATS.fields.fed_bs.mean - 2 * BASELINE_STATS.fields.fed_bs.std,
  rrp: BASELINE_STATS.fields.rrp.mean - 2 * BASELINE_STATS.fields.rrp.std,
  curve_slope: -1.0,
};
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertLess(result["score"], 45,
            "Synthetic crisis (VIX 45, HY 8%, SPX -35%) must score below the "
            "'Moderate stress' threshold -- scoring 'Healthy' here is exactly "
            "the bug this fix exists to close.")

    def test_calm_baseline_scores_healthy_not_stressed(self):
        # The counterpart regression case: the actual calm market day that
        # scored 18/"Elevated stress" under the old PCA version must now
        # land in "Healthy" (score > 70) -- never inverted. Every field
        # nudged 1.5 std toward calm (verified by hand against this
        # project's real BASELINE_STATS.fields values during plan-writing:
        # this exact nudge produces score=75, comfortably inside "Healthy"
        # with real, not cherry-picked, margin).
        script = self.snippet + self._synthetic_baseline_prelude() + """
const live = {};
Object.keys(BASELINE_STATS.stress_sign).forEach(f => {
  const stat = BASELINE_STATS.fields[f];
  const sign = BASELINE_STATS.stress_sign[f];
  live[f] = stat.mean - sign * 1.5 * stat.std;
});
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertGreater(result["score"], 70,
            "A day with every field nudged 1.5 std toward calm must score "
            "'Healthy' (>70) -- this is the inverse of the original bug's "
            "failure mode (a calm day scoring 18/'Elevated stress').")

    def test_leading_category_is_largest_positive_not_largest_magnitude(self):
        # Regression test for the final-review finding: leadingCategory used
        # to be picked by Math.abs(v), which could name a strongly CALMING
        # category (large negative contribution) as what's "driving" stress.
        # Here spx (Equity valuation, sign -1) is pushed 3 std toward calm --
        # a huge negative contribution (-3) that dwarfs everything else in
        # magnitude -- while hy_oas (Credit, sign +1) gets only a mild 0.3
        # std stress nudge (+0.3). Every other field sits at its own mean
        # (contributes 0). Credit is the only category with a POSITIVE
        # contribution, so it must be picked -- never Equity valuation,
        # despite its larger magnitude.
        script = self.snippet + self._synthetic_baseline_prelude() + """
const live = {};
Object.keys(BASELINE_STATS.stress_sign).forEach(f => {
  live[f] = BASELINE_STATS.fields[f].mean;
});
live.spx = BASELINE_STATS.fields.spx.mean + 3 * BASELINE_STATS.fields.spx.std;
live.hy_oas = BASELINE_STATS.fields.hy_oas.mean + 0.3 * BASELINE_STATS.fields.hy_oas.std;
process.stdout.write(JSON.stringify(computeCompositeScore(live)));
"""
        result = _run_node(script)
        self.assertEqual(result["leadingCategory"], "Credit",
            "leadingCategory must be the category with the largest POSITIVE "
            "contribution (Credit, +0.3ish), not the largest-magnitude one "
            "(Equity valuation, -3 -- strongly calming, not stressing).")


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

    def test_narrative_has_exactly_three_sentences_and_cites_real_cpi_and_score(self):
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
BASELINE_STATS.stress_sign = {hy_oas:1, ig_oas:1, vix:1, spx:-1, fed_bs:-1, rrp:-1, curve_slope:-1};
BASELINE_STATS.category = {hy_oas:'Credit', ig_oas:'Credit', vix:'Volatility', spx:'Equity valuation', fed_bs:'Funding', rrp:'Funding', curve_slope:'Safe assets'};
const live = {};
Object.keys(BASELINE_STATS.stress_sign).forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
live.cpi_yoy = 2.6;
live.nfp_mom = 150;
const composite = computeCompositeScore(live);
const driverValues = {};
DRIVERS.forEach(d => { driverValues[d.key] = BASELINE_STATS.fields[d.key].mean; });
const nodes = computeNodeMultipliers(driverValues);
const narrative = buildMacroNarrative(composite, nodes, live);
process.stdout.write(JSON.stringify({ narrative, sentences: narrative.split(/(?<=[.])\\s+/).length, score: composite.score }));
"""
        result = _run_node(script)
        self.assertEqual(result["sentences"], 3)
        self.assertIn("2.6", result["narrative"])
        self.assertIn(str(result["score"]), result["narrative"])

    def test_narrative_with_populated_mults_names_worst_and_best_nodes(self):
        script = """
let selectedHistoryDate = null, useLiveData = false;
""" + self.snippet + """
BASELINE_STATS.stress_sign = {hy_oas:1, ig_oas:1, vix:1, spx:-1, fed_bs:-1, rrp:-1, curve_slope:-1};
BASELINE_STATS.category = {hy_oas:'Credit', ig_oas:'Credit', vix:'Volatility', spx:'Equity valuation', fed_bs:'Funding', rrp:'Funding', curve_slope:'Safe assets'};
const live = {};
Object.keys(BASELINE_STATS.stress_sign).forEach(f => { live[f] = BASELINE_STATS.fields[f].mean; });
live.cpi_yoy = 3.2;
live.nfp_mom = -50;
const composite = computeCompositeScore(live);
const nodes = {
  mults: {
    "Tech_Equities": -0.60,
    "Inflation": -0.15,
    "USD_Strength": 0.45,
    "Credit": 0.05
  },
  noDataNodes: ["Russia", "Geopolitics"]
};
const narrative = buildMacroNarrative(composite, nodes, live);
process.stdout.write(JSON.stringify({
  narrative,
  sentences: narrative.split(/(?<=[.])\\s+/).length,
  hasWorstNodeAsHeadwind: narrative.includes("headwind is to Tech Equities"),
  hasBestNodeAsSupport: narrative.includes("USD Strength shows the most support")
}));
"""
        result = _run_node(script)
        self.assertEqual(result["sentences"], 3,
                         "Narrative must be exactly 3 sentences")
        self.assertTrue(result["hasWorstNodeAsHeadwind"],
                        "Worst node (Tech Equities, -60%) must be paired with 'headwind is to' "
                        "(substring check prevents role-swap regression)")
        self.assertTrue(result["hasBestNodeAsSupport"],
                        "Best node (USD Strength, +45%) must be paired with 'shows the most support' "
                        "(substring check prevents role-swap regression)")


if __name__ == "__main__":
    unittest.main()
