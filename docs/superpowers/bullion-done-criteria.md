# Bullion Mk Ultra — Done Criteria

**Written:** 2026-09-25 · **Authority:** this file. Per the global workflow's stage 2, these are
the checkable statements of what "finished" means for Bullion. Refine stops when they are met.
Before this existed, Bullion had no finish line and absorbed polish sessions indefinitely
(start screen, nav redesign, orb docking, persona glow — all shipped, none of them *closing*
anything).

## The owner's four criteria, verbatim

1. It should serve as a good mind map/teaching tool for people who have minor understanding or
   greater understanding of macroeconomics.
2. It should be able to analyze the concurrent market using reputable sources and give its
   analysis based on how healthy the market is, what factors are being inflated, what is being
   manipulated.
3. Bullion should update continuously on current data (federal funds rate numbers, etc). The
   important numbers that drive the market should be written in a report and sent to me every
   day with the analysis.
4. Bullion should update on relevant news relating to these financial information.

## Made checkable

| # | Met when | Status |
|---|---|---|
| 1 | The stage-5 panel (3 questions, ≥3 people, at least one non-finance) reports they could follow a causal chain unaided and name one thing they learned. Not self-assessed. | **Infrastructure done, never tested.** 39 nodes, beginner/expert bullets, chain-reaction paths ≤3 hops. Nobody outside the owner has used it. |
| 2 | The five existing dimensions (Credit, Volatility, Equity valuation, Funding, Safe assets) each read tight or loose with their drivers explained per the bar below, and the panel can restate one in their own words. | **BUILT 2026-09-25, uncommitted.** Five rows render beneath the retained score, verified in headless Chrome. Still needs the stage-5 panel to actually close. |
| 3a | Data refreshes unattended and `generated_at` is never older than 48h on a market week. | **MET.** `daily-data.yml` cron `7 10 * * *`; 29 fields; verified fresh 2026-09-25T15:07Z. |
| 3b | A daily report of the driving numbers plus the analysis arrives on the owner's phone/inbox without the owner opening the site. | **NOT MET — does not exist.** No report generator, no delivery channel in this repo. |
| 4 | Headlines refresh unattended on market days and are scoped to the financial fields the map tracks. | **MET.** `news-hourly.yml` cron `11 13-21 * * 1-5`; 40 headlines, verified 2026-09-24T21:27Z. |

Two of four are already met and were met before this file existed. That is worth stating plainly:
the gap was never capability, it was that nothing recorded when a thing was done.

## Criterion 2 — LOCKED 2026-09-25 (option a), corrected against the live file

**Correction, 2026-09-25.** The framing this decision was first made under was wrong, taken from
the stale 2026-08-11 macro-engine descope handoff. Verified against `origin/main`:

- **Option (b) already shipped.** The PCA-weighted composite was the thing found inverted and
  disabled. It was *replaced* by a hierarchical equal-weighted composite over 7 fields in 5
  categories, each field z-scored against its own baseline and sign-aligned to a fixed stress
  convention. That is live. There is no open research question here.
- **The score is visible, not hidden.** `.health-score-row.hidden` exists in CSS but nothing ever
  applies the class. It is a PCA-era vestige. `runMacroAnalysis` sets `health-num`, `health-label`,
  and the colour bar on every run, and `buildMacroNarrative`'s first sentence prints the score.
- **Two links are `aud:false`, not three** (`china→tsy`, `geo→credit`). The earlier count included
  a comment line.
- **`BASELINE_STATS` is not stale by accident.** `annual-baseline-refresh.yml` regenerates it every
  Jan 1 with a `baseline-alarm` issue on failure. A 15yr/2yr baseline drifts slowly by design.

**What this means for the build.** The per-dimension read does not need to be authored. It is
already computed and then thrown away: `computeCompositeScore` returns `categoryContributions` (a
signed z per category, plus `fieldsUsed`, `fieldsMissing`, and a `measured`/`directional` tier) and
the only consumer is `leadingCategory`, used for one narrative clause. **The work is to stop
discarding it.**

**Dimensions are the five that already exist**, not a new taxonomy. Inventing a parallel set would
leave two competing category systems in one file:

| Dimension | Fields | Baseline window |
|---|---|---|
| Credit | `hy_oas`, `ig_oas` | 15 yr |
| Volatility | `vix` | 15 yr |
| Equity valuation | `spx` | **2 yr** |
| Funding | `fed_bs`, `rrp` | **2 yr** |
| Safe assets | `curve_slope` (10Y minus 2Y) | 15 yr |

That last column is the strongest argument for surfacing dimensions and does not depend on the
score being wrong: **averaging a 15-year-grounded read and a 2-year-grounded read into one number
hides the difference in how much each is actually known.** A per-dimension view can label it.

**"What is being inflated"** ships as the signed z per field against its own baseline. Deviation,
never accusation.

**"What is being manipulated"** ships as the administered-versus-market-set distinction. Note that
`data.json`'s `class` field is `"measured"` for all 29 fields and does **not** encode this — the
mapping is new work. The federal funds target is voted by committee, SOFR is market-set, RRP is a
policy facility. Factual and sourceable. No claims about intent.

### The explanation bar (owner requirement, 2026-09-25)

The analysis must go in depth on why each number is what it is and why it matters, while assuming
the reader has never studied this.

**Correction, 2026-09-25 (second pass).** The first version of this bar said the default view
carries "why it matters" and the **expert** view carries the depth. That is unbuildable as written:
`beginnerMode` is initialised `true` at line 2031 and **is never assigned anywhere else in the
file**. The 2026-09-18 nav simplification removed the Tools toggle, so all 39 nodes' `expert`
arrays are unreachable dead content on the live page. The comment at the old line 6614 admits it:
"until something re-exposes a toggle for it."

**What was built instead.** The depth goes inline, in the one view that exists, using the
`METRIC_GUIDE` structure the project already had (Mk9): *what it is*, *why it matters*, *how to
read the number*, plus a `Source:` line. That structure is already written at beginner reading
level, so it satisfies the bar without a second view. `METRIC_GUIDE` covered 3 of the 7 composite
fields (`vix`, `spx`, `curve_slope`); four new entries were added in the same voice for `hy_oas`,
`ig_oas`, `fed_bs` and `rrp`, and the seven relevant entries now carry a `field:` key so a
dimension row can look its own guide text up.

**Still true and still binding:** causal claims are read out of the audited link graph, never
authored fresh. The runtime graph is **93** links (`LINKS` after `PLUMBING_LINKS` merges into it at
load), not the 102 an earlier draft of this document claimed — that number counted both arrays
before the supersede-or-append merge.

**Open, not built:** re-exposing an expert toggle would revive 39 nodes of already-written cited
content for the "greater understanding" half of criterion 1. It is a nav change outside these
criteria, so per stage 4 it goes on the someday list rather than into this work.

### Met when

The stage-5 panel (the same three people as criterion 1, at least one with no finance background)
can each, for one flagged dimension, say **in their own words** why that number is where it is and
why it matters. Not self-assessed. One panel run closes criteria 1 and 2 together.

**Verification:** jsdom smoke test through the rendered DOM via `openDetail(node)`. Do not read
`NODES` or `LINKS` off `window` — they are top-level consts and read as `undefined`.

## What this does not authorize

Not a mandate to restart the composite health score, redesign the nav again, or add features not
listed above. Anything not on this list is an idea for the someday list, per stage 4.

## How Bullion ends

Released: tag a version, short changelog of what it does and does not do. Not buried — it works,
it is public, and it is the strongest thing in the portfolio.
