import sys
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


if __name__ == "__main__":
    unittest.main()
