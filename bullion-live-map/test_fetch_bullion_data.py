import datetime as dt
import unittest
import fetch_bullion_data as f

NEW_FRED = {"NFCI","M2SL","MORTGAGE30US","BAMLH0A0HYM2","BAMLC0A0CM",
            "SOFR","DTB3","WALCL","RRPONTSYD"}
NEW_YAHOO = {"XLK","XLF","XLE","XLP"}

class TestWeeklyCadence(unittest.TestCase):
    def test_weekly_bucket_exists(self):
        self.assertEqual(f.CADENCE_TOLERANCE_DAYS.get("weekly"), 10)

    def test_weekly_fresh_at_8_days(self):
        pub = dt.date(2026, 7, 17)
        today = dt.date(2026, 7, 25)  # 8 days later
        state, age = f.freshness_verdict("weekly", pub, today)
        self.assertEqual(state, "fresh")
        self.assertEqual(age, 8)

    def test_weekly_flagged_past_10_days(self):
        pub = dt.date(2026, 7, 12)
        today = dt.date(2026, 7, 25)  # 13 days later
        state, _ = f.freshness_verdict("weekly", pub, today)
        self.assertEqual(state, "flagged")

class TestProvenanceCoverage(unittest.TestCase):
    def test_every_series_has_field_meta(self):
        # Mirrors build_envelope's guarantee: no field ships without provenance.
        fred_fields = {out for (out, _units, _dec) in f.FRED_SERIES.values()}
        yahoo_fields = {out for (out, _dec) in f.YAHOO_SYMBOLS.values()}
        for name in fred_fields | yahoo_fields:
            self.assertIn(name, f.FIELD_META, f"{name} missing FIELD_META")

    def test_new_series_present(self):
        self.assertTrue(NEW_FRED.issubset(set(f.FRED_SERIES.keys())))
        self.assertTrue(NEW_YAHOO.issubset(set(f.YAHOO_SYMBOLS.keys())))

    def test_new_field_cadences(self):
        want = {"nfci":"weekly","fed_bs":"weekly","mortgage_30y":"weekly",
                "m2":"monthly","sofr":"daily","rrp":"daily","tbill_3m":"daily",
                "hy_oas":"daily","ig_oas":"daily",
                "xlk":"daily","xlf":"daily","xle":"daily","xlp":"daily"}
        for field, cad in want.items():
            self.assertEqual(f.FIELD_META[field]["cadence"], cad, field)

if __name__ == "__main__":
    unittest.main()
