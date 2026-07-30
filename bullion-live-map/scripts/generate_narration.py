#!/usr/bin/env python3
"""One-time offline generation of the 8 pilot narration MP3s, in the user's
cloned voice, for the Bullion voice-narration pilot. Texts below are
copy-pasted verbatim from the `beginner`/`fieldNote` fields in
bullion_mk18.html / bullion_mkultra.html as of 2026-07-30 — this script does
not read the HTML files, per the design spec's YAGNI call on a full-blown
extractor for 8 fixed strings."""
import subprocess
import sys
from pathlib import Path

import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

ROOT = Path(__file__).resolve().parent.parent
VOICE_SAMPLE = ROOT / "audio" / "voice_sample" / "user_voice.wav"
OUTPUT_DIR = ROOT / "audio" / "narration"

NARRATIONS = {
    "node-fed.mp3": (
        "The central bank that controls interest rates and money supply. "
        "It keeps prices stable, supports jobs, and lends as a last resort in crises."
    ),
    "node-gold.mp3": (
        "A 'safe haven' asset bought when people fear inflation or crashes. "
        "Its price often moves opposite to the dollar."
    ),
    "node-vix.mp3": (
        "The 'fear index', measuring how nervous options traders are. "
        "Above 30 signals panic and a rush out of stocks."
    ),
    "node-sec.mp3": (
        "The main watchdog for the stock market and public companies. "
        "Forces honest financial disclosure and punishes fraud and insider trading."
    ),
    "node-repo.mp3": (
        "The overnight market where banks and funds borrow cash using bonds as collateral. "
        "It is the plumbing of short-term funding, and the Fed steps in when it seizes."
    ),
    "node-yield.mp3": (
        "A chart of government borrowing rates across different time lengths. "
        "When short-term rates exceed long-term (inverted), recession risk rises."
    ),
    "link-credit-equit.mp3": (
        "I originally had wider credit spreads lifting stocks — which, looking back, "
        "never made sense. Once I actually measured it, spreads widening tracks equities "
        "falling, the way you’d expect."
    ),
    "link-usd-oil.mp3": (
        "I had this coded as dollar up → oil down — the textbook FX-pricing story "
        "everyone learns. The data disagreed. Over this window it’s actually positive. "
        "I’m leaving that in and telling you it’s weird rather than hiding it."
    ),
}


def main():
    if not VOICE_SAMPLE.exists():
        sys.exit(f"Voice sample not found: {VOICE_SAMPLE}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model = ChatterboxTTS.from_pretrained(device="cpu")

    for filename, text in NARRATIONS.items():
        wav_tmp = OUTPUT_DIR / (filename[:-4] + ".wav")
        mp3_out = OUTPUT_DIR / filename

        wav = model.generate(text, audio_prompt_path=str(VOICE_SAMPLE))
        ta.save(str(wav_tmp), wav, model.sr)

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_tmp), "-af", "afftdn=nf=-25",
             "-codec:a", "libmp3lame", "-qscale:a", "2", str(mp3_out)],
            check=True,
        )
        wav_tmp.unlink()
        print(f"wrote {mp3_out}")


if __name__ == "__main__":
    main()
