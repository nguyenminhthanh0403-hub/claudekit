# Bullion Voice Narration — Two-Persona Toggle, Captions & Autoplay — Design

**Written:** 2026-07-31 · **Status:** approved, ready for `writing-plans`.

**Builds on / supersedes:** `2026-07-31-bullion-voice-british-swap-design.md` (v1) for
scope. v1's engine mechanics — `say -v "Jamie (Premium)"`, the `ffmpeg` conversion step,
fail-loud error handling for a missing voice — are unchanged and referenced here, not
repeated in full. What v1 called "no UI toggle, replaces the voice outright" is
superseded: this spec adds the toggle v1 explicitly ruled out, on top of the same engine
swap. Also formally supersedes the investigation in
`docs/superpowers/voice-narration-accent-debug-handoff.md` (moot — voice is being
replaced, not tuned).

## Goal

Ship two narration personas on top of the `say`-CLI British-voice engine from v1:
**Alfred**, a formal butler voice reading the existing factual node text (all 39 nodes,
unchanged from v1), and **Johnny**, a rocker persona with hand-written, deliberately
non-factual flavor text (piloted on 6 nodes). Add a global toggle, synced captions, and
session-scoped autoplay on first node-open.

## Personas

### Alfred (existing, unchanged from v1)

`say -v "Jamie (Premium)" -r 200`, reads the beginner-mode bullet text extracted from the
live `NODES` array, all 39 nodes. See v1 spec for full mechanics.

### Johnny (new, pilot)

Same voice/engine (`say -v "Jamie (Premium)"`), a slower/looser rate — **provisional
`-r 170`**, to be confirmed by ear the same way v1's `-r 200` was (generate a sample,
compare, adjust before locking in; this is an implementation-phase task, not resolved by
this spec). Reads **hand-written scripts**, not the page's factual text — a deliberate,
manually-maintained text source for this one persona only (Phase 1 eliminated manual text
maintenance for Alfred/the page copy; this reintroduces it on purpose for Johnny).

Pilot scope: the same 6 nodes as the project's original Chatterbox pilot — `fed`, `gold`,
`vix`, `sec`, `repo`, `yield` — so both personas cover identical nodes for a clean
first comparison. Not the 2 field-note links (`credit-equit`, `usd-oil`) — those stay
Alfred-only; see "Explicitly not building."

**Johnny's 6 pilot scripts** (final text, referencing Cyberpunk 2077's Johnny Silverhand
— rockerboy, anti-corpo, "choom"/"corpo"/"suits" register — applied to the actual
financial content of each node):

- **fed:** "They call it the Federal Reserve. I call it the biggest chrome-plated puppet
  show in the world — a room full of suits who print money out of thin air and decide who
  eats and who don't. Rates go up, rates go down, and every time some corpo uptown gets
  richer while the street picks up the tab. Keeps prices 'stable,' they say. Sure. Stable
  for them."
- **gold:** "Gold. Old-world chrome, choom — no batteries, no code, can't be hacked,
  can't be printed. When the suits panic and the dollar starts bleeding out, everybody
  runs for the shiny rock like it's the last exit off a burning highway. Ironic, right?
  Most advanced economy on the planet, and when it all goes sideways, we're back to
  digging up shiny metal."
- **vix:** "They call it the fear index. I call it the market's heart-rate monitor right
  before a flatline. Number's low, everybody's cruising, thinks the good times never end.
  Number spikes past thirty — that's panic, choom, suits sprinting for the exits, dumping
  everything, prices crashing like a bad cyberware job."
- **sec:** "SEC. Supposed to be the cops on the beat, keeping the corpos honest. Half the
  time they're a step behind, chasing paper trails after the damage's already done. But
  pull 'em out of the picture and it's open season — little guy's holding a busted
  contract while the suits count their cut."
- **repo:** "Repo market. Nobody talks about it 'cause it's boring — banks trading bonds
  for cash overnight, greasing the wheels so the whole system doesn't seize up. But pull
  that plug, choom, everything stops. No headlines, no warning — just the whole city
  going dark 'cause the wiring underneath finally gave out."
- **yield:** "Yield curve. Line on a chart nobody looks at till it flips upside down —
  then suddenly everybody's screaming recession. Funny thing about the future: it's
  usually cheaper to borrow for than the present. When that flips, smart money thinks
  tomorrow's rough. Pay attention when it inverts, choom. The suits sure do."

## Toggle: global switch, header, `localStorage`-persisted

One button in the header toolbar (`#stage`'s preceding control row, alongside the
existing `#mode-toggle-btn` "⚙ Tools" / `#live-toggle-btn` "Live Data" buttons):
`#persona-toggle-btn`, e.g. label "🎙 Alfred" / "🎸 Johnny", toggles on click.

- State stored in `localStorage['bullion-narration-persona']`, value `'alfred'` |
  `'johnny'`. Default (key absent): `'alfred'`.
- Applies **site-wide**, both `bullion_mk18.html` and `bullion_mkultra.html` (same
  duplication pattern as every prior narration change — no shared JS module between the
  two files today).
- Switching mid-playback does not interrupt audio already playing; it only affects the
  next `playNarration()` call (manual click or next autoplay).
- **Fallback when Johnny selected but the open node has no Johnny clip** (33 of 39
  nodes): silently play Alfred's clip for that node instead. The caption reflects
  whichever persona is actually speaking (`ALFRED:`), not the toggle's nominal state —
  avoids a caption/audio mismatch.

## Captions

