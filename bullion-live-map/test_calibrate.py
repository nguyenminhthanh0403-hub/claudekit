import unittest
import calibrate as c

class TestSplit(unittest.TestCase):
    def test_split_80_20(self):
        dates = [f'2025-01-{d:02d}' for d in range(1, 11)]  # 10 dates
        train = c.train_split(dates)
        self.assertEqual(len(train), 8)                 # floor(0.8*10)=8
        self.assertIn('2025-01-08', train)
        self.assertNotIn('2025-01-09', train)           # held out
    def test_split_is_prefix(self):
        dates = ['2025-01-03','2025-01-01','2025-01-02','2025-01-05','2025-01-04']
        train = c.train_split(dates)                    # must sort first
        self.assertEqual(train, {'2025-01-01','2025-01-02','2025-01-03','2025-01-04'})

class TestVerdict(unittest.TestCase):
    def test_promote_when_sign_matches_and_significant(self):
        fit = {'slope': -0.9, 't': -5.3, 'x_span': 0.7}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'measured')
    def test_keep_when_sign_flips(self):
        fit = {'slope': +0.4, 't': 5.0, 'x_span': 0.7}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'directional')
    def test_keep_when_insignificant(self):
        fit = {'slope': -0.9, 't': 0.4, 'x_span': 0.7}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'directional')
    def test_keep_when_regressor_flat(self):
        fit = {'slope': -0.9, 't': 5.0, 'x_span': 0.0}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'directional')
    def test_verdict_nan_t_is_directional(self):
        from calibrate import verdict
        fit = {"slope": 0.5, "t": float("nan"), "x_span": 1.0}
        tier, why = verdict(1, fit)
        self.assertEqual(tier, "directional")
        self.assertIn("not significant", why)

if __name__ == '__main__':
    unittest.main()
