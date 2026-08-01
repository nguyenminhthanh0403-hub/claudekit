#!/usr/bin/env python3
"""Throwaway spike: validates the embedding-averaging voice-blend mechanism
before any of it is wired into generate_narration.py for real. Produces two
converted clips for a human listening test — see
docs/superpowers/specs/2026-08-01-bullion-thamie-voice-blend-design.md's
"Feasibility spike" section. Run with .venv-narration/bin/python3, not plain
python3 (needs torch/chatterbox, which are not installed for system python3).

Also validates Johnny's post-conversion "meaner" pitch-down (-1.5 semitones),
added after the user found the initial blend "not fully convincing" and asked
for more spite in Johnny's voice specifically — confirmed via a listening
test in the same session that produced the base blend spike (2026-08-01).
"""
import subprocess
import tempfile
from pathlib import Path

import librosa
import soundfile as sf
import torch
from chatterbox.vc import ChatterboxVC, S3GEN_SR

JOHNNY_MEANNESS_PITCH_SHIFT_SEMITONES = -1.5

ROOT = Path(__file__).resolve().parent.parent
VOICE_SAMPLE_DIR = ROOT / "audio" / "voice_sample"
USER_VOICE_PATH = VOICE_SAMPLE_DIR / "user_voice.wav"
TOM_SAMPLE_PATH = VOICE_SAMPLE_DIR / "tom_sample.wav"
JAMIE_SAMPLE_PATH = VOICE_SAMPLE_DIR / "jamie_sample.wav"
TOM_VOICE = "Tom (Enhanced)"
JAMIE_VOICE = "Jamie (Premium)"
REFERENCE_SENTENCE = (
    "This is a reference recording used only to capture this voice's tone "
    "and timbre for narration blending."
)

ALFRED_INPUT = ROOT / "audio" / "narration" / "node-fed.mp3"
JOHNNY_INPUT = ROOT / "audio" / "narration" / "johnny-fed.mp3"
OUTPUT_DIR = ROOT / "audio" / "voice_sample" / "spike_output"


def synthesize_reference_wav(voice_name, output_wav_path):
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff_path = Path(tmp.name)
    try:
        subprocess.run(
            ["say", "-v", voice_name, "-o", str(aiff_path), REFERENCE_SENTENCE],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(aiff_path), str(output_wav_path)],
            check=True,
        )
    finally:
        aiff_path.unlink(missing_ok=True)


def embed_clip(vc, wav_path):
    wav, _ = librosa.load(str(wav_path), sr=S3GEN_SR)
    wav = wav[: ChatterboxVC.DEC_COND_LEN]
    return vc.s3gen.embed_ref(wav, S3GEN_SR, device=vc.device)


def blended_ref_dict(vc, embedding_clip_paths, prompt_clip_path):
    cache = {}
    for path in set(embedding_clip_paths) | {prompt_clip_path}:
        cache[path] = embed_clip(vc, path)
    embeddings = torch.stack(
        [cache[p]["embedding"] for p in embedding_clip_paths], dim=0
    )
    prompt_dict = cache[prompt_clip_path]
    return {
        "prompt_token": prompt_dict["prompt_token"],
        "prompt_token_len": prompt_dict["prompt_token_len"],
        "prompt_feat": prompt_dict["prompt_feat"],
        "prompt_feat_len": prompt_dict["prompt_feat_len"],
        "embedding": embeddings.mean(dim=0),
    }


def convert(vc, ref_dict, input_path, output_path):
    vc.ref_dict = ref_dict
    wav = vc.generate(str(input_path))
    sf.write(str(output_path), wav.squeeze(0).cpu().numpy(), S3GEN_SR)


def apply_johnny_meanness(input_wav_path, output_wav_path):
    """Pitch-shifts a converted clip down by JOHNNY_MEANNESS_PITCH_SHIFT_SEMITONES
    for a slightly harsher edge. Johnny-only — Alfred's blend is unaffected."""
    y, sr = librosa.load(str(input_wav_path), sr=None)
    y_meaner = librosa.effects.pitch_shift(
        y, sr=sr, n_steps=JOHNNY_MEANNESS_PITCH_SHIFT_SEMITONES
    )
    sf.write(str(output_wav_path), y_meaner, sr)


def main():
    if not USER_VOICE_PATH.exists():
        raise RuntimeError(f"{USER_VOICE_PATH} is missing.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not TOM_SAMPLE_PATH.exists():
        print(f"Synthesizing {TOM_SAMPLE_PATH.name} via say -v \"{TOM_VOICE}\"...")
        synthesize_reference_wav(TOM_VOICE, TOM_SAMPLE_PATH)
    if not JAMIE_SAMPLE_PATH.exists():
        print(f"Synthesizing {JAMIE_SAMPLE_PATH.name} via say -v \"{JAMIE_VOICE}\"...")
        synthesize_reference_wav(JAMIE_VOICE, JAMIE_SAMPLE_PATH)

    print("Loading ChatterboxVC (first run downloads model weights)...")
    vc = ChatterboxVC.from_pretrained(device="mps")

    print("Building Alfred's 2-way blend (Jamie + user)...")
    alfred_dict = blended_ref_dict(
        vc,
        embedding_clip_paths=[JAMIE_SAMPLE_PATH, USER_VOICE_PATH],
        prompt_clip_path=USER_VOICE_PATH,
    )
    alfred_out = OUTPUT_DIR / "alfred_blend_spike.wav"
    convert(vc, alfred_dict, ALFRED_INPUT, alfred_out)
    print(f"wrote {alfred_out}")

    print("Building Johnny's 3-way blend (Tom + user + Jamie)...")
    johnny_dict = blended_ref_dict(
        vc,
        embedding_clip_paths=[TOM_SAMPLE_PATH, USER_VOICE_PATH, JAMIE_SAMPLE_PATH],
        prompt_clip_path=USER_VOICE_PATH,
    )
    johnny_out = OUTPUT_DIR / "johnny_blend_spike.wav"
    convert(vc, johnny_dict, JOHNNY_INPUT, johnny_out)
    print(f"wrote {johnny_out}")

    johnny_meaner_out = OUTPUT_DIR / "johnny_blend_spike_meaner.wav"
    apply_johnny_meanness(johnny_out, johnny_meaner_out)
    print(f"wrote {johnny_meaner_out}")

    print("\nListen to all three files, then report back:")
    print(f"  afplay {alfred_out}")
    print(f"  afplay {johnny_out}")
    print(f"  afplay {johnny_meaner_out}")


if __name__ == "__main__":
    main()
