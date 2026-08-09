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


if __name__ == "__main__":
    unittest.main()
