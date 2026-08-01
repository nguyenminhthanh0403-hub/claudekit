#!/usr/bin/env python3
"""Generates narration MP3s via macOS's `say` CLI: Alfred (butler, all 39
nodes, factual on-page text extracted from bullion_mk18.html's live NODES
array) and Johnny (rocker, 6 pilot nodes, hand-written scripts hardcoded in
this file). Replaces the original Chatterbox voice-cloning engine, dropped
after the cloned voice was found to carry the wrong accent."""
import html
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "audio" / "narration"
SOURCE_HTML = ROOT / "bullion_mk18.html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SAY_VOICE = "Jamie (Premium)"
ALFRED_RATE = 240

JOHNNY_RATE = 225

TOM_VOICE = "Tom (Enhanced)"
VOICE_SAMPLE_DIR = ROOT / "audio" / "voice_sample"
USER_VOICE_PATH = VOICE_SAMPLE_DIR / "user_voice.wav"
TOM_SAMPLE_PATH = VOICE_SAMPLE_DIR / "tom_sample.wav"
JAMIE_SAMPLE_PATH = VOICE_SAMPLE_DIR / "jamie_sample.wav"
VOICE_BLEND_REFERENCE_TEXT = (
    "This is a reference recording used only to capture this voice's tone "
    "and timbre for narration blending."
)
JOHNNY_MEANNESS_PITCH_SHIFT_SEMITONES = -1.5

JOHNNY_SCRIPTS = {
    "fed": "They call it the Federal Reserve. I call it the biggest chrome-plated puppet show in the world — a room full of suits who print money out of thin air and decide who eats and who don't. Rates go up, rates go down, and every time some corpo uptown gets richer while the street picks up the tab. Keeps prices 'stable,' they say. Sure. Stable for them.",
    "gold": "Gold. Old-world chrome, choom — no batteries, no code, can't be hacked, can't be printed. When the suits panic and the dollar starts bleeding out, everybody runs for the shiny rock like it's the last exit off a burning highway. Ironic, right? Most advanced economy on the planet, and when it all goes sideways, we're back to digging up shiny metal.",
    "vix": "They call it the fear index. I call it the market's heart-rate monitor right before a flatline. Number's low, everybody's cruising, thinks the good times never end. Number spikes past thirty — that's panic, choom, suits sprinting for the exits, dumping everything, prices crashing like a bad cyberware job.",
    "sec": "SEC. Supposed to be the cops on the beat, keeping the corpos honest. Half the time they're a step behind, chasing paper trails after the damage's already done. But pull 'em out of the picture and it's open season — little guy's holding a busted contract while the suits count their cut.",
    "repo": "Repo market. Nobody talks about it 'cause it's boring — banks trading bonds for cash overnight, greasing the wheels so the whole system doesn't seize up. But pull that plug, choom, everything stops. No headlines, no warning — just the whole city going dark 'cause the wiring underneath finally gave out.",
    "yield": "Yield curve. Line on a chart nobody looks at till it flips upside down — then suddenly everybody's screaming recession. Funny thing about the future: it's usually cheaper to borrow for than the present. When that flips, smart money thinks tomorrow's rough. Pay attention when it inverts, choom. The suits sure do.",
}

PROBE_SCRIPT = (
    "<script>document.title = 'NODE_TEXT_JSON:' + "
    "JSON.stringify(NODES.map(function(n){"
    "return {id: n.id, text: n.beginner.join(' ')};"
    "}));</script>"
)

TITLE_RE = re.compile(r"<title>NODE_TEXT_JSON:(.*?)</title>", re.S)
DUMP_TIMEOUT = 45      # seconds to wait for the DOM dump (it normally lands in ~2s)
EXIT_GRACE = 1.0       # extra seconds to keep reading after Chrome exits


