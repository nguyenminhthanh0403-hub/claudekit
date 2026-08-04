"""Guard the Python↔JS freshness-tolerance duplication.

freshness_verdict() exists twice: once in fetch_bullion_data.py (which decides
what the FLAGGED log line says) and once inlined into every map HTML (which
decides what the live-status pill says). They are meant to be the same
function. Nothing forced them to stay the same, and they drifted: Mk17 added
the 'weekly' cadence to the Python table on 2026-07-26 and never added it to
the HTML, so fed_bs / mortgage_30y / nfci silently reported 'unknown' — the
one verdict the UI renders as nothing at all — for as long as they were stale.
A missing cadence key fails OPEN (looks healthy), which is why nobody saw it.

tests/freshness_test.html was supposed to catch exactly this, but it fetches
bullion_mk11_constellation.html, which became a redirect stub — so it had been
throwing 'marker comments not found' rather than asserting anything. This
test needs no browser and runs in the normal unittest sweep, so it cannot rot
the same way.

Frozen versions are deliberately NOT checked: this project freezes shipped
mk<N> files byte-for-byte, so an old file carrying an old table is correct.
Only the versions still being edited must agree with Python.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_bullion_data import CADENCE_TOLERANCE_DAYS, FIELD_TOLERANCE_OVERRIDE

MAP_DIR = os.path.join(os.path.dirname(__file__), "..")

# The maps still under active development. Add a file here when it is cut and
# remove it when it is frozen; a frozen file must never be edited to satisfy
# this test.
LIVE_MAPS = ["bullion_mk18.html", "bullion_mkultra.html"]

_JS_TABLE_RE = r"const\s+%s\s*=\s*\{([^}]*)\}"


def _parse_js_object(html, const_name):
    """Pull a flat `const NAME = { k: v, ... }` literal out of the HTML.

    Only handles the shape these two tables actually use — bare identifier
    keys with number or `null` values. Anything else raises rather than
    silently parsing to something that happens to compare equal.
    """
    m = re.search(_JS_TABLE_RE % const_name, html)
    if not m:
        raise AssertionError(f"{const_name} not found in map HTML")
    out = {}
    for part in m.group(1).split(","):
        part = part.strip()
        if not part:
            continue
        key, _, raw = part.partition(":")
        raw = raw.strip()
        out[key.strip()] = None if raw == "null" else float(raw)
    return out


def _normalise(table):
    """Python's table to the same shape _parse_js_object returns."""
    return {k: (None if v is None else float(v)) for k, v in table.items()}


class TestFreshnessToleranceParity(unittest.TestCase):
    def test_live_maps_match_python_cadence_tolerances(self):
        for name in LIVE_MAPS:
            with self.subTest(map=name):
                with open(os.path.join(MAP_DIR, name)) as f:
                    html = f.read()
                self.assertEqual(
                    _parse_js_object(html, "CADENCE_TOLERANCE_DAYS"),
                    _normalise(CADENCE_TOLERANCE_DAYS),
                    f"{name}'s CADENCE_TOLERANCE_DAYS has drifted from "
                    f"fetch_bullion_data.py; a cadence missing here reports "
                    f"'unknown' and the UI shows nothing.",
                )

    def test_live_maps_match_python_field_overrides(self):
        for name in LIVE_MAPS:
            with self.subTest(map=name):
                with open(os.path.join(MAP_DIR, name)) as f:
                    html = f.read()
                self.assertEqual(
                    _parse_js_object(html, "FIELD_TOLERANCE_OVERRIDE"),
                    _normalise(FIELD_TOLERANCE_OVERRIDE),
                    f"{name}'s FIELD_TOLERANCE_OVERRIDE has drifted from "
                    f"fetch_bullion_data.py.",
                )

    def test_live_maps_agree_on_pipeline_tolerance(self):
        """PIPELINE_TOLERANCE_DAYS has no Python source of truth (it's a
        UI-only banner threshold), so the two live maps are each other's only
        guard against silently drifting apart."""
        values = {}
        for name in LIVE_MAPS:
            with open(os.path.join(MAP_DIR, name)) as f:
                html = f.read()
            m = re.search(r"const\s+PIPELINE_TOLERANCE_DAYS\s*=\s*(\d+)", html)
            self.assertIsNotNone(m, f"PIPELINE_TOLERANCE_DAYS not found in {name}")
            values[name] = int(m.group(1))
        self.assertEqual(
            len(set(values.values())), 1,
            f"PIPELINE_TOLERANCE_DAYS has drifted between live maps: {values}",
        )

    def test_every_shipped_cadence_has_a_tolerance(self):
        """Catch the drift at its source: a FIELD_META cadence with no entry
        in the tolerance table is unjudgeable, which is how 'weekly' hid."""
        from fetch_bullion_data import FIELD_META

        for field, meta in FIELD_META.items():
            with self.subTest(field=field):
                self.assertIn(
                    meta["cadence"], CADENCE_TOLERANCE_DAYS,
                    f"{field} ships cadence {meta['cadence']!r}, which has no "
                    f"CADENCE_TOLERANCE_DAYS entry — its freshness can never "
                    f"be judged.",
                )


if __name__ == "__main__":
    unittest.main()
