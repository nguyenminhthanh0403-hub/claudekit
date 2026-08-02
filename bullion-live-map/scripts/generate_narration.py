#!/usr/bin/env python3
"""Generates narration MP3s for Alfred (butler, all 39 nodes, factual
on-page text extracted from bullion_mk18.html's live NODES array) and
Johnny (rocker, all 39 nodes, hand-written scripts hardcoded in this
file).

Alfred's content is generated via macOS's `say` CLI, then re-colored via a
ChatterboxVC voice-conversion pass blending in reference voices (see
build_blended_ref_dict).

Johnny is generated directly by ChatterboxTTS (native text-to-speech, not
voice conversion) from the hired voice actor's recording alone — no `say`
scaffold, no blending in Tom/Jamie/the user's voice. An earlier attempt at
TTS mode (cloning the user's own voice) was dropped after the cloned voice
carried the wrong accent; that problem did not reproduce with the actor's
recording as the reference, and TTS mode's exaggeration/cfg_weight controls
gave a genuinely more lively/bitter delivery than anything achievable by
recoloring a flat `say` reading, so Johnny moved to this mechanism."""
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
ALFRED_RATE = 213  # was 218; user review 2026-08-02: "Alfred is speaking too fast"

JOHNNY_EXAGGERATION = 0.8
JOHNNY_CFG_WEIGHT = 0.3
JOHNNY_TEMPO = 0.95  # ffmpeg atempo — ChatterboxTTS has no native rate control;
                     # was 0.9, raised per user review 2026-08-02 ("Johnny is
                     # speaking too slow").

# Loudness target for both personas' final encode — user review 2026-08-02:
# Johnny measured ~-32 LUFS integrated vs Alfred's ~-20 LUFS on 3 sample
# node pairs (fed/gold/vix), both around -2..-3 dBTP true peak. A fixed
# runtime gain multiplier was rejected (per-clip peak headroom varies too
# much — a gain closing the gap on "fed" would clip on "gold"/"vix");
# loudnorm is a true loudness normalizer with peak limiting, so it closes
# the gap correctly per-clip instead of by a single blanket number.
LOUDNORM_FILTER = "loudnorm=I=-20:TP=-2:LRA=7"

VOICE_SAMPLE_DIR = ROOT / "audio" / "voice_sample"
USER_VOICE_PATH = VOICE_SAMPLE_DIR / "user_voice.wav"
JAMIE_SAMPLE_PATH = VOICE_SAMPLE_DIR / "jamie_sample.wav"
ACTOR_SAMPLE_PATH = VOICE_SAMPLE_DIR / "actor_sample.wav"
VOICE_BLEND_REFERENCE_TEXT = (
    "This is a reference recording used only to capture this voice's tone "
    "and timbre for narration blending."
)