def extract_node_texts(html_path):
    """Injects a probe script before html_path's REAL closing </body> (there is
    a decoy </body> inside a JS string mid-file — must use rfind, never
    find), runs it in isolated headless Chrome, and returns the node list.
    Raises RuntimeError on any failure; never falls back to stale text.

    Note on the polling: `--dump-dom` writes the full DOM to stdout within a
    couple of seconds, but this Chrome build then hangs instead of exiting, so
    waiting on the process (subprocess.run) blocks forever. We therefore stream
    stdout to a file, poll it for the probe's title, and kill Chrome ourselves
    as soon as we have the payload."""
    html_text = html_path.read_text()
    idx = html_text.rfind("</body>")
    if idx == -1:
        raise RuntimeError(f"No </body> found in {html_path}")
    patched = html_text[:idx] + PROBE_SCRIPT + html_text[idx:]

    # ignore_cleanup_errors: Chrome may still be flushing profile files when we
    # kill it, which would otherwise make the temp-dir teardown raise.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        probe_html = tmp_path / "probe.html"
        probe_html.write_text(patched)
        user_data_dir = tmp_path / "chrome-profile"
        dump_path = tmp_path / "dom.html"
        err_path = tmp_path / "chrome-stderr.txt"

        command = [
            CHROME, "--headless=new", "--disable-gpu",
            f"--user-data-dir={user_data_dir}",
            "--virtual-time-budget=5000",
            "--dump-dom",
            f"file://{probe_html}",
        ]
        try:
            dump_file = dump_path.open("wb")
            err_file = err_path.open("wb")
            proc = subprocess.Popen(command, stdout=dump_file, stderr=err_file)
        except OSError as e:
            raise RuntimeError(f"Could not launch headless Chrome ({CHROME}): {e}")

        match = None
        deadline = time.monotonic() + DUMP_TIMEOUT
        exit_deadline = None
        try:
            while True:
                dumped = dump_path.read_bytes().decode("utf-8", "replace")
                match = TITLE_RE.search(dumped)
                if match:
                    break
                if "</html>" in dumped:
                    # The dump is complete and the marker is not in it — the
                    # probe failed. Fail now instead of waiting out the timeout.
                    break
                now = time.monotonic()
                if now > deadline:
                    break
                if proc.poll() is not None:
                    # Chrome exited on its own; read a little longer, then stop.
                    if exit_deadline is None:
                        exit_deadline = now + EXIT_GRACE
                    elif now > exit_deadline:
                        break
                time.sleep(0.25)
        finally:
            proc.kill()
            proc.wait()
            dump_file.close()
            err_file.close()

        if not match:
            stderr_tail = err_path.read_bytes().decode("utf-8", "replace")[-2000:]
            raise RuntimeError(
                "Probe script never ran or NODES was empty — no NODE_TEXT_JSON "
                f"title found in dumped DOM (chrome exit code: "
                f"{proc.returncode}). Chrome stderr:\n{stderr_tail}"
            )
        # Chrome's DOM serializer entity-escapes <title> content, so text
        # containing & < > or nbsp arrives as &amp; &lt; &gt; &nbsp; — and
        # still parses as valid JSON. Unescaping is what stops that from
        # silently corrupting narration text.
        try:
            return json.loads(html.unescape(match.group(1)))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Extracted JSON failed to parse: {e}")


def synthesize(text, rate, output_mp3_path, vc, ref_dict, pitch_shift_semitones=None):
    """Runs `say` at the given words-per-minute rate, converts the result
    through ChatterboxVC against the given (possibly blended) ref_dict,
    optionally pitch-shifts it (Johnny only, via pitch_shift_semitones), and
    encodes the final result to MP3 via ffmpeg. Fails loudly on any
    subprocess or model error — never falls back silently."""
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff_path = Path(tmp.name)
    wav_in_path = aiff_path.with_suffix(".in.wav")
    wav_out_path = aiff_path.with_suffix(".out.wav")
    try:
        try:
            subprocess.run(
                ["say", "-v", SAY_VOICE, "-r", str(rate), "-o", str(aiff_path), text],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f'`say -v "{SAY_VOICE}"` failed (exit {e.returncode}). Is the '
                f'"{SAY_VOICE}" voice installed? System Settings -> Accessibility -> '
                "Spoken Content -> System Voice -> Manage Voices."
            ) from e

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(aiff_path), str(wav_in_path)],
            check=True,
        )
        convert_voice(vc, ref_dict, wav_in_path, wav_out_path)
        if pitch_shift_semitones is not None:
            apply_johnny_meanness(wav_out_path)

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_out_path),
             "-codec:a", "libmp3lame", "-qscale:a", "2", str(output_mp3_path)],
            check=True,
        )
    finally:
        aiff_path.unlink(missing_ok=True)
        wav_in_path.unlink(missing_ok=True)
        wav_out_path.unlink(missing_ok=True)