A caption line in the detail panel (new `#detail-caption` element, inside `#detail-body`,
hidden when nothing is playing), labeled `ALFRED:` or `JOHNNY:` per the persona actually
speaking (see fallback rule above), with words revealed in sync using **estimated
character-count-proportional timing**: split the spoken text into words, allocate each
word a duration proportional to its character-count share of the total text, scaled
against the clip's real duration.

Real duration is read via the `Audio` element's `loadedmetadata` event (`audio.duration`)
at play time — **no manifest change needed**, no precomputed duration data. (True
word-level timing via `AVSpeechSynthesizer` boundary callbacks was spiked and is a
confirmed dead end for this voice on this system — see the prior handoff's reproduction
script; not reattempted here.)

## Autoplay: first open per session

Narration plays automatically the first time a node with a narration clip is opened,
**tracked in `sessionStorage`** (survives reloads within the same tab, unlike an
in-memory flag, but resets on a new tab/session) under a key like
`bullion-narration-autoplayed` (JSON array of node ids already autoplayed). Reopening the
same node later in the same session stays silent; the existing 🔊 `#detail-narrate`
button remains available for manual replay at any time. Autoplay always uses whichever
persona is currently toggled (with the same fallback rule as manual play).

## Generation script changes

`bullion-live-map/scripts/generate_narration.py`:

1. Add a hardcoded `JOHNNY_SCRIPTS` dict (node id → script text, the 6 strings above) —
   same pattern the original 6-node Alfred pilot used before Phase 1 externalized
   extraction to the DOM probe. Johnny stays hardcoded permanently; it is not extracted
   from `NODES`.
2. Extend `main()`'s generation loop: for each `JOHNNY_SCRIPTS` entry, shell out to
   `say -v "Jamie (Premium)" -r 170 -o <tmp>.aiff "<script>"` (rate provisional, see
   "Personas"), then the existing `ffmpeg -i <tmp>.aiff -codec:a libmp3lame -qscale:a 2
   <OUTPUT_DIR>/johnny-<id>.mp3` conversion — same as the Alfred `node-<id>.mp3` path,
   different output prefix.
3. Alfred's existing `node-<id>.mp3` generation for all 39 nodes is unchanged.
4. Fail-loud posture unchanged: missing voice still aborts with a non-zero exit; no
   silent fallback.

## Front-end changes (both `bullion_mk18.html` and `bullion_mkultra.html`)

- New `JOHNNY_MANIFEST` object literal (6 entries: id → `johnny-<id>.mp3`), separate from
  the existing `NARRATION_MANIFEST` (Alfred, 39 entries, untouched).
- `openDetail()`: resolve which manifest/file to use per the toggle + fallback rule
  above; drive autoplay (`sessionStorage` check) in addition to the existing
  `#detail-narrate` button wiring.
- `playNarration()`: extend to accept a persona label for the caption, wire up
  `#detail-caption` word-reveal timing keyed off `loadedmetadata`.
- New `#persona-toggle-btn` in the header toolbar, new `#detail-caption` element in the
  detail panel markup.

## Testing

- Extend `test_generate_narration.py` with a coverage/non-empty check for
  `JOHNNY_SCRIPTS` (all 6 pilot ids present, each a non-empty string) and a
  manifest-completeness check that every `JOHNNY_SCRIPTS` key has a corresponding
  generated `johnny-<id>.mp3`. **Not** a content-match-to-page-text check — divergence
  from the factual node text is Johnny's entire point.
- Existing Alfred/`NARRATION_MANIFEST` tests (extraction, 39-node completeness) are
  unchanged and continue to pass independent of this work.
- Manual, real Chrome (per this project's standing idiom — audible correctness is never
  automatable): toggle personas, confirm Alfred plays on all 39 nodes and Johnny plays on
  its 6 pilot nodes with the fallback correctly kicking in elsewhere; confirm captions
  stay in sync and the label matches the audio actually playing; confirm autoplay fires
  once per node per session and not on reopen; confirm 0 console errors.

## Explicitly not building

- Johnny clips for the 2 field-note links (`credit-equit`, `usd-oil`) — out of pilot
  scope; those stay Alfred-only.
- Expansion of Johnny beyond the 6 pilot nodes — a decision for after the pilot is heard,
  not part of this spec.
- Any persisted/precomputed audio-duration data in the manifest — durations are read live
  via `Audio.duration`.
- True word-level caption timing via native speech-synthesis APIs — confirmed dead end,
  not reattempted (see prior handoff).
- Any voice/persona beyond Alfred and Johnny, and no attempt to clone or approximate any
  real person's actual voice (a firm, previously-settled boundary — see prior handoff's
  "What has failed" section on the Keanu Reeves / Paul Bettany discussion).

## Risks / unverified

- **Johnny's `-r 170` is a first guess**, unconfirmed by ear — same status v1's `-r 200`
  had before the user heard it. Must be A/B'd against at least one alternative rate before
  locking in, using this project's standing verification idiom (`afplay`/Finder, never
  automatable).
- Character-count-proportional caption timing is an approximation, not frame-accurate —
  accepted trade-off given the confirmed dead end on true API timing; may look slightly
  off on words with unusual length-to-duration ratios (numbers, abbreviations). Acceptable
  per the user's prior sign-off on this fallback.
- `localStorage`/`sessionStorage` keys are new state surfaces for this static-HTML-only
  project (no prior narration state was persisted client-side) — low risk, but worth
  a sanity check that nothing else in either file collides with the same keys.