JOHNNY_SCRIPTS = {
    "sec": "SEC. Supposed to be the cops on the beat, keeping the corpos honest. Half the time they're a step behind, chasing paper trails after the damage's already done. But pull 'em out of the picture and it's open season — little guy's holding a busted contract while the suits count their cut.",
    "cftc": "CFTC. The badge that's supposed to police the derivatives grid — a market so big it makes the stock exchange look like a corner store. Six hundred trillion in notional paper changing hands, choom, more zeroes than anyone can actually picture. They watch the futures pits, split turf with the SEC on the weird hybrid stuff, and mostly show up after the fire's already out. Still better than nobody watching the wires.",
    "fdic": "FDIC. The only reason you don't lose your whole life savings when some banker gambles it away and loses. Insures your deposit up to a quarter million, backed by a fund the banks themselves pay into — corpo insurance for corpo mistakes. When a bank flatlines, these are the suits who show up Monday morning, hand you your money, and sell off the wreckage. Cold comfort, but it's the floor under the whole system.",
    "tsy": "US Treasury. Uncle Sam's credit card, and it's maxed at thirty-five trillion and climbing. Sells IOUs every week — bills, notes, bonds — and the interest rate on that paper is the baseline hum underneath every other rate in the system. Mortgages, corporate debt, your credit card APR, all of it takes its cue from what the government pays to borrow. World's biggest, most trusted debtor. Funny how that works.",
    "fed": "They call it the Federal Reserve. I call it the biggest chrome-plated puppet show in the world — a room full of suits who print money out of thin air and decide who eats and who don't. Rates go up, rates go down, and every time some corpo uptown gets richer while the street picks up the tab. Keeps prices 'stable,' they say. Sure. Stable for them.",
    "fomc": "FOMC. Twelve people in a room, eight times a year, deciding whether your mortgage gets cheaper or your savings account finally earns something. They call it data-dependent. I call it a dozen suits staring at spreadsheets and guessing, same as the rest of us, just with better seats. The whole market holds its breath waiting on a vote most people can't name a single member of.",
    "ffr": "Fed Funds Rate. One number, and it runs the whole grid — mortgages, car loans, credit cards, business loans, all of it tuned off this single dial the Fed turns eight times a year. Overnight rate banks charge each other, sure, but the ripple never stops there. Turn it up, everything downstream gets more expensive. Turn it down, cheap money everywhere. Simple knob, choom. Just wired to everything you own.",
    "banks": "Commercial banks. Where you park your paycheck and where they turn around and lend most of it right back out — that's not a side effect, that's the whole business, and most of the money in the world exists because of it. Works fine until everybody wants their cash back at once. Silicon Valley Bank found that out the hard way — forty-two billion gone in a day, gone before the suits even finished their coffee.",
    "dealers": "Primary Dealers. Two dozen big banks strong-armed into buying government bonds whether they want them or not, every single auction, no exceptions. Sounds like a favor to Uncle Sam — really it's the pipe the whole national debt gets pushed through into the market. Pipe gets narrow, yields spike, and suddenly borrowing costs more for everybody downstream. Nobody thinks about plumbing till it backs up.",
    "repo": "Repo market. Nobody talks about it 'cause it's boring — banks trading bonds for cash overnight, greasing the wheels so the whole system doesn't seize up. But pull that plug, choom, everything stops. No headlines, no warning — just the whole city going dark 'cause the wiring underneath finally gave out.",
    "mmf": "Money market funds. 'Safe as cash,' they tell you — six and a half trillion parked in stuff that's supposed to never break. 'Supposed to' is doing a lot of work in that sentence. One of these funds broke the buck in '08 and froze the whole short-term system solid. They're the quiet giant lending into repo every single night — pull that money out fast enough, and the lights start flickering everywhere else.",
    "hf": "Hedge funds. Suits playing with borrowed chips, four trillion and counting, betting big because somebody else's money makes the losses easier to swallow. Fine when it's calm — they grease the wheels, add a little liquidity. But when the trade goes bad and the margin calls hit, they all sell the same stuff at the same time, and calm turns into a stampede real fast. March 2020 taught that lesson loud.",
    "gse": "Fannie Mae and Freddie Mac. Zombie companies, choom — the government seized them in '08 and never let go, and they're still standing behind roughly half of every mortgage in this country. They buy up home loans, bundle 'em into bonds, and quietly keep the whole housing market from seizing up. Not private, not really public either. Just permanently on government life support, keeping your neighbor's mortgage rate sane.",
    "yield": "Yield curve. Line on a chart nobody looks at till it flips upside down — then suddenly everybody's screaming recession. Funny thing about the future: it's usually cheaper to borrow for than the present. When that flips, smart money thinks tomorrow's rough. Pay attention when it inverts, choom. The suits sure do.",
    "credit": "Credit markets. Ten trillion in corporate debt, the river businesses drink from to invest, hire, expand. Turn that river to a trickle — rates go up, spreads blow out — and hiring freezes, expansion stops, and the guy who was gonna get hired next quarter doesn't. Nobody riots over a widening spread. They just quietly don't get the job.",
    "equit": "Equity markets. Forty-five trillion parked in stocks, and every bit of it is a bet on tomorrow's profits discounted back to today. Crank up interest rates and that discount gets brutal — future money's worth less, so the whole market marks itself down. Same companies, same earnings, different math. Welcome to the casino where the house rules change every FOMC meeting.",
    "mbs": "Mortgage bond market. Twelve trillion in bundled-up home loans, and this — not the Fed's headline rate — is what actually decides what you pay for a house. Tracks the ten-year Treasury plus whatever spread the suits feel like charging that week. The Fed even owned a couple trillion of this stuff at the peak, propping up the whole housing complex from behind the curtain.",
    "tech": "Tech stocks. Prettiest targets on the grid when rates climb — all that value's sitting way out in the future, profits promised years down the line, and a higher discount rate guts long-dated promises hardest. Almost a third of the whole S&P is riding on this bet. Rates tick up half a point, and the most 'innovative' companies on the planet bleed the most.",
    "fins": "Financials. The banks, the lenders — the one sector actually rooting for higher rates, since they profit off the gap between what they pay you for deposits and what they charge everyone else for loans. Steepen that curve and their margins fatten right up. Funny how the house always finds an angle no matter which way the rates move.",
    "defn": "Defensive equities. Utilities, groceries, hospitals — the boring stuff nobody brags about owning, until the market gets scary and suddenly everybody wants a piece. Low beta, steady dividends, the financial equivalent of pulling the blinds and hiding indoors. Doesn't make you rich. Just keeps you from losing your shirt when everything else is bleeding.",
    "cpi": "Core CPI. Inflation with the noisy stuff stripped out — no food, no energy, just the sticky prices that don't bounce around month to month. Fed's got a two percent target burned into their brains, and every point this runs hot past that is another excuse to keep rates jacked up. Doesn't feel abstract when your grocery bill's the thing proving the number right.",
    "nfp": "Non-Farm Payrolls. First Friday of the month, one report, and it can swing the whole market before most people finish their coffee. Too many jobs added, and the suits start sweating inflation. Too few, and it's recession chatter by lunch. A hundred and fifty-some million people's paychecks, reduced to one headline number everybody trades off of.",
    "vix": "They call it the fear index. I call it the market's heart-rate monitor right before a flatline. Number's low, everybody's cruising, thinks the good times never end. Number spikes past thirty — that's panic, choom, suits sprinting for the exits, dumping everything, prices crashing like a bad cyberware job.",
    "usd": "US Dollar. Trade-weighted against six other currencies, and when it flexes, the whole planet feels it — cheaper for you to buy stuff from overseas, pricier for anyone trying to sell you something made here. Sixty percent of the world's reserves sit in this thing. Strong dollar sounds like a flex. Ask an exporter how it actually feels.",
    "dxy_fx": "Emerging market currencies. Poorer countries borrowed in dollars they don't print, and when the dollar rallies, that debt gets heavier without them spending a cent — five and a half trillion of exposure, just sitting there waiting for the exchange rate to turn against them. Ten percent dollar strength, roughly a point and a half off their GDP. Nobody in those countries voted for a Fed meeting, but they pay for it anyway.",
    "gold": "Gold. Old-world chrome, choom — no batteries, no code, can't be hacked, can't be printed. When the suits panic and the dollar starts bleeding out, everybody runs for the shiny rock like it's the last exit off a burning highway. Ironic, right? Most advanced economy on the planet, and when it all goes sideways, we're back to digging up shiny metal.",
    "oil": "Oil. WTI, the US benchmark — crude's in everything, plastic, shipping, the diesel in the truck that brought your groceries in. Ten bucks a barrel up, and headline inflation ticks up a few tenths almost automatically. OPEC+ controls close to half of global supply and can move that number with a phone call. Whole economy, downstream of a cartel's mood.",
    "china": "China. Second-biggest economy on the planet, still holding hundreds of billions in US debt even after cutting that pile down for years. When their growth slows, our exports feel it and commodities drop worldwide. And Taiwan's sitting right in the middle of it, making most of the world's cutting-edge chips — the kind that run everything from your phone to a missile guidance system. Geopolitics, wired straight into your motherboard.",
    "russia": "Russia. One invasion in 2022, and the fallout's still rattling energy markets worldwide — they controlled a real chunk of the planet's oil and gas, and when the sanctions hit, Europe scrambled for supply and prices spiked everywhere. Three hundred billion in frozen reserves, energy quietly rerouted to China and India instead. War doesn't stay contained to a map. It shows up in your heating bill.",
    "geo": "Global trade. The rulebook — WTO, tariffs, the whole tangled web that decides what crossing a border costs. Twenty-five trillion a year in goods moving around the planet, and when that breaks down — tariffs jacked up, supply chains snapped — prices climb everywhere, not just at the border. Post-COVID alone reportedly tacked a couple points onto global inflation. Nobody notices the rules until they get rewritten under you.",
    "deposits": "Bank deposits. Your checking account, your savings — feels like your money, sitting there. Legally, it's a debt the bank owes you, and most of the money that exists in this whole economy got created the moment some bank made a loan against it. Seventeen, eighteen trillion of it, insured up to a quarter million. Comforting number till everybody tries to pull it out at once, like Silicon Valley Bank found out.",
    "m2": "Money supply. M2 — cash, checking, savings, the whole spendable pool, twenty-one trillion deep. Grew forty percent in two years during the pandemic, then shrank for the first time since 1948. Print that much money that fast and inflation usually shows up to collect, sooner or later. The connection's loose, choom, but it's never really zero.",
    "mortgage": "Thirty-year mortgage rate. The single number that decides whether you buy a house or stay renting forever. Doesn't track the Fed directly — tracks the ten-year Treasury plus whatever spread the market's charging that week, and it peaked near eight percent not long ago. High enough, and everybody who already has a cheap rate just... doesn't move. Whole housing market frozen solid by people refusing to trade a good deal for a bad one.",
    "privcredit": "Private credit. Banks pulled back after '08, and these funds moved right into the gap — lending straight to mid-sized companies, no bank in the middle, one point six trillion and climbing. Illiquid, lightly regulated, marked to whatever model the fund feels like using that quarter. Insurers and pensions are the ones backing it. Never been through a real default cycle. Untested tech running live in production, choom.",
    "tbills": "T-Bills. Government IOUs that mature inside a year — the safest, most boring, most liquid dollar asset there is, six trillion of it forming the actual bedrock of the money market. Supply swings with the deficit and the debt-ceiling circus in Washington. Boring till it isn't. Everything else in this system is built assuming this stuff never breaks.",
    "options": "Listed options. Side bets on which way a stock or index moves — and here's the twist, choom, this IS where the VIX comes from. Every fear-index number you see starts as options pricing. Dealers hedge their exposure to all these contracts, and that hedging can amplify a market move or dampen it, depending which way the wind's blowing that week.",
    "etf": "ETFs. Baskets of stocks wrapped up and traded like a single share, and at this point most new investing money flows straight through them instead of picking stocks one at a time. Convenient, cheap, and it means concentrated flows can now move an entire index at once. Quiet machinery running most of the market's plumbing these days — nobody clocks it till a corner of it, like a high-yield bond ETF, seizes up.",
    "energy": "Energy sector. Oil and gas company stocks, rising and falling on nothing but the price of crude — about four percent of the S&P by weight, but when oil spikes, these stocks swing the hardest and the fastest. Half hedge, half bet: they're the one corner of the equity market that actually wins when everyone else's input costs are getting crushed.",
    "house": "Households. That's you, choom. Two-thirds of the whole economy, every quarter, riding on what you and everyone like you decides to spend. Mortgage rate ticks up, debt payments eat more of the paycheck, confidence wobbles — and suddenly the biggest number in GDP is just a few hundred million people deciding whether to buy the thing or not. Every policy in this whole map, eventually, is aimed at you.",
}

