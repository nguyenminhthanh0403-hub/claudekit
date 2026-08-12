import os
import statistics
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backfill_baseline import (
    field_stats, forward_fill, fetch_all_history,
    add_curve_slope, EXPECTED_STRESS_SIGN, COMPOSITE_CATEGORY, COMPOSITE_FIELDS,
    EXPECTED_BASELINE_FIELDS, missing_baseline_fields, RECENT_WINDOW_YEARS,
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

    def test_cb_gold_reserves_is_trending_and_forward_filled(self):
        from datetime import datetime, timedelta, timezone
        base = datetime.now(timezone.utc)
        dense_dates = [(base - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(27, -1, -1)]
        history = self._synthetic_history()
        # cb_gold_reserves only reports on every 10th dense date, mirroring
        # its real monthly sparsity against the other fields' daily grid.
        sparse_dates = dense_dates[::10]
        history["cb_gold_reserves"] = {d: 25000.0 for d in sparse_dates}

        baseline = build_baseline(history)

        stats = baseline["fields"]["cb_gold_reserves"]
        self.assertEqual(stats["window_years"], RECENT_WINDOW_YEARS)
        self.assertGreater(stats["n"], len(sparse_dates),
                            "forward-fill should carry cb_gold_reserves onto the dense grid")

    def test_usd_reserve_share_is_trending_and_forward_filled(self):
        from datetime import datetime, timedelta, timezone
        base = datetime.now(timezone.utc)
        dense_dates = [(base - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(27, -1, -1)]
        history = self._synthetic_history()
        # usd_reserve_share only reports on every 10th dense date, mirroring
        # its real quarterly sparsity against the other fields' daily grid.
        sparse_dates = dense_dates[::10]
        history["usd_reserve_share"] = {d: 57.0 for d in sparse_dates}

        baseline = build_baseline(history)

        stats = baseline["fields"]["usd_reserve_share"]
        self.assertEqual(stats["window_years"], RECENT_WINDOW_YEARS)
        self.assertGreater(stats["n"], len(sparse_dates),
                            "forward-fill should carry usd_reserve_share onto the dense grid")


class TestFetchAllHistoryIncludesImfBasket(unittest.TestCase):
    def test_fetch_all_history_calls_the_imf_basket_fetcher(self):
        # FRED_SERIES/YAHOO_SYMBOLS are stubbed to empty so this test makes
        # no real network calls for those loops (a dummy key would otherwise
        # trip real FRED HTTP errors and a real Yahoo fetch for every
        # symbol) -- only the IMF basket wiring is under test here.
        import backfill_baseline as bb_module
        orig_imf = bb_module.fetch_imf_gold_reserves_basket
        orig_cofer = bb_module.fetch_usd_reserve_share
        orig_fred = bb_module.FRED_SERIES
        orig_yahoo = bb_module.YAHOO_SYMBOLS
        called = {}

        def fake(start, end):
            called["args"] = (start, end)
            return (25000.0, "2026-06-30", "2026-06-30", {"2026-06-30": 25000.0})

        bb_module.fetch_imf_gold_reserves_basket = fake
        bb_module.fetch_usd_reserve_share = lambda start, end: (57.1, "2026-03-31", "2026-03-31", {})
        bb_module.FRED_SERIES = {}
        bb_module.YAHOO_SYMBOLS = {}
        try:
            out = bb_module.fetch_all_history("dummy-key", "2011-01-01", "2026-08-12")
        finally:
            bb_module.fetch_imf_gold_reserves_basket = orig_imf
            bb_module.fetch_usd_reserve_share = orig_cofer
            bb_module.FRED_SERIES = orig_fred
            bb_module.YAHOO_SYMBOLS = orig_yahoo

        self.assertEqual(called["args"], ("2011-01-01", "2026-08-12"))
        self.assertEqual(out, {"cb_gold_reserves": {"2026-06-30": 25000.0}, "usd_reserve_share": {}})


class TestFetchAllHistoryIncludesCofer(unittest.TestCase):
    def test_fetch_all_history_calls_the_cofer_fetcher(self):
        # FRED_SERIES/YAHOO_SYMBOLS/fetch_imf_gold_reserves_basket are
        # stubbed so this makes no real network calls for those paths --
        # only the COFER wiring is under test here.
        import backfill_baseline as bb_module
        orig_cofer = bb_module.fetch_usd_reserve_share
        orig_gold = bb_module.fetch_imf_gold_reserves_basket
        orig_fred = bb_module.FRED_SERIES
        orig_yahoo = bb_module.YAHOO_SYMBOLS
        called = {}

        def fake_cofer(start, end):
            called["args"] = (start, end)
            return (57.1, "2026-03-31", "2026-03-31", {"2026-03-31": 57.1})

        bb_module.fetch_usd_reserve_share = fake_cofer
        bb_module.fetch_imf_gold_reserves_basket = lambda start, end: (25000.0, "2026-06-30", "2026-06-30", {})
        bb_module.FRED_SERIES = {}
        bb_module.YAHOO_SYMBOLS = {}
        try:
            out = bb_module.fetch_all_history("dummy-key", "2011-01-01", "2026-08-12")
        finally:
            bb_module.fetch_usd_reserve_share = orig_cofer
            bb_module.fetch_imf_gold_reserves_basket = orig_gold
            bb_module.FRED_SERIES = orig_fred
            bb_module.YAHOO_SYMBOLS = orig_yahoo

        self.assertEqual(called["args"], ("2011-01-01", "2026-08-12"))
        self.assertEqual(out["usd_reserve_share"], {"2026-03-31": 57.1})


class TestMissingBaselineFields(unittest.TestCase):
    # Regression coverage for the annual-cron completeness gate: an unattended
    # run must refuse to write a BASELINE_STATS block that's missing fields a
    # flaky FRED/Yahoo call dropped, rather than silently shipping a smaller
    # baseline than last time (same failure class fetch_bullion_data.py's
    # truncated-write guard exists to prevent for data.json).
    def _full_synthetic_history(self):
        from datetime import datetime, timedelta, timezone
        base = datetime.now(timezone.utc)
        dates = [(base - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(27, -1, -1)]
        history = {}
        for i, f in enumerate(["hy_oas", "ig_oas", "sofr", "tbill_3m", "us10y", "us2y",
                                "vix", "spx", "fed_bs", "rrp", "ffr", "cpi_yoy", "dxy", "wti_px",
                                "nfp_mom", "cb_gold_reserves", "usd_reserve_share"]):
            history[f] = {d: 1.0 + i * 0.1 + 0.01 * n for n, d in enumerate(dates)}
        return history

    def test_complete_baseline_has_no_missing_fields(self):
        baseline = build_baseline(self._full_synthetic_history())
        self.assertEqual(missing_baseline_fields(baseline), [])

    def test_baseline_missing_a_field_is_flagged_not_silently_dropped(self):
        history = self._full_synthetic_history()
        del history["hy_oas"]  # simulate a single flaky fetch
        baseline = build_baseline(history)
        missing = missing_baseline_fields(baseline)
        self.assertIn("hy_oas", missing)
        # Everything else still fetched fine and must not be flagged.
        self.assertNotIn("vix", missing)
        self.assertNotIn("curve_slope", missing)

    def test_total_outage_flags_every_expected_field(self):
        baseline = {"fields": {}}
        self.assertEqual(sorted(missing_baseline_fields(baseline)), sorted(EXPECTED_BASELINE_FIELDS))


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
