import os
import sys
import tempfile
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


from fetch_bullion_data import build_envelope, FIELD_META


class TestBuildEnvelope(unittest.TestCase):
    LATEST = {
        "cpi_yoy": {"value": 2.6, "ref_date": "2026-06-01", "published": "2026-07-14"},
        "gold_px": {"value": 4018.8, "ref_date": "2026-07-17", "published": "2026-07-17"},
    }
    HISTORY = {
        "2026-07-17": {"gold_px": 4018.8},
        "2026-06-01": {"cpi_yoy": 2.6},
    }

    def build(self):
        return build_envelope(self.LATEST, self.HISTORY, "2026-07-20T10:07:14Z")

    def test_declares_schema_two(self):
        self.assertEqual(self.build()["schema"], 2)

    def test_history_passes_through_unchanged(self):
        # The date picker reads this block; its shape must not drift.
        self.assertEqual(self.build()["history"], self.HISTORY)

    def test_field_carries_full_provenance(self):
        f = self.build()["fields"]["cpi_yoy"]
        self.assertEqual(f["class"], "measured")
        self.assertEqual(f["cadence"], "monthly")
        self.assertEqual(f["source"], "FRED CPILFESL")
        self.assertEqual(f["ref_date"], "2026-06-01")
        self.assertEqual(f["published"], "2026-07-14")
        self.assertEqual(f["value"], 2.6)

    def test_yahoo_field_is_daily_and_measured(self):
        f = self.build()["fields"]["gold_px"]
        self.assertEqual(f["cadence"], "daily")
        self.assertEqual(f["source"], "Yahoo GC=F")

    def test_nasdaq_and_dow_field_meta(self):
        self.assertEqual(FIELD_META["nasdaq"],
                          {"class": "measured", "cadence": "daily", "source": "Yahoo ^IXIC"})
        self.assertEqual(FIELD_META["dow"],
                          {"class": "measured", "cadence": "daily", "source": "Yahoo ^DJI"})

    def test_omits_fields_that_failed_to_fetch(self):
        env = build_envelope({"gold_px": self.LATEST["gold_px"]}, self.HISTORY,
                             "2026-07-20T10:07:14Z")
        self.assertIn("gold_px", env["fields"])
        self.assertNotIn("cpi_yoy", env["fields"])

    def test_unmetadata_field_raises_rather_than_shipping_unlabelled(self):
        # The defect this whole schema exists to prevent: a value reaching
        # data.json with no provenance. Without this test, replacing the raise
        # with `continue` would silently drop the field and every other test
        # here would still pass.
        with self.assertRaises(KeyError):
            build_envelope(
                {"not_a_real_field": {"value": 1.0, "ref_date": "2026-07-17",
                                      "published": "2026-07-17"}},
                {}, "2026-07-20T10:07:14Z")

    def test_every_known_field_has_metadata(self):
        # A field fetched but absent from FIELD_META would ship with no
        # provenance, which is the bug this whole change exists to prevent.
        expected = {"us2y", "us10y", "vix", "ffr", "wti_px", "cpi_yoy",
                    "nfp_mom", "gold_px", "dxy", "spx", "nasdaq", "dow",
                    "nfci", "m2", "mortgage_30y", "hy_oas", "ig_oas",
                    "sofr", "tbill_3m", "fed_bs", "rrp",
                    "xlk", "xlf", "xle", "xlp", "cb_gold_reserves",
                    "usd_reserve_share"}
        self.assertEqual(set(FIELD_META), expected)
        for name, meta in FIELD_META.items():
            self.assertIn(meta["cadence"], {"daily", "weekly", "monthly", "quarterly", "fomc"})
            self.assertTrue(meta["source"])


import fetch_bullion_data as fetch_bullion_data_module


