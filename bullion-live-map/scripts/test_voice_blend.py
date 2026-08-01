import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_narration as gn

ROOT = Path(__file__).resolve().parent.parent


class TestBuildBlendedRefDict(unittest.TestCase):
    """build_blended_ref_dict must average only the fixed-size 'embedding'
    x-vector across clips, and take the variable-length acoustic prompt
    (prompt_token/prompt_feat) from exactly one designated clip — see the
    design spec's 2026-08-01 correction. Averaging prompt_token/prompt_feat
    across differently-shaped clips would shape-mismatch or produce mush."""

    def _fake_ref_dict(self, embedding_value, prompt_token_value):
        return {
            "embedding": torch.tensor([[embedding_value, embedding_value + 1.0]]),
            "prompt_token": torch.tensor([[prompt_token_value]]),
            "prompt_token_len": torch.tensor([1]),
            "prompt_feat": torch.tensor([[[float(prompt_token_value)]]]),
            "prompt_feat_len": None,
        }

    def test_averages_embedding_across_two_clips(self):
        clip_a = Path("/fake/a.wav")
        clip_b = Path("/fake/b.wav")
        fakes = {
            clip_a: self._fake_ref_dict(1.0, 11),
            clip_b: self._fake_ref_dict(3.0, 22),
        }
        with patch(
            "generate_narration.embed_reference_clip",
            side_effect=lambda vc, path: fakes[path],
        ):
            result = gn.build_blended_ref_dict(
                vc=object(),
                embedding_clip_paths=[clip_a, clip_b],
                prompt_clip_path=clip_b,
            )
        self.assertTrue(
            torch.equal(result["embedding"], torch.tensor([[2.0, 3.0]]))
        )

    def test_prompt_fields_come_from_the_designated_clip_only(self):
        clip_a = Path("/fake/a.wav")
        clip_b = Path("/fake/b.wav")
        clip_c = Path("/fake/c.wav")
        fakes = {
            clip_a: self._fake_ref_dict(1.0, 11),
            clip_b: self._fake_ref_dict(3.0, 22),
            clip_c: self._fake_ref_dict(5.0, 33),
        }
        with patch(
            "generate_narration.embed_reference_clip",
            side_effect=lambda vc, path: fakes[path],
        ):
            result = gn.build_blended_ref_dict(
                vc=object(),
                embedding_clip_paths=[clip_a, clip_b, clip_c],
                prompt_clip_path=clip_a,
            )
        self.assertTrue(
            torch.equal(result["prompt_token"], fakes[clip_a]["prompt_token"])
        )
        self.assertTrue(
            torch.equal(result["prompt_feat"], fakes[clip_a]["prompt_feat"])
        )
        self.assertIsNone(result["prompt_feat_len"])

    def test_three_way_average_matches_johnny_blend_shape(self):
        clip_a = Path("/fake/a.wav")
        clip_b = Path("/fake/b.wav")
        clip_c = Path("/fake/c.wav")
        fakes = {
            clip_a: self._fake_ref_dict(0.0, 1),
            clip_b: self._fake_ref_dict(3.0, 2),
            clip_c: self._fake_ref_dict(6.0, 3),
        }
        with patch(
            "generate_narration.embed_reference_clip",
            side_effect=lambda vc, path: fakes[path],
        ):
            result = gn.build_blended_ref_dict(
                vc=object(),
                embedding_clip_paths=[clip_a, clip_b, clip_c],
                prompt_clip_path=clip_b,
            )
        self.assertTrue(
            torch.equal(result["embedding"], torch.tensor([[3.0, 4.0]]))
        )


class TestEnsureReferenceClips(unittest.TestCase):
    def test_raises_if_user_voice_missing(self):
        with patch.object(gn, "USER_VOICE_PATH", Path("/nonexistent/user_voice.wav")):
            with self.assertRaises(RuntimeError) as ctx:
                gn.ensure_reference_clips()
            self.assertIn("missing", str(ctx.exception))

    def test_synthesizes_missing_tom_and_jamie_clips(self):
        with patch.object(gn, "USER_VOICE_PATH", ROOT / "audio" / "voice_sample" / "user_voice.wav"), \
             patch.object(gn, "TOM_SAMPLE_PATH", Path("/tmp/does-not-exist-tom.wav")), \
             patch.object(gn, "JAMIE_SAMPLE_PATH", Path("/tmp/does-not-exist-jamie.wav")), \
             patch("generate_narration.synthesize_reference_wav") as mock_synth:
            gn.ensure_reference_clips()
            self.assertEqual(mock_synth.call_count, 2)


if __name__ == "__main__":
    unittest.main()