# Item 8 (2026-08-02 review): short flavor lines fired on the 10 scenario
# triggers (5 quick-shock buttons + 5 dropdown scenarios, all routed through
# the same triggerShock(type) in the HTML) and on the AI-analysis button —
# a second event-driven narration layer alongside the per-node one above.
# Deliberately generic (not data-dependent): the AI-analysis line always
# reads the same regardless of the numeric result, since there is no static
# audio file for every possible score.
EVENT_IDS = [
    "rate_hike", "vix_spike", "cpi_rise", "usd_shock", "bank_stress",
    "fiscal_stimulus", "fiscal_tightening", "geo_conflict", "trade_war",
    "deregulation", "ai_analysis",
]

EVENT_ALFRED_SCRIPTS = {
    "rate_hike": "Simulating a fifty basis point rate hike. Borrowing costs rise across the board, and long-duration assets like technology stocks take the hardest hit.",
    "vix_spike": "Simulating a volatility spike above thirty. Investors are fleeing risk for shelter in Treasuries, gold, and defensive stocks.",
    "cpi_rise": "Simulating inflation running hot. Markets are pricing in a more aggressive Federal Reserve well before any actual policy move.",
    "usd_shock": "Simulating a dollar surge. Global funding conditions tighten, squeezing anyone who borrows or buys in dollars.",
    "bank_stress": "Simulating a deposit run on a bank. Lending freezes as money rushes into Treasuries and money market funds.",
    "fiscal_stimulus": "Simulating deficit-funded government spending. Growth gets a boost, but heavier bond issuance pushes yields higher.",
    "fiscal_tightening": "Simulating an austerity or debt-ceiling standoff. Growth drags, and markets price in a political risk premium.",
    "geo_conflict": "Simulating a war or sanctions escalation. Oil supply is disrupted, energy prices spike, and capital rushes toward safe havens.",
    "trade_war": "Simulating new tariffs and a trade war. Import costs rise, and companies with global supply chains come under pressure.",
    "deregulation": "Simulating looser financial rules. Bank profits and lending expand now, at the cost of risk building up unseen.",
    "ai_analysis": "Running the analysis now. One moment, while current conditions are weighed against every driver on this map.",
}