class TestMainRefusesIncompleteWrites(unittest.TestCase):
    """main() does real network I/O, so these drive it by monkeypatching the
    module's fetch/load functions and DATA_OUT_PATH — never the network, and
    never the real data.json. Both guards protect the live site from a
    truncated publish: Fix 3 covers a total outage (nothing fetched at all),
    Fix 4 covers a partial one (some fields fetched, at least one didn't)."""

    def setUp(self):
        self.mod = fetch_bullion_data_module
        self._orig_fetch_fred_series = self.mod.fetch_fred_series
        self._orig_fetch_yahoo_symbol = self.mod.fetch_yahoo_symbol
        self._orig_fetch_imf_basket = self.mod.fetch_imf_gold_reserves_basket
        self._orig_fetch_cofer = self.mod.fetch_usd_reserve_share
        self._orig_load_key = self.mod.load_key
        self._orig_data_out_path = self.mod.DATA_OUT_PATH

        fd, self.tmp_path = tempfile.mkstemp(prefix="bullion_test_data_", suffix=".json")
        os.close(fd)
        self.known_content = '{"sentinel": "yesterday-complete-file"}'
        with open(self.tmp_path, "w") as f:
            f.write(self.known_content)

        self.mod.DATA_OUT_PATH = self.tmp_path
        self.mod.load_key = lambda: "dummy-key"

    def tearDown(self):
        self.mod.fetch_fred_series = self._orig_fetch_fred_series
        self.mod.fetch_yahoo_symbol = self._orig_fetch_yahoo_symbol
        self.mod.fetch_imf_gold_reserves_basket = self._orig_fetch_imf_basket
        self.mod.fetch_usd_reserve_share = self._orig_fetch_cofer
        self.mod.load_key = self._orig_load_key
        self.mod.DATA_OUT_PATH = self._orig_data_out_path
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def _target_file_contents(self):
        with open(self.tmp_path) as f:
            return f.read()

    def test_total_outage_exits_without_touching_existing_file(self):
        # Fix 3: main()'s pre-existing "if not history_by_date" guard, added
        # for the case where nothing fetches at all. Deleting it left all 33
        # prior tests passing — nothing drove this path.
        #
        # Mocking every fetch to (None, None, None, {}) (a literal outage)
        # would also leave latest_out empty, which independently trips Fix
        # 4's "missing fields" guard below it — so that mock can't tell the
        # two guards apart post-Fix-4; deleting Fix 3 alone wouldn't turn
        # this test red. Instead every field succeeds with a real latest
        # value (so Fix 4 sees nothing missing) but an empty per-date
        # history ({}), so ONLY the history_by_date guard can catch it.
        self.mod.fetch_fred_series = (
            lambda series_id, key, units, decimals, start, end:
                (1.0, "2026-07-17", "2026-07-17", {}))
        self.mod.fetch_yahoo_symbol = (
            lambda symbol, decimals, range_="1y":
                (1.0, "2026-07-17", "2026-07-17", {}))
        self.mod.fetch_imf_gold_reserves_basket = (
            lambda start, end: (1.0, "2026-07-17", "2026-07-17", {}))
        self.mod.fetch_usd_reserve_share = (
            lambda start, end: (1.0, "2026-07-17", "2026-07-17", {}))

        with self.assertRaises(SystemExit):
            self.mod.main()

        self.assertEqual(self._target_file_contents(), self.known_content)

    def test_partial_fetch_exits_without_writing_truncated_file(self):
        # Fix 4: all but one field (us2y) fetch successfully. Publishing the
        # other nine behind a green exit code is exactly the defect being
        # closed, so this must also raise SystemExit and leave the prior
        # file untouched rather than writing nine of ten fields.
        def fake_fred(series_id, key, units, decimals, start, end):
            if series_id == "DGS2":  # -> us2y; the one deliberate failure
                return (None, None, None, {})
            return (1.23, "2026-07-17", "2026-07-18", {"2026-07-17": 1.23})

        def fake_yahoo(symbol, decimals, range_="1y"):
            return (99.9, "2026-07-17", "2026-07-17", {"2026-07-17": 99.9})

        self.mod.fetch_fred_series = fake_fred
        self.mod.fetch_yahoo_symbol = fake_yahoo
        self.mod.fetch_imf_gold_reserves_basket = (
            lambda start, end: (25000.0, "2026-07-17", "2026-07-17", {"2026-07-17": 25000.0}))
        self.mod.fetch_usd_reserve_share = (
            lambda start, end: (57.0, "2026-07-17", "2026-07-17", {"2026-07-17": 57.0}))

        with self.assertRaises(SystemExit):
            self.mod.main()

        self.assertEqual(self._target_file_contents(), self.known_content)


