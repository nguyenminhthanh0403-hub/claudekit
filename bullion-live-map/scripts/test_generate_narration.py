import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


class TestVoiceInstallationCheck(unittest.TestCase):
    """Tests that _voice_installed() correctly detects installed and missing voices."""

    def test_voice_installed_detects_real_voice(self):
        """Test that _voice_installed() returns True for "Jamie (Premium)"."""
        # This test actually queries the system for real voices
        result = gn._voice_installed("Jamie (Premium)")
        self.assertTrue(result, "Jamie (Premium) voice should be installed on this system")

    def test_voice_installed_rejects_fake_voice(self):
        """Test that _voice_installed() returns False for a clearly non-existent voice."""
        # Use a voice name that's almost certainly not installed
        result = gn._voice_installed("NonExistentVoiceXYZ123")
        self.assertFalse(result, "NonExistentVoiceXYZ123 should not be installed")

    def test_voice_installed_with_mocked_output(self):
        """Test that _voice_installed() correctly parses the output from 'say -v ?'."""
        # Mock the subprocess.run to return fake voice data
        mock_output = "Agnes  \nBruce  \nJamie (Premium)  \n"
        from unittest.mock import MagicMock
        with patch("generate_narration.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            # Should find Jamie (Premium) when mocked output includes it
            result = gn._voice_installed("Jamie (Premium)")
            self.assertTrue(result)

    def test_voice_installed_with_mocked_missing_voice(self):
        """Test that _voice_installed() returns False when voice is not in the mocked output."""
        mock_output = "Agnes  \nBruce  \n"
        from unittest.mock import MagicMock
        with patch("generate_narration.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            # Should not find Jamie (Premium) when it's not in mocked output
            result = gn._voice_installed("Jamie (Premium)")
            self.assertFalse(result)

    def test_main_raises_on_missing_voice(self):
        """Test that main() raises RuntimeError if the required voice is not installed."""
        with patch("generate_narration._voice_installed", return_value=False):
            with self.assertRaises(RuntimeError) as context:
                gn.main()
            self.assertIn("is not installed", str(context.exception))


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


class TestManifestCompleteness(unittest.TestCase):
    """Guards the invariant Task 2 established: every node in NODES has a
    NARRATION_MANIFEST entry in both shipped HTML files, and every entry has a
    real audio file behind it. A 40th node added without regenerating narration
    fails here instead of shipping a silent 🔊 button."""

    def _manifest_ids(self, html_path):
        text = html_path.read_text()
        start = text.index("const NARRATION_MANIFEST = {")
        end = text.index("};", start)
        body = text[start:end]
        return set(re.findall(r"^\s*(\w+):", body, re.M))

    def test_mk18_manifest_covers_every_node(self):
        nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
        node_ids = {n["id"] for n in nodes}
        manifest_ids = self._manifest_ids(ROOT / "bullion_mk18.html")
        self.assertEqual(node_ids, manifest_ids)

    def test_mkultra_manifest_covers_every_node(self):
        nodes = gn.extract_node_texts(ROOT / "bullion_mkultra.html")
        node_ids = {n["id"] for n in nodes}
        manifest_ids = self._manifest_ids(ROOT / "bullion_mkultra.html")
        self.assertEqual(node_ids, manifest_ids)

    def test_both_files_have_identical_node_text(self):
        # All 39 MP3s are generated from mk18's text alone. If mkultra's copy of
        # a node's text is edited without the matching mk18 edit (or vice versa),
        # mkultra's on-screen text drifts from its own voice-over silently.
        a = {n["id"]: n["text"] for n in gn.extract_node_texts(ROOT / "bullion_mk18.html")}
        b = {n["id"]: n["text"] for n in gn.extract_node_texts(ROOT / "bullion_mkultra.html")}
        self.assertEqual(a, b)

    def test_every_manifest_file_exists_and_nonempty(self):
        nodes = gn.extract_node_texts(ROOT / "bullion_mk18.html")
        for n in nodes:
            f = ROOT / "audio" / "narration" / f"node-{n['id']}.mp3"
            self.assertTrue(f.exists(), f"missing {f}")
            self.assertGreater(f.stat().st_size, 0, f"empty {f}")


if __name__ == "__main__":
    unittest.main()
