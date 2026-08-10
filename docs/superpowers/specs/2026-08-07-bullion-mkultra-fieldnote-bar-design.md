# Bullion Mk Ultra — Field-Note Credibility Bar — Design

## Problem

The 2026-08-06 `/impeccable critique` of `bullion_mkultra.html` asked: *"The field notes are
the most human thing in the file — why only 2? What's the real bar for 'this link deserves a
field note,' and should it be lower?"* This was deferred out of the fieldnote-discoverability
pass (which only made the existing 2 notes visible; see
`docs/superpowers/bullion-mkultra-fieldnote-discoverability-handoff.md`) and is resolved here.

## Decision: credibility is the bar, not "was I originally wrong"

A field note is the creator's own first-person marginalia on a link — it only works if it reads
as a genuine, confident observation, not decorative copy or a hedge. Auditing every
`conf:'measured'` link (17 of 102) against the two existing notes shows the real filter already
operating implicitly: both existing notes sit on the two strongest sign-reversal findings in the
dataset. The two other links that reverse an original hand-coded sign the same way — and would be
the obvious candidates for "the bar was just too high" — turn out to be sitting right at the weak
end of statistical significance instead of being overlooked.

**Rule:** a link earns a field note when it tells a genuinely surprising, creator-voiced story —
either (a) *"the data reversed my original hand-coded guess"* or (b) *"this relationship isn't
the stable rule it looks like"* — **and** the underlying measured evidence is credible enough to
state with confidence: a non-trivial sample, and a fitted `|t|` well clear of the ~2 conventional
significance floor rather than sitting right on it. Weak or thin-sample findings don't get voiced
as a confident reversal, because doing so would overstate the evidence.

## Links evaluated and their verdicts

| Link | Story type | \|t\| | n | Verdict |
|---|---|---|---|---|
| `credit→equit` | hand-sign flip | 12.5 | 199 | has note (unchanged) |
| `usd→oil` | hand-sign flip | 4.7 | 198 | has note (unchanged) |
| `oil→equit` | regime-dependent sign | 5.1 | 198 | **new note (below)** |
| `vix→defn` | hand-sign flip | 2.0 | 199 | excluded — too weak |
| `mortgage→credit` | hand-sign flip | 2.0 | 40 | excluded — too weak, thin sample |
| `yield→equit` | regime-dependent, unstable | 2.0 | 197 | excluded — too weak; its own `stat` text already says "no stable coefficient" |

These are the only 6 links (of 102) whose existing `why`/`stat`/`note` text tells a
reversal-or-instability story at all; the other 11 measured links describe expected, unsurprising
relationships (e.g. `equit→tech` beta, `usd→gold` pricing) and were never candidates.

## New field note: `oil→equit`

Existing data already states the story — this only turns it into first-person voice, nothing
fabricated:

> `note:` *"Oil-equity correlation flips sign across regimes. Demand-led oil rallies often
> coincide with rising stocks."* … `stat:` *"Sign is regime-dependent (energy shock research), but
> the inverse sign shown here held over the fitted window."*

Drafted `fieldNote` text, matching the terse, honest voice of the two existing notes:

> "This inverse sign looks tidy, but I don't fully trust it — oil and equities flip correlation
> depending on whether a rally is demand-led or supply-led, and this fitted window just happened
> to land on the textbook side."

## Implementation footprint

1. Add the `fieldNote:'...'` string above to the `oil→equit` link object
   (`bullion_mkultra.html:1458`).
2. Add a code comment directly above `FIELDNOTE_NODE_IDS` (`bullion_mkultra.html:1538`)
   documenting the rule and listing the 3 excluded links with their `|t|`/n, so a future critique
   doesn't re-raise "why only N field notes" as an unexamined oversight.
3. Nothing else changes. `FIELDNOTE_NODE_IDS` is derived via
   `LINKS.forEach(l => { if (l.fieldNote) ... })`, and all three discoverability surfaces from the
   prior pass (board-card badge, 3D node-label badge, relationship-row badge) read from that same
   set — they pick up the new node/link automatically. No CSS, onboarding-copy, or badge-wiring
   changes are needed.

## Out of scope

- The source-reinforcement idea raised mid-brainstorm — validating/refining causal links against
  government sources, Wikipedia, and textbooks — is a separate, much larger research initiative.
  Explicitly deferred to its own future `superpowers:brainstorming` session, not folded into this
  spec.
- Any field notes beyond `oil→equit`. No other link in the dataset both tells a
  reversal/instability story and clears the credibility bar.
- Lowering the credibility threshold itself, or writing hedged/uncertain-toned notes for the 3
  excluded links.