from fetch_bullion_data import parse_imf_sdmx, imf_period_to_end_date


class TestImfPeriodToEndDate(unittest.TestCase):
    def test_converts_month_period_to_last_day_of_month(self):
        self.assertEqual(imf_period_to_end_date("2026-M07"), "2026-07-31")

    def test_handles_february_in_a_leap_year(self):
        self.assertEqual(imf_period_to_end_date("2024-M02"), "2024-02-29")

    def test_converts_quarter_period_to_last_day_of_quarter(self):
        self.assertEqual(imf_period_to_end_date("2026-Q1"), "2026-03-31")
        self.assertEqual(imf_period_to_end_date("2026-Q2"), "2026-06-30")
        self.assertEqual(imf_period_to_end_date("2026-Q3"), "2026-09-30")
        self.assertEqual(imf_period_to_end_date("2026-Q4"), "2026-12-31")

    def test_unrecognised_shape_returns_none(self):
        self.assertIsNone(imf_period_to_end_date("2026"))
        self.assertIsNone(imf_period_to_end_date("2026-Q5"))
        self.assertIsNone(imf_period_to_end_date(""))


class TestParseImfSdmx(unittest.TestCase):
    PAYLOAD = {
        "data": {
            "dataSets": [{
                "series": {
                    "0:0:0:0": {
                        "observations": {
                            "0": ["261499000", None, 0, None],
                            "1": ["261499000.5", None, 0, None],
                        }
                    }
                }
            }],
            "structures": [{
                "dimensions": {
                    "observation": [{
                        "id": "TIME_PERIOD",
                        "values": [{"value": "2026-M06"}, {"value": "2026-M07"}],
                    }]
                }
            }],
        }
    }

    def test_returns_troy_oz_keyed_by_month_end_date(self):
        history = parse_imf_sdmx(self.PAYLOAD)
        self.assertEqual(history, {
            "2026-06-30": 261499000.0,
            "2026-07-31": 261499000.5,
        })

    def test_missing_series_key_returns_empty(self):
        payload = {"data": {"dataSets": [{}], "structures": [{"dimensions": {"observation": [{"values": []}]}}]}}
        self.assertEqual(parse_imf_sdmx(payload), {})

    def test_null_observation_value_is_skipped(self):
        payload = {
            "data": {
                "dataSets": [{"series": {"0:0:0:0": {"observations": {
                    "0": [None, None, 0, None],
                    "1": ["100.0", None, 0, None],
                }}}}],
                "structures": [{"dimensions": {"observation": [{
                    "values": [{"value": "2026-M06"}, {"value": "2026-M07"}],
                }]}}],
            }
        }
        self.assertEqual(parse_imf_sdmx(payload), {"2026-07-31": 100.0})

    def test_completely_malformed_payload_returns_empty(self):
        self.assertEqual(parse_imf_sdmx({}), {})
        self.assertEqual(parse_imf_sdmx({"data": {}}), {})


import fetch_bullion_data as fbd_module
from fetch_bullion_data import fetch_imf_gold_reserves_basket, IMF_GOLD_COUNTRIES


