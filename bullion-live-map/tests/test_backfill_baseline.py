import os
import statistics
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backfill_baseline import field_stats, forward_fill, fetch_all_history


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


if __name__ == "__main__":
    unittest.main()
