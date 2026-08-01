#!/usr/bin/env python3
"""Throwaway spike: tests adding the hired voice actor's reference recording
(`actor_sample.wav`) as a 4th embedding ingredient to Johnny's blend
(currently Tom (Enhanced) + user + Jamie (Premium), see generate_narration.py),
producing one comparison clip for a human listening test against the current
production `audio/narration/johnny-fed.mp3`. Not wired into production.

Run with .venv-narration/bin/python3, not plain python3 (needs torch/chatterbox).
"""
import soundfile as sf
import torch
from chatterbox.vc import ChatterboxVC, S3GEN_SR
import librosa
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE_SAMPLE_DIR = ROOT / "audio" / "voice_sample"
USER_VOICE_PATH = VOICE_SAMPLE_DIR / "user_voice.wav"
TOM_SAMPLE_PATH = VOICE_SAMPLE_DIR / "tom_sample.wav"
JAMIE_SAMPLE_PATH = VOICE_SAMPLE_DIR / "jamie_sample.wav"
ACTOR_SAMPLE_PATH = VOICE_SAMPLE_DIR / "actor_sample.wav"

JOHNNY_INPUT = ROOT / "audio" / "narration" / "johnny-fed.mp3"
OUTPUT_DIR = VOICE_SAMPLE_DIR / "spike_output"


def embed_clip(vc, wav_path):
    wav, _ = librosa.load(str(wav_path), sr=S3GEN_SR)
    wav = wav[: ChatterboxVC.DEC_COND_LEN]
    return vc.s3gen.embed_ref(wav, S3GEN_SR, device=vc.device)


def blended_ref_dict(vc, embedding_clip_paths, prompt_clip_path, weights=None):
    """weights: optional list aligned with embedding_clip_paths, normalized
    to sum to 1. Defaults to an equal-weight mean (original behavior)."""
    cache = {}
    for path in set(embedding_clip_paths) | {prompt_clip_path}:
        cache[path] = embed_clip(vc, path)
    embeddings = torch.stack(
        [cache[p]["embedding"] for p in embedding_clip_paths], dim=0
    )
    if weights is None:
        blended_embedding = embeddings.mean(dim=0)
    else:
        w = torch.tensor(weights, dtype=embeddings.dtype, device=embeddings.device).view(-1, *([1] * (embeddings.dim() - 1)))
        w = w / w.sum()
        blended_embedding = (embeddings * w).sum(dim=0)
    prompt_dict = cache[prompt_clip_path]
    return {
        "prompt_token": prompt_dict["prompt_token"],
        "prompt_token_len": prompt_dict["prompt_token_len"],
        "prompt_feat": prompt_dict["prompt_feat"],
        "prompt_feat_len": prompt_dict["prompt_feat_len"],
        "embedding": blended_embedding,
    }


def convert(vc, ref_dict, input_path, output_path):
    vc.ref_dict = ref_dict
    wav = vc.generate(str(input_path))
    sf.write(str(output_path), wav.squeeze(0).cpu().numpy(), S3GEN_SR)


def main():
    for path in (USER_VOICE_PATH, TOM_SAMPLE_PATH, JAMIE_SAMPLE_PATH, ACTOR_SAMPLE_PATH):
        if not path.exists():
            raise RuntimeError(f"{path} is missing.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading ChatterboxVC (first run downloads model weights)...")
    vc = ChatterboxVC.from_pretrained(device="mps")

    print("Building Johnny's 4-way blend (Tom + user + Jamie + actor, equal weight)...")
    johnny_4way_dict = blended_ref_dict(
        vc,
        embedding_clip_paths=[
            TOM_SAMPLE_PATH,
            USER_VOICE_PATH,
            JAMIE_SAMPLE_PATH,
            ACTOR_SAMPLE_PATH,
        ],
        prompt_clip_path=USER_VOICE_PATH,
    )
    out = OUTPUT_DIR / "johnny_actor_4way_spike.wav"
    convert(vc, johnny_4way_dict, JOHNNY_INPUT, out)
    print(f"wrote {out}")

    print("Building Johnny's 90/10 blend (actor 90%, Tom+user+Jamie share 10%)...")
    johnny_90_10_dict = blended_ref_dict(
        vc,
        embedding_clip_paths=[
            ACTOR_SAMPLE_PATH,
            TOM_SAMPLE_PATH,
            USER_VOICE_PATH,
            JAMIE_SAMPLE_PATH,
        ],
        prompt_clip_path=ACTOR_SAMPLE_PATH,
        weights=[0.90, 0.10 / 3, 0.10 / 3, 0.10 / 3],
    )
    out_90_10 = OUTPUT_DIR / "johnny_actor_90pct_spike.wav"
    convert(vc, johnny_90_10_dict, JOHNNY_INPUT, out_90_10)
    print(f"wrote {out_90_10}")

    print("\nCompare against current production Johnny voice:")
    print(f"  afplay {JOHNNY_INPUT}")
    print(f"  afplay {out}")
    print(f"  afplay {out_90_10}")


if __name__ == "__main__":
    main()
