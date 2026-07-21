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


if __name__ == "__main__":
    unittest.main()
