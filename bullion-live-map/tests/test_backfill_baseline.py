import os
import statistics
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backfill_baseline import (
    field_stats, forward_fill, fetch_all_history,
    add_curve_slope, build_zscore_rows, pca_first_component,
    orient_loadings, percentile_table,
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


class TestZscoreRows(unittest.TestCase):
    def test_only_dates_with_all_fields_present_are_kept(self):
        history = {"a": {"d1": 1.0, "d2": 2.0}, "b": {"d1": 10.0}}
        stats = {"a": {"mean": 1.5, "std": 0.5}, "b": {"mean": 10.0, "std": 1.0}}
        dates, rows = build_zscore_rows(history, stats, ["a", "b"])
        self.assertEqual(dates, ["d1"])
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][0], (1.0 - 1.5) / 0.5)
        self.assertAlmostEqual(rows[0][1], (10.0 - 10.0) / 1.0)


class TestPCA(unittest.TestCase):
    def test_recovers_dominant_direction_of_perfectly_correlated_fields(self):
        # Two fields that move in lockstep should load ~equally onto PC1.
        rows = [[x, x] for x in [-2.0, -1.0, 0.0, 1.0, 2.0]]
        loadings = pca_first_component(rows, n_iter=200, seed=1)
        self.assertAlmostEqual(abs(loadings[0]), abs(loadings[1]), places=3)
        self.assertAlmostEqual(loadings[0] * loadings[1], abs(loadings[0]) * abs(loadings[1]), places=3)

    def test_orient_loadings_flips_sign_so_anchor_is_positive(self):
        loadings = [-0.7, 0.7]
        oriented = orient_loadings(loadings, ["vix", "other"], anchor_field="vix")
        self.assertGreater(oriented[0], 0)
        self.assertLess(oriented[1], 0)

    def test_orient_loadings_noop_when_anchor_already_positive(self):
        loadings = [0.7, -0.7]
        oriented = orient_loadings(loadings, ["vix", "other"], anchor_field="vix")
        self.assertEqual(oriented, loadings)


class TestPercentileTable(unittest.TestCase):
    def test_table_is_monotonic_nondecreasing_and_spans_min_max(self):
        values = list(range(1000))
        table = percentile_table([float(v) for v in values], n_points=101)
        self.assertEqual(len(table), 101)
        self.assertEqual(table[0], 0.0)
        self.assertEqual(table[-1], 999.0)
        for i in range(1, len(table)):
            self.assertGreaterEqual(table[i], table[i - 1])


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
        self.assertIn("pc1_loadings", baseline)
        self.assertEqual(set(baseline["pc1_loadings"].keys()),
                          {"hy_oas", "ig_oas", "sofr", "tbill_3m", "us10y", "us2y",
                           "curve_slope", "vix", "spx", "fed_bs", "rrp"})
        self.assertEqual(len(baseline["composite_percentiles"]), 101)
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
                    "pc1_loadings": {"vix": 1.0}, "composite_percentiles": [0.0, 1.0]}
        block = render_js_block(baseline)
        self.assertTrue(block.strip().startswith("const BASELINE_STATS ="))
        inner = block.strip()[len("const BASELINE_STATS ="):].rstrip(";").strip()
        self.assertEqual(json.loads(inner), baseline)


if __name__ == "__main__":
    unittest.main()