EVENT_JOHNNY_SCRIPTS = {
    "rate_hike": "Rate hike, fifty basis points. Every loan in the country just got more expensive overnight, choom — and the tech stocks feel it worst, 'cause their whole story was cheap money.",
    "vix_spike": "Fear gauge just blew past thirty. Everybody's dumping the risky stuff and running for the shelters — gold, Treasuries, the boring stocks nobody brags about owning.",
    "cpi_rise": "Inflation's running hot again. Markets don't even wait for the Fed anymore, choom — they just price in the pain early.",
    "usd_shock": "Dollar's surging. Feels like a flex until you remember half the planet owes debt in the currency that just got more expensive to pay back.",
    "bank_stress": "Depositors are running for the exits. Lending freezes solid, and the money's already halfway into a Treasury bill before the bank even opens Monday.",
    "fiscal_stimulus": "Government's spending borrowed money again. Growth gets a jolt, but somebody's gotta buy all those new bonds — and that somebody wants a higher rate for the trouble.",
    "fiscal_tightening": "Debt ceiling standoff, choom. Washington plays chicken with the full faith and credit of the whole system, and the market prices in the stupidity.",
    "geo_conflict": "War's broken out, sanctions are flying. Oil supply gets choked, prices spike, and everybody's chrome runs for gold like it's the last exit off a burning highway.",
    "trade_war": "Tariffs just went up. Every company running a global supply chain just got a tax nobody voted for, and tech eats it worst.",
    "deregulation": "Rules just got looser. Banks get to run hotter, profits climb — and somewhere down the line, that's exactly the kind of slack that snaps.",
    "ai_analysis": "Running the numbers now, choom. Give it a second to weigh the whole grid.",
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


def synthesize(text, rate, output_mp3_path, vc, ref_dict):
    """Runs `say` at the given words-per-minute rate, converts the result
    through ChatterboxVC against the given (possibly blended) ref_dict, and
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

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_out_path),
             "-filter:a", LOUDNORM_FILTER,
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
    """Generates jamie_sample.wav via `say` if missing. user_voice.wav and
    actor_sample.wav are never generated here — they're real recordings,
    not something this script can produce; raises if either is absent."""
    VOICE_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    if not USER_VOICE_PATH.exists():
        raise RuntimeError(
            f"{USER_VOICE_PATH} is missing. This is a real recording of the "
            "user's voice, not something this script can generate."
        )
    if not ACTOR_SAMPLE_PATH.exists():
        raise RuntimeError(
            f"{ACTOR_SAMPLE_PATH} is missing. This is a real recording of "
            "the hired voice actor, not something this script can generate."
        )
    if not JAMIE_SAMPLE_PATH.exists():
        synthesize_reference_wav(SAY_VOICE, JAMIE_SAMPLE_PATH)


def load_vc_model():
    """Loads ChatterboxVC once. Expensive (real model weights) — callers
    should call this exactly once per script run and reuse the result."""
    from chatterbox.vc import ChatterboxVC
    return ChatterboxVC.from_pretrained(device="mps")


def load_tts_model():
    """Loads ChatterboxTTS once, for Johnny's direct text-to-speech
    generation. Expensive (real model weights) — callers should call this
    exactly once per script run and reuse the result."""
    from chatterbox.tts import ChatterboxTTS
    return ChatterboxTTS.from_pretrained(device="mps")


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
    spec's "Blend mechanism" section (corrected 2026-08-01). Used only for
    Alfred now — Johnny is generated directly by ChatterboxTTS, no blend."""
    import torch
    cache = {}
    for path in set(embedding_clip_paths) | {prompt_clip_path}:
        cache[path] = embed_reference_clip(vc, path)

    embeddings = torch.stack(
        [cache[path]["embedding"] for path in embedding_clip_paths], dim=0
    )
    blended_embedding = embeddings.mean(dim=0)
    prompt_dict = cache[prompt_clip_path]
    return {
        "prompt_token": prompt_dict["prompt_token"],
        "prompt_token_len": prompt_dict["prompt_token_len"],
        "prompt_feat": prompt_dict["prompt_feat"],
        "prompt_feat_len": prompt_dict["prompt_feat_len"],
        "embedding": blended_embedding,
    }


def alfred_ref_dict(vc):
    """Alfred's 2-way blend: Jamie (the content voice) + the user's own voice."""
    return build_blended_ref_dict(
        vc,
        embedding_clip_paths=[JAMIE_SAMPLE_PATH, USER_VOICE_PATH],
        prompt_clip_path=USER_VOICE_PATH,
    )


def convert_voice(vc, ref_dict, input_audio_path, output_wav_path):
    """Runs ChatterboxVC conversion against a pre-built (possibly blended)
    ref_dict and writes the result as a wav file."""
    import soundfile as sf
    vc.ref_dict = ref_dict
    wav = vc.generate(str(input_audio_path))
    sf.write(str(output_wav_path), wav.squeeze(0).cpu().numpy(), vc.sr)


def synthesize_johnny(text, output_mp3_path, tts):
    """Generates Johnny's line directly with ChatterboxTTS, using the hired
    voice actor's recording as the sole voice prompt (no `say` scaffold, no
    blending in Tom/Jamie/the user's voice), applies a JOHNNY_TEMPO time-stretch
    (pitch-preserved — ChatterboxTTS has no native rate control), then encodes
    to MP3 via ffmpeg. Fails loudly on any model or subprocess error — never
    falls back silently."""
    import torchaudio as ta
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    try:
        wav = tts.generate(
            text,
            audio_prompt_path=str(ACTOR_SAMPLE_PATH),
            exaggeration=JOHNNY_EXAGGERATION,
            cfg_weight=JOHNNY_CFG_WEIGHT,
        )
        ta.save(str(wav_path), wav, tts.sr)
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path),
             "-filter:a", f"atempo={JOHNNY_TEMPO},{LOUDNORM_FILTER}",
             "-codec:a", "libmp3lame", "-qscale:a", "2", str(output_mp3_path)],
            check=True,
        )
    finally:
        wav_path.unlink(missing_ok=True)


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
    # Verify the say voice is installed before generating anything
    if not _voice_installed(SAY_VOICE):
        raise RuntimeError(
            f'"{SAY_VOICE}" is not installed. System Settings -> Accessibility -> '
            "Spoken Content -> System Voice -> Manage Voices."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_reference_clips()

    print("Loading ChatterboxVC (first run downloads model weights)...")
    vc = load_vc_model()
    print("Building Alfred's blend (Jamie + user)...")
    alfred_dict = alfred_ref_dict(vc)
    print("Loading ChatterboxTTS for Johnny...")
    tts = load_tts_model()

    nodes = extract_node_texts(SOURCE_HTML)
    print(f"Extracted {len(nodes)} node texts from {SOURCE_HTML.name}")
    for node in nodes:
        out = OUTPUT_DIR / f"node-{node['id']}.mp3"
        synthesize(node["text"], ALFRED_RATE, out, vc, alfred_dict)
        print(f"wrote {out}")

    for node_id, script in JOHNNY_SCRIPTS.items():
        out = OUTPUT_DIR / f"johnny-{node_id}.mp3"
        synthesize_johnny(script, out, tts)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
