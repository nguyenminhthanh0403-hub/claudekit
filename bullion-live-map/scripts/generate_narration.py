#!/usr/bin/env python3
"""Phase 1: generates all 39 node narration MP3s in the user's cloned voice.
Text is extracted from bullion_mk18.html's live NODES array at generation
time (never hardcoded), so narration can't silently drift from the on-page
text the way a hand-copied dict could."""
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

ROOT = Path(__file__).resolve().parent.parent
VOICE_SAMPLE = ROOT / "audio" / "voice_sample" / "user_voice.wav"
OUTPUT_DIR = ROOT / "audio" / "narration"
SOURCE_HTML = ROOT / "bullion_mk18.html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

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
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Extracted JSON failed to parse: {e}")


def main():
    if not VOICE_SAMPLE.exists():
        sys.exit(f"Voice sample not found: {VOICE_SAMPLE}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    nodes = extract_node_texts(SOURCE_HTML)
    print(f"Extracted {len(nodes)} node texts from {SOURCE_HTML.name}")

    model = ChatterboxTTS.from_pretrained(device="cpu")

    for node in nodes:
        filename = f"node-{node['id']}.mp3"
        text = node["text"]
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
