import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_calibration_history import transpose_to_date_major, missing_fields, EXPECTED_FIELDS
import fetch_calibration_history as fetch_calibration_history_module


class TestTransposeToDateMajor(unittest.TestCase):
    def test_transposes_field_major_to_date_major(self):
        field_major = {
            "vix": {"2026-01-02": 14.5, "2026-01-03": 15.1},
            "spx": {"2026-01-02": 4800.0},
        }
        result = transpose_to_date_major(field_major)
        self.assertEqual(result, {
            "2026-01-02": {"vix": 14.5, "spx": 4800.0},
            "2026-01-03": {"vix": 15.1},
        })

    def test_empty_field_major_yields_empty_history(self):
        self.assertEqual(transpose_to_date_major({}), {})


class TestMissingFields(unittest.TestCase):
    def test_no_fields_missing_when_all_present(self):
        field_major = {f: {"2026-01-02": 1.0} for f in EXPECTED_FIELDS}
        self.assertEqual(missing_fields(field_major), [])

    def test_reports_fields_with_empty_history(self):
        field_major = {f: {"2026-01-02": 1.0} for f in EXPECTED_FIELDS}
        field_major["vix"] = {}  # simulate a failed fetch
        self.assertIn("vix", missing_fields(field_major))

    def test_reports_fields_entirely_absent(self):
        field_major = {f: {"2026-01-02": 1.0} for f in EXPECTED_FIELDS if f != "spx"}
        self.assertIn("spx", missing_fields(field_major))


class TestMainGuardsAgainstPartialFetch(unittest.TestCase):
    def setUp(self):
        self.mod = fetch_calibration_history_module
        self._orig_fetch_all_history = self.mod.fetch_all_history
        self._orig_load_key = self.mod.load_key
        self._orig_out_path = self.mod.OUT_PATH

        fd, self.tmp_path = tempfile.mkstemp(prefix="bullion_calib_test_", suffix=".json")
        os.close(fd)
        os.remove(self.tmp_path)

        self.mod.OUT_PATH = self.tmp_path
        self.mod.load_key = lambda: "dummy-key"

    def tearDown(self):
        self.mod.fetch_all_history = self._orig_fetch_all_history
        self.mod.load_key = self._orig_load_key
        self.mod.OUT_PATH = self._orig_out_path
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    def test_partial_fetch_exits_without_writing(self):
        def fake_fetch_all_history(key, start, end):
            out = {f: {"2026-01-02": 1.0} for f in self.mod.EXPECTED_FIELDS}
            out["vix"] = {}
            return out
        self.mod.fetch_all_history = fake_fetch_all_history

        with self.assertRaises(SystemExit):
            self.mod.main()

        self.assertFalse(os.path.exists(self.tmp_path))

    def test_complete_fetch_writes_date_major_history(self):
        def fake_fetch_all_history(key, start, end):
            return {f: {"2026-01-02": 1.0, "2026-01-03": 2.0}
                    for f in self.mod.EXPECTED_FIELDS}
        self.mod.fetch_all_history = fake_fetch_all_history

        self.mod.main()

        with open(self.tmp_path) as f:
            written = json.load(f)
        self.assertIn("history", written)
        self.assertEqual(set(written["history"]["2026-01-02"]), set(self.mod.EXPECTED_FIELDS))


if __name__ == "__main__":
    unittest.main()
