import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_bullion_data import (
    freshness_verdict,
    CADENCE_TOLERANCE_DAYS,
    FIELD_TOLERANCE_OVERRIDE,
)

TODAY = date(2026, 7, 20)


class TestFreshnessVerdict(unittest.TestCase):
    def test_daily_within_tolerance_is_fresh(self):
        state, age = freshness_verdict("daily", date(2026, 7, 14), TODAY)
        self.assertEqual(state, "fresh")
        self.assertEqual(age, 6)

    def test_daily_exactly_at_tolerance_is_fresh(self):
        state, age = freshness_verdict("daily", date(2026, 7, 13), TODAY)
        self.assertEqual(state, "fresh")
        self.assertEqual(age, 7)

    def test_daily_past_tolerance_is_flagged(self):
        state, age = freshness_verdict("daily", date(2026, 7, 12), TODAY)
        self.assertEqual(state, "flagged")
        self.assertEqual(age, 8)

    def test_wti_override_keeps_eight_days_fresh(self):
        # 8 days would be flagged under the 7-day daily default; wti_px
        # publishes on a structurally longer lag and gets 10.
        state, age = freshness_verdict(
            "daily", date(2026, 7, 12), TODAY,
            override_days=FIELD_TOLERANCE_OVERRIDE["wti_px"])
        self.assertEqual(state, "fresh")
        self.assertEqual(age, 8)

    def test_wti_override_still_flags_at_eleven_days(self):
        state, age = freshness_verdict(
            "daily", date(2026, 7, 9), TODAY,
            override_days=FIELD_TOLERANCE_OVERRIDE["wti_px"])
        self.assertEqual(state, "flagged")
        self.assertEqual(age, 11)

    def test_monthly_within_tolerance_is_fresh(self):
        state, age = freshness_verdict("monthly", date(2026, 6, 6), TODAY)
        self.assertEqual(state, "fresh")
        self.assertEqual(age, 44)

    def test_monthly_past_tolerance_is_flagged(self):
        state, age = freshness_verdict("monthly", date(2026, 6, 4), TODAY)
        self.assertEqual(state, "flagged")
        self.assertEqual(age, 46)

    def test_real_world_cpi_is_fresh_despite_old_reference_period(self):
        # June CPI references 2026-06-01 (49 days old) but published
        # 2026-07-14 (6 days old). Judged on publication it is healthy.
        state, age = freshness_verdict("monthly", date(2026, 7, 14), TODAY)
        self.assertEqual(state, "fresh")
        self.assertEqual(age, 6)

    def test_fomc_cadence_is_unknown(self):
        state, age = freshness_verdict("fomc", date(2026, 7, 14), TODAY)
        self.assertEqual(state, "unknown")
        self.assertIsNone(age)

    def test_missing_published_date_is_unknown(self):
        state, age = freshness_verdict("daily", None, TODAY)
        self.assertEqual(state, "unknown")
        self.assertIsNone(age)

    def test_unrecognised_cadence_is_unknown(self):
        state, age = freshness_verdict("hourly", date(2026, 7, 19), TODAY)
        self.assertEqual(state, "unknown")
        self.assertIsNone(age)

    def test_tolerance_table_matches_spec(self):
        self.assertEqual(CADENCE_TOLERANCE_DAYS["daily"], 7)
        self.assertEqual(CADENCE_TOLERANCE_DAYS["monthly"], 45)
        self.assertIsNone(CADENCE_TOLERANCE_DAYS["fomc"])
        self.assertEqual(FIELD_TOLERANCE_OVERRIDE["wti_px"], 10)


from fetch_bullion_data import (
    parse_fred_observations,
    parse_yahoo_chart,
    fred_observation_params,
)


