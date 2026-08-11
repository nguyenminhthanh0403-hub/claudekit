import os
import statistics
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backfill_baseline import (
    field_stats, forward_fill, fetch_all_history,
    add_curve_slope, EXPECTED_STRESS_SIGN, COMPOSITE_CATEGORY, COMPOSITE_FIELDS,
)


class TestFieldStats(unittest.TestCase):
    def test_field_stats_matches_hand_computed_mean_and_std(self):
        values = [10.0, 12.0, 14.0, 16.0, 18.0]
        stats = field_stats(values)
        self.assertAlmostEqual(stats["mean"], 14.0)
        self.assertAlmostEqual(stats["std"], statistics.pstdev(values))
        self.assertEqual(stats["n"], 5)

    def test_field_stats_empty_raises(self):
        with self.assertRaises(ValueError):
            field_stats([])


class TestCurveSlope(unittest.TestCase):
    def test_curve_slope_is_us10y_minus_us2y(self):
        history = {"us10y": {"2020-01-01": 4.0, "2020-01-02": 4.5},
                    "us2y": {"2020-01-01": 1.0, "2020-01-02": 2.0}}
        out = add_curve_slope(history)
        self.assertAlmostEqual(out["curve_slope"]["2020-01-01"], 3.0)
        self.assertAlmostEqual(out["curve_slope"]["2020-01-02"], 2.5)


class TestCompositeSignAndCategoryMaps(unittest.TestCase):
    def test_composite_fields_is_the_trimmed_seven(self):
        self.assertEqual(
            set(COMPOSITE_FIELDS),
            {"hy_oas", "ig_oas", "vix", "spx", "fed_bs", "rrp", "curve_slope"},
        )

    def test_stress_sign_covers_exactly_the_composite_fields(self):
        self.assertEqual(set(EXPECTED_STRESS_SIGN.keys()), set(COMPOSITE_FIELDS))
        for f, sign in EXPECTED_STRESS_SIGN.items():
            self.assertIn(sign, (1, -1), f"{f} sign must be +1 or -1, got {sign}")

    def test_stress_sign_values_match_design_spec(self):
        self.assertEqual(EXPECTED_STRESS_SIGN["hy_oas"], 1)
        self.assertEqual(EXPECTED_STRESS_SIGN["ig_oas"], 1)
        self.assertEqual(EXPECTED_STRESS_SIGN["vix"], 1)
        self.assertEqual(EXPECTED_STRESS_SIGN["spx"], -1)
        self.assertEqual(EXPECTED_STRESS_SIGN["fed_bs"], -1)
        self.assertEqual(EXPECTED_STRESS_SIGN["rrp"], -1)
        self.assertEqual(EXPECTED_STRESS_SIGN["curve_slope"], -1)

    def test_category_covers_exactly_the_composite_fields(self):
        self.assertEqual(set(COMPOSITE_CATEGORY.keys()), set(COMPOSITE_FIELDS))

    def test_category_values_match_design_spec(self):
        self.assertEqual(COMPOSITE_CATEGORY["hy_oas"], "Credit")
        self.assertEqual(COMPOSITE_CATEGORY["ig_oas"], "Credit")
        self.assertEqual(COMPOSITE_CATEGORY["vix"], "Volatility")
        self.assertEqual(COMPOSITE_CATEGORY["spx"], "Equity valuation")
        self.assertEqual(COMPOSITE_CATEGORY["fed_bs"], "Funding")
        self.assertEqual(COMPOSITE_CATEGORY["rrp"], "Funding")
        self.assertEqual(COMPOSITE_CATEGORY["curve_slope"], "Safe assets")


import json

from backfill_baseline import build_baseline, render_js_block, splice_into_html


class TestBuildBaseline(unittest.TestCase):
    def _synthetic_history(self):
        # Dates are generated relative to "now" (not hardcoded to 2020-01)
        # because build_baseline's TRENDING_FIELDS path filters to the last
        # RECENT_WINDOW_YEARS using datetime.now(): a fixed 2020 fixture
        # would fall outside that window and field_stats() would raise on
        # an empty list once "now" drifts more than ~2 years past 2020-01.
        from datetime import datetime, timedelta, timezone
        base = datetime.now(timezone.utc)
        dates = [(base - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(27, -1, -1)]
        history = {}
        for i, f in enumerate(["hy_oas", "ig_oas", "sofr", "tbill_3m", "us10y", "us2y",
                                "vix", "spx", "fed_bs", "rrp", "ffr", "cpi_yoy", "dxy", "wti_px"]):
            history[f] = {d: 1.0 + i * 0.1 + 0.01 * n for n, d in enumerate(dates)}
        return history

    def test_build_baseline_produces_expected_keys(self):
        baseline = build_baseline(self._synthetic_history())
        self.assertIn("fields", baseline)
        self.assertIn("curve_slope", baseline["fields"])
        self.assertIn("stress_sign", baseline)
        self.assertEqual(set(baseline["stress_sign"].keys()),
                          {"hy_oas", "ig_oas", "vix", "spx", "fed_bs", "rrp", "curve_slope"})
        self.assertIn("category", baseline)
        self.assertEqual(set(baseline["category"].keys()),
                          {"hy_oas", "ig_oas", "vix", "spx", "fed_bs", "rrp", "curve_slope"})
        self.assertNotIn("pc1_loadings", baseline)
        self.assertNotIn("composite_percentiles", baseline)
        self.assertNotIn("composite_window_years", baseline)
        for f in ("ffr", "cpi_yoy", "dxy", "wti_px"):
            self.assertIn(f, baseline["fields"])


class TestSplice(unittest.TestCase):
    def test_splice_replaces_only_between_markers(self):
        html = (
            "before\n"
            "// ─── BASELINE-STATS-START ───\n"
            "const BASELINE_STATS = { old: true };\n"
            "// ─── BASELINE-STATS-END ───\n"
            "after\n"
        )
        out = splice_into_html(html, "const BASELINE_STATS = { new: true };")
        self.assertIn("before", out)
        self.assertIn("after", out)
        self.assertIn("new: true", out)
        self.assertNotIn("old: true", out)

    def test_splice_raises_if_markers_missing(self):
        with self.assertRaises(ValueError):
            splice_into_html("no markers here", "const BASELINE_STATS = {};")

    def test_render_js_block_is_valid_json_payload(self):
        baseline = {"generated_at": "2026-08-09", "fields": {"vix": {"mean": 18.0, "std": 5.0, "n": 100, "window_years": 15}},
                    "stress_sign": {"vix": 1}, "category": {"vix": "Volatility"}}
        block = render_js_block(baseline)
        self.assertTrue(block.strip().startswith("const BASELINE_STATS ="))
        inner = block.strip()[len("const BASELINE_STATS ="):].rstrip(";").strip()
        self.assertEqual(json.loads(inner), baseline)


if __name__ == "__main__":
    unittest.main()
