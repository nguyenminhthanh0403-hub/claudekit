import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_narration as gn

ROOT = Path(__file__).resolve().parent.parent


class TestExtractNodeTexts(unittest.TestCase):
    def test_extracts_all_39_nodes(self):
        nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
        self.assertEqual(len(nodes), 39)

    def test_each_node_has_id_and_nonempty_text(self):
        nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
        for n in nodes:
            self.assertIn("id", n)
            self.assertIn("text", n)
            self.assertTrue(n["text"].strip())

    def test_known_pilot_node_text_matches_pilot_wording(self):
        nodes = {n["id"]: n["text"] for n in gn.extract_node_texts(ROOT / "bullion_mk18.html")}
        self.assertEqual(
            nodes["fed"],
            "The central bank that controls interest rates and money supply. "
            "It keeps prices stable, supports jobs, and lends as a last resort in crises."
        )


class TestHtmlEntityRoundTrip(unittest.TestCase):
    """The payload rides back inside a <title>, which Chrome's DOM serializer
    entity-escapes. Without unescaping, text containing &, <, > or nbsp comes
    back corrupted AND still parses as JSON — silent drift, exactly what this
    extractor exists to prevent."""

    def _extract_beginner(self, beginner_js):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixture.html"
            fixture.write_text(
                "<html><body><script>const NODES = [{id:'x', beginner:["
                + beginner_js
                + "]}];</script></body></html>"
            )
            nodes = gn.extract_node_texts(fixture)
        self.assertEqual(len(nodes), 1)
        return nodes[0]["text"]

    def test_special_characters_survive_the_title_transport(self):
        self.assertEqual(self._extract_beginner("'A & B < C > D'"), "A & B < C > D")

    def test_literal_entity_text_is_not_double_unescaped(self):
        # A literal "&copy;" in the source must stay "&copy;", not become "©".
        self.assertEqual(self._extract_beginner("'see &copy; 2026'"), "see &copy; 2026")

    def test_nonbreaking_space_survives(self):
        # Must come back as a real U+00A0, not the literal string "&nbsp;".
        self.assertEqual(
            self._extract_beginner("'gap\\u00a0here'"), "gap\u00a0here"
        )


if __name__ == "__main__":
    unittest.main()