class TestParseFredObservations(unittest.TestCase):
    PAYLOAD = {
        "observations": [
            {"realtime_start": "2026-05-12", "realtime_end": "9999-12-31",
             "date": "2026-04-01", "value": "335.423"},
            {"realtime_start": "2026-06-10", "realtime_end": "9999-12-31",
             "date": "2026-05-01", "value": "336.121"},
            {"realtime_start": "2026-07-14", "realtime_end": "9999-12-31",
             "date": "2026-06-01", "value": "336.065"},
        ]
    }

    def test_returns_latest_value_reference_and_publication_dates(self):
        value, ref, pub, hist = parse_fred_observations(self.PAYLOAD, decimals=1)
        self.assertEqual(value, 336.1)
        self.assertEqual(ref, "2026-06-01")
        self.assertEqual(pub, "2026-07-14")

    def test_builds_full_history_keyed_by_reference_date(self):
        _, _, _, hist = parse_fred_observations(self.PAYLOAD, decimals=1)
        self.assertEqual(len(hist), 3)
        self.assertEqual(hist["2026-04-01"], 335.4)

    def test_skips_missing_value_sentinel(self):
        payload = {"observations": [
            {"realtime_start": "2026-07-16", "date": "2026-07-15", "value": "."},
            {"realtime_start": "2026-07-17", "date": "2026-07-16", "value": "4.21"},
        ]}
        value, ref, pub, hist = parse_fred_observations(payload, decimals=2)
        self.assertEqual(value, 4.21)
        self.assertEqual(ref, "2026-07-16")
        self.assertEqual(len(hist), 1)

    def test_empty_payload_returns_all_none(self):
        value, ref, pub, hist = parse_fred_observations({"observations": []}, decimals=2)
        self.assertIsNone(value)
        self.assertIsNone(ref)
        self.assertIsNone(pub)
        self.assertEqual(hist, {})

    def test_missing_realtime_start_yields_none_publication(self):
        payload = {"observations": [
            {"date": "2026-07-16", "value": "4.21"},
        ]}
        value, ref, pub, hist = parse_fred_observations(payload, decimals=2)
        self.assertEqual(value, 4.21)
        self.assertEqual(ref, "2026-07-16")
        self.assertIsNone(pub)

    def test_multi_vintage_newest_first_keeps_greatest_realtime_start(self):
        # Same observation date, two vintages, newest row supplied first.
        payload = {"observations": [
            {"realtime_start": "2026-07-20", "realtime_end": "9999-12-31",
             "date": "2026-07-17", "value": "4.25"},
            {"realtime_start": "2026-07-18", "realtime_end": "9999-12-31",
             "date": "2026-07-17", "value": "4.20"},
        ]}
        value, ref, pub, hist = parse_fred_observations(payload, decimals=2)
        self.assertEqual(value, 4.25)
        self.assertEqual(ref, "2026-07-17")
        self.assertEqual(pub, "2026-07-20")
        self.assertEqual(hist["2026-07-17"], 4.25)

    def test_multi_vintage_oldest_first_keeps_greatest_realtime_start(self):
        # Same two rows as above, supplied oldest-first: result must be
        # identical, proving resolution is order-independent.
        payload = {"observations": [
            {"realtime_start": "2026-07-18", "realtime_end": "9999-12-31",
             "date": "2026-07-17", "value": "4.20"},
            {"realtime_start": "2026-07-20", "realtime_end": "9999-12-31",
             "date": "2026-07-17", "value": "4.25"},
        ]}
        value, ref, pub, hist = parse_fred_observations(payload, decimals=2)
        self.assertEqual(value, 4.25)
        self.assertEqual(ref, "2026-07-17")
        self.assertEqual(pub, "2026-07-20")
        self.assertEqual(hist["2026-07-17"], 4.25)

    def test_row_with_realtime_start_beats_row_without_for_same_date(self):
        # A row missing realtime_start must sort as oldest, so a row that
        # HAS a realtime_start always wins for the same observation date,
        # regardless of order.
        payload = {"observations": [
            {"date": "2026-07-17", "value": "4.20"},
            {"realtime_start": "2026-07-20", "realtime_end": "9999-12-31",
             "date": "2026-07-17", "value": "4.25"},
        ]}
        value, ref, pub, hist = parse_fred_observations(payload, decimals=2)
        self.assertEqual(value, 4.25)
        self.assertEqual(pub, "2026-07-20")

    def test_single_vintage_per_date_unchanged(self):
        # Existing single-vintage behaviour: no competing rows per date.
        payload = {"observations": [
            {"realtime_start": "2026-07-19", "realtime_end": "9999-12-31",
             "date": "2026-07-16", "value": "4.10"},
            {"realtime_start": "2026-07-20", "realtime_end": "9999-12-31",
             "date": "2026-07-17", "value": "4.21"},
        ]}
        value, ref, pub, hist = parse_fred_observations(payload, decimals=2)
        self.assertEqual(value, 4.21)
        self.assertEqual(ref, "2026-07-17")
        self.assertEqual(pub, "2026-07-20")
        self.assertEqual(hist["2026-07-16"], 4.10)
        self.assertEqual(len(hist), 2)


class TestFredObservationParams(unittest.TestCase):
    def test_units_set_excludes_realtime_keys(self):
        params = fred_observation_params(
            "CPILFESL", "KEY", "pc1", "2026-01-01", "2026-07-20")
        self.assertNotIn("realtime_start", params)
        self.assertNotIn("realtime_end", params)
        self.assertEqual(params["units"], "pc1")

    def test_units_unset_includes_both_realtime_keys(self):
        params = fred_observation_params(
            "DGS2", "KEY", None, "2026-01-01", "2026-07-20")
        self.assertEqual(params["realtime_start"], "2026-01-01")
        self.assertEqual(params["realtime_end"], "9999-12-31")
        self.assertNotIn("units", params)

    def test_publication_date_params_always_have_both_realtime_keys_and_no_units(self):
        import fetch_bullion_data as mod
        captured = {}

        def fake_http_get_json(url, timeout=15):
            captured["url"] = url
            return {"observations": [{"date": "2026-07-01", "realtime_start": "2026-07-05"}]}

        original = mod.http_get_json
        mod.http_get_json = fake_http_get_json
        try:
            mod.fetch_fred_publication_date(
                "CPILFESL", "KEY", "2026-01-01", "2026-07-20")
        finally:
            mod.http_get_json = original

        self.assertIn("realtime_start=", captured["url"])
        self.assertIn("realtime_end=", captured["url"])
        self.assertNotIn("units=", captured["url"])


class TestParseYahooChart(unittest.TestCase):
    PAYLOAD = {
        "chart": {"result": [{
            "timestamp": [1784332800, 1784419200],
            "indicators": {"quote": [{"close": [4001.5, 4018.84]}]},
            "meta": {"regularMarketPrice": 4018.84},
        }]}
    }

    def test_reference_and_publication_dates_are_equal(self):
        value, ref, pub, hist = parse_yahoo_chart(self.PAYLOAD, decimals=2)
        self.assertEqual(value, 4018.84)
        self.assertEqual(ref, pub,
                         "a daily close is both the reference period and the "
                         "moment it exists")

    def test_unexpected_shape_returns_all_none(self):
        value, ref, pub, hist = parse_yahoo_chart({"chart": {"result": []}}, decimals=2)
        self.assertIsNone(value)
        self.assertIsNone(ref)
        self.assertIsNone(pub)
        self.assertEqual(hist, {})


if __name__ == "__main__":
    unittest.main()