def synthesize_reference_wav(voice_name, output_wav_path):
    """Generates a short reference clip for `voice_name` via `say`, used only
    to extract a speaker embedding for voice-conversion blending — never
    played directly. Fails loudly, same posture as synthesize()."""
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff_path = Path(tmp.name)
    try:
        try:
            subprocess.run(
                ["say", "-v", voice_name, "-o", str(aiff_path), VOICE_BLEND_REFERENCE_TEXT],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f'`say -v "{voice_name}"` failed (exit {e.returncode}) while '
                "generating a voice-blend reference clip."
            ) from e
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(aiff_path), str(output_wav_path)],
            check=True,
        )
    finally:
        aiff_path.unlink(missing_ok=True)


def ensure_reference_clips():
    """Generates tom_sample.wav / jamie_sample.wav via `say` if missing.
    user_voice.wav is never generated here — it's a real recording, not
    something this script can produce; raises if it's absent."""
    VOICE_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    if not USER_VOICE_PATH.exists():
        raise RuntimeError(
            f"{USER_VOICE_PATH} is missing. This is a real recording of the "
            "user's voice, not something this script can generate."
        )
    if not TOM_SAMPLE_PATH.exists():
        synthesize_reference_wav(TOM_VOICE, TOM_SAMPLE_PATH)
    if not JAMIE_SAMPLE_PATH.exists():
        synthesize_reference_wav(SAY_VOICE, JAMIE_SAMPLE_PATH)


def load_vc_model():
    """Loads ChatterboxVC once. Expensive (real model weights) — callers
    should call this exactly once per script run and reuse the result."""
    from chatterbox.vc import ChatterboxVC
    return ChatterboxVC.from_pretrained(device="mps")


def embed_reference_clip(vc, wav_path):
    """Extracts ChatterboxVC's conditioning dict for one reference clip,
    truncated to the model's DEC_COND_LEN the same way
    ChatterboxVC.set_target_voice() does internally."""
    import librosa
    from chatterbox.vc import ChatterboxVC, S3GEN_SR
    wav, _ = librosa.load(str(wav_path), sr=S3GEN_SR)
    wav = wav[: ChatterboxVC.DEC_COND_LEN]
    return vc.s3gen.embed_ref(wav, S3GEN_SR, device=vc.device)


def build_blended_ref_dict(vc, embedding_clip_paths, prompt_clip_path):
    """Averages the fixed-size speaker x-vector ('embedding') across
    embedding_clip_paths, but takes the variable-length acoustic prompt
    ('prompt_token'/'prompt_token_len'/'prompt_feat') from prompt_clip_path
    alone — averaging those across clips of different lengths would either
    shape-mismatch or blend unrelated spectrograms into mush. See the design
    spec's "Blend mechanism" section (corrected 2026-08-01)."""
    import torch
    cache = {}
    for path in set(embedding_clip_paths) | {prompt_clip_path}:
        cache[path] = embed_reference_clip(vc, path)

    embeddings = torch.stack(
        [cache[path]["embedding"] for path in embedding_clip_paths], dim=0
    )
    prompt_dict = cache[prompt_clip_path]
    return {
        "prompt_token": prompt_dict["prompt_token"],
        "prompt_token_len": prompt_dict["prompt_token_len"],
        "prompt_feat": prompt_dict["prompt_feat"],
        "prompt_feat_len": prompt_dict["prompt_feat_len"],
        "embedding": embeddings.mean(dim=0),
    }