class TestFetchImfGoldReservesBasket(unittest.TestCase):
    def setUp(self):
        self._orig = fbd_module.fetch_imf_country_series

    def tearDown(self):
        fbd_module.fetch_imf_country_series = self._orig

    def test_sums_all_countries_for_their_common_latest_date(self):
        def fake(country, start, end):
            # every country reports through 2026-07-31; two also have a
            # stale August partial that must NOT be included since not
            # every country has it yet
            hist = {"2026-06-30": 100.0, "2026-07-31": 200.0}
            if country in ("USA", "DEU"):
                hist["2026-08-15"] = 999.0
            return hist
        fbd_module.fetch_imf_country_series = fake

        value, ref, pub, history = fetch_imf_gold_reserves_basket("2026-01-01", "2026-08-20")

        n = len(IMF_GOLD_COUNTRIES)
        self.assertEqual(ref, "2026-07-31")
        self.assertEqual(pub, ref, "IMF exposes no separate publication date")
        self.assertAlmostEqual(value, round(200.0 * n / fbd_module.TROY_OZ_PER_TONNE, 1))
        self.assertNotIn("2026-08-15", history)
        self.assertAlmostEqual(history["2026-06-30"], round(100.0 * n / fbd_module.TROY_OZ_PER_TONNE, 1))

    def test_any_single_country_failure_fails_the_whole_basket(self):
        def fake(country, start, end):
            if country == "RUS":
                return {}
            return {"2026-06-30": 100.0}
        fbd_module.fetch_imf_country_series = fake

        value, ref, pub, history = fetch_imf_gold_reserves_basket("2026-01-01", "2026-08-20")
        self.assertIsNone(value)
        self.assertIsNone(ref)
        self.assertIsNone(pub)
        self.assertEqual(history, {})

    def test_no_common_date_across_countries_fails_closed(self):
        def fake(country, start, end):
            # every country has data, but no two dates overlap
            return {f"2026-0{IMF_GOLD_COUNTRIES.index(country) % 9 + 1}-28": 100.0}
        fbd_module.fetch_imf_country_series = fake

        value, ref, pub, history = fetch_imf_gold_reserves_basket("2026-01-01", "2026-08-20")
        self.assertIsNone(value)
        self.assertEqual(history, {})


from fetch_bullion_data import fetch_usd_reserve_share


class TestFetchUsdReserveShare(unittest.TestCase):
    def setUp(self):
        self._orig = fbd_module.http_get_json

    def tearDown(self):
        fbd_module.http_get_json = self._orig

    PAYLOAD = {
        "data": {
            "dataSets": [{
                "series": {
                    "0:0:0:0:0": {
                        "observations": {
                            "0": ["58.3839225769043", None, 0, None],
                            "1": ["57.130786895752", None, 0, None],
                        }
                    }
                }
            }],
            "structures": [{
                "dimensions": {
                    "observation": [{
                        "values": [{"value": "2025-Q4"}, {"value": "2026-Q1"}],
                    }]
                }
            }],
        }
    }

    def test_returns_latest_rounded_percentage(self):
        fbd_module.http_get_json = lambda url: self.PAYLOAD

        value, ref, pub, history = fetch_usd_reserve_share("2025-01-01", "2026-08-12")

        self.assertEqual(value, 57.1)
        self.assertEqual(ref, "2026-03-31")
        self.assertEqual(pub, ref, "COFER exposes no separate publication date")
        self.assertEqual(history, {"2025-12-31": 58.4, "2026-03-31": 57.1})

    def test_http_error_returns_all_none(self):
        def raise_timeout(url):
            raise TimeoutError("boom")
        fbd_module.http_get_json = raise_timeout

        value, ref, pub, history = fetch_usd_reserve_share("2025-01-01", "2026-08-12")

        self.assertIsNone(value)
        self.assertIsNone(ref)
        self.assertIsNone(pub)
        self.assertEqual(history, {})

    def test_malformed_response_returns_all_none(self):
        fbd_module.http_get_json = lambda url: {}

        value, ref, pub, history = fetch_usd_reserve_share("2025-01-01", "2026-08-12")

        self.assertIsNone(value)
        self.assertEqual(history, {})

    def test_start_mid_quarter_snaps_filter_to_quarter_start(self):
        # start="2025-08-15" falls in Q3 (Jul-Sep); a naive "YYYY-MM"
        # truncation would filter ge:2025-08 and silently skip 2025-Q3
        # (July-September), which is legitimately in range. The filter must
        # snap back to the quarter's true start month, 2025-07.
        captured_urls = []

        def fake_http_get_json(url):
            captured_urls.append(url)
            return self.PAYLOAD

        fbd_module.http_get_json = fake_http_get_json

        fetch_usd_reserve_share("2025-08-15", "2026-08-12")

        self.assertEqual(len(captured_urls), 1)
        self.assertIn("c%5BTIME_PERIOD%5D=ge:2025-07", captured_urls[0])
        self.assertNotIn("ge:2025-08", captured_urls[0])


if __name__ == "__main__":
    unittest.main()
