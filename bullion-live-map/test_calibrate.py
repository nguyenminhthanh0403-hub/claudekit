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
    def test_dxy_us10y_is_measured(self):
        # controller-adopted Mk15 cell: sign matches hand +1, |t|>2, regressor varied
        fit = {'slope': 0.0449, 't': 6.6, 'x_span': 2.37}
        tier, _ = c.verdict(1, fit)
        self.assertEqual(tier, 'measured')
    def test_us10y_spx_candidate_is_directional(self):
        # rejected: |t|<2
        fit = {'slope': -0.027, 't': -1.9, 'x_span': 0.28}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'directional')
    def test_vix_wti_candidate_signflip_is_directional(self):
        # rejected: fitted sign (+) disagrees with hand sign (-)
        fit = {'slope': 0.0058, 't': 4.3, 'x_span': 11.1}
        tier, _ = c.verdict(-1, fit)
        self.assertEqual(tier, 'directional')

class TestMk17Cells(unittest.TestCase):
    MK17_TARGETS = {'mortgage_30y','xlk','xlf','xle','xlp','hy_oas','sofr','tbill_3m'}
    def test_mk17_cells_present_and_wellformed(self):
        tgt_fields = {tgtfield for (_d, _k, tgtfield, _kind, _hand) in c.CELLS}
        self.assertTrue(self.MK17_TARGETS.issubset(tgt_fields),
                        f"missing Mk17 target cells: {self.MK17_TARGETS - tgt_fields}")
        for (drv, key, tgtfield, kind, hand) in c.CELLS:
            self.assertIn(kind, ('level','pct','add'), f"{key} bad kind {kind}")
            self.assertIsInstance(hand, (int, float))

FAKE_MAP = """
const NODES = [ {id:'a'} ];
const LINKS = [
  {s:'usd', t:'oil', w:1, sign:-1, aud:false, why:'Priced in dollars, so it\\'s pricier.', stat:'Roughly -0.3 (EIA).'},
  {s:'ffr', t:'privcredit', w:2, sign:0, conf:'directional', why:'Cuts both ways.', stat:'Floating-rate (Fed).'},
  {s:'fed', t:'fomc', w:3, sign:1, conf:CONF.MEASURED, why:'Sets the target.', stat:'Fitted (FRED).'},
  {s:'sec', t:'equit', w:2, sign:1, why:'Disclosure underpins trust.', stat:'Structural (SEC).'},
];
"""

class TestParseLinks(unittest.TestCase):
    def test_parses_every_row(self):
        links = c.parse_links(FAKE_MAP)
        self.assertEqual(len(links), 4)
        self.assertEqual([l['s'] for l in links], ['usd','ffr','fed','sec'])
    def test_parses_signs_including_zero(self):
        links = c.parse_links(FAKE_MAP)
        self.assertEqual([l['sign'] for l in links], [-1, 0, 1, 1])
    def test_normalises_quoted_and_constant_conf(self):
        # the map uses both conf:'directional' and conf:CONF.MEASURED
        links = c.parse_links(FAKE_MAP)
        self.assertEqual([l['conf'] for l in links],
                         [None, 'directional', 'measured', None])
    def test_prose_with_escaped_apostrophe_does_not_split_a_row(self):
        # "it\\'s" in the first row must not end the row early
        self.assertEqual(c.parse_links(FAKE_MAP)[0]['t'], 'oil')

class TestLinkCandidates(unittest.TestCase):
    def test_drops_links_with_an_unmapped_endpoint(self):
        # 'sec' and 'privcredit' bind to no data.json field
        cands = c.link_candidates(c.parse_links(FAKE_MAP))
        pairs = {(l['s'], l['t']) for l in cands}
        self.assertNotIn(('sec','equit'), pairs)
        self.assertNotIn(('ffr','privcredit'), pairs)
    def test_drops_degenerate_same_field_pairs(self):
        # fomc and ffr both resolve to the `ffr` field: regressing a series on
        # itself always "fits" and proves nothing
        cands = c.link_candidates([{'s':'fed','t':'fomc','sign':1,'conf':None},
                                   {'s':'fomc','t':'ffr','sign':1,'conf':None},
                                   {'s':'tsy','t':'yield','sign':1,'conf':None},
                                   {'s':'usd','t':'dxy_fx','sign':1,'conf':None}])
        self.assertEqual([(l['s'], l['t']) for l in cands], [('fed','fomc')])
    def test_kind_is_pct_for_prices_level_for_rates(self):
        cands = c.link_candidates([{'s':'usd','t':'oil','sign':-1,'conf':None},
                                   {'s':'vix','t':'credit','sign':1,'conf':None}])
        self.assertEqual(cands[0]['kind'], 'pct')     # wti_px is a price
        self.assertEqual(cands[1]['kind'], 'level')   # hy_oas is a spread

class TestLinkVerdict(unittest.TestCase):
    STRONG = {'slope': -0.9, 't': -5.3, 'x_span': 0.7, 'n': 199}
    def test_promotes_when_sign_matches_and_significant(self):
        tier, action, _ = c.link_verdict(-1, self.STRONG)
        self.assertEqual((tier, action), ('measured', ''))
    def test_flips_when_strong_fit_contradicts_hand_sign(self):
        tier, action, why = c.link_verdict(+1, self.STRONG)
        self.assertEqual((tier, action), ('measured', 'flip'))
        self.assertIn('contradicts', why)
    def test_weak_contradiction_is_a_conflict_not_a_flip(self):
        tier, action, _ = c.link_verdict(+1, {'slope': -0.9, 't': -1.3, 'x_span': 0.7, 'n': 199})
        self.assertEqual((tier, action), ('directional', 'conflict'))
    def test_insignificant_fit_is_never_promoted(self):
        tier, action, _ = c.link_verdict(-1, {'slope': -0.9, 't': -0.4, 'x_span': 0.7, 'n': 199})
        self.assertEqual((tier, action), ('directional', ''))
    def test_t_boundary_is_strictly_above_two(self):
        at = c.link_verdict(-1, {'slope': -0.9, 't': -2.0, 'x_span': 0.7, 'n': 199})
        above = c.link_verdict(-1, {'slope': -0.9, 't': -2.01, 'x_span': 0.7, 'n': 199})
        self.assertEqual(at[0], 'directional')     # |t| == 2 does not promote
        self.assertEqual(above[0], 'measured')
    def test_thin_sample_is_never_promoted_however_large_t(self):
        # monthly series give ~8 daily first differences; a t-stat there is noise
        tier, action, why = c.link_verdict(+1, {'slope': 0.94, 't': 4.7, 'x_span': 2.0, 'n': 8})
        self.assertEqual((tier, action), ('directional', ''))
        self.assertIn('too coarse', why)
    def test_conditional_hand_sign_is_flagged_for_review_never_rewritten(self):
        tier, action, why = c.link_verdict(0, self.STRONG)
        self.assertEqual((tier, action), ('directional', 'review'))
        self.assertIn('sign:0', why)
    def test_conditional_stays_quiet_when_fit_is_weak(self):
        tier, action, _ = c.link_verdict(0, {'slope': -0.9, 't': -1.0, 'x_span': 0.7, 'n': 199})
        self.assertEqual((tier, action), ('directional', ''))
    def test_flat_regressor_is_directional(self):
        tier, action, why = c.link_verdict(-1, {'slope': -0.9, 't': -5.0, 'x_span': 0.0, 'n': 199})
        self.assertEqual((tier, action), ('directional', ''))
        self.assertIn('did not vary', why)

if __name__ == '__main__':
    unittest.main()