def alfred_ref_dict(vc):
    """Alfred's 2-way blend: Jamie (the content voice) + the user's own voice."""
    return build_blended_ref_dict(
        vc,
        embedding_clip_paths=[JAMIE_SAMPLE_PATH, USER_VOICE_PATH],
        prompt_clip_path=USER_VOICE_PATH,
    )


def johnny_ref_dict(vc):
    """Johnny's 3-way blend: Tom + the user's own voice + Jamie."""
    return build_blended_ref_dict(
        vc,
        embedding_clip_paths=[TOM_SAMPLE_PATH, USER_VOICE_PATH, JAMIE_SAMPLE_PATH],
        prompt_clip_path=USER_VOICE_PATH,
    )


def convert_voice(vc, ref_dict, input_audio_path, output_wav_path):
    """Runs ChatterboxVC conversion against a pre-built (possibly blended)
    ref_dict and writes the result as a wav file."""
    import soundfile as sf
    vc.ref_dict = ref_dict
    wav = vc.generate(str(input_audio_path))
    sf.write(str(output_wav_path), wav.squeeze(0).cpu().numpy(), vc.sr)


def apply_johnny_meanness(wav_path):
    """In-place pitch-shift of a converted wav file by
    JOHNNY_MEANNESS_PITCH_SHIFT_SEMITONES, for a slightly harsher edge.
    Johnny-only — never called for Alfred's output. Validated by ear in the
    Task 1 spike; see the design spec's "Persona voice-color tweak"
    section."""
    import librosa
    import soundfile as sf
    y, sr = librosa.load(str(wav_path), sr=None)
    y_shifted = librosa.effects.pitch_shift(
        y, sr=sr, n_steps=JOHNNY_MEANNESS_PITCH_SHIFT_SEMITONES
    )
    sf.write(str(wav_path), y_shifted, sr)


def _voice_installed(voice_name):
    """Checks if a voice is installed by querying `say -v '?'`.
    Returns True if the voice is found, False otherwise.
    Raises RuntimeError if the query itself fails."""
    result = subprocess.run(
        ["say", "-v", "?"], capture_output=True, text=True, check=True
    )
    # Each line in the output starts with the voice name followed by space or tab
    for line in result.stdout.splitlines():
        if line.startswith(voice_name + " ") or line.startswith(voice_name + "\t"):
            return True
    return False


def main():
    # Verify both voices are installed before generating anything
    if not _voice_installed(SAY_VOICE):
        raise RuntimeError(
            f'"{SAY_VOICE}" is not installed. System Settings -> Accessibility -> '
            "Spoken Content -> System Voice -> Manage Voices."
        )
    if not _voice_installed(TOM_VOICE):
        raise RuntimeError(
            f'"{TOM_VOICE}" is not installed. System Settings -> Accessibility -> '
            "Spoken Content -> System Voice -> Manage Voices."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_reference_clips()

    print("Loading ChatterboxVC (first run downloads model weights)...")
    vc = load_vc_model()
    print("Building Alfred's blend (Jamie + user)...")
    alfred_dict = alfred_ref_dict(vc)
    print("Building Johnny's blend (Tom + user + Jamie)...")
    johnny_dict = johnny_ref_dict(vc)

    nodes = extract_node_texts(SOURCE_HTML)
    print(f"Extracted {len(nodes)} node texts from {SOURCE_HTML.name}")
    for node in nodes:
        out = OUTPUT_DIR / f"node-{node['id']}.mp3"
        synthesize(node["text"], ALFRED_RATE, out, vc, alfred_dict)
        print(f"wrote {out}")

    for node_id, script in JOHNNY_SCRIPTS.items():
        out = OUTPUT_DIR / f"johnny-{node_id}.mp3"
        synthesize(
            script, JOHNNY_RATE, out, vc, johnny_dict,
            pitch_shift_semitones=JOHNNY_MEANNESS_PITCH_SHIFT_SEMITONES,
        )
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
