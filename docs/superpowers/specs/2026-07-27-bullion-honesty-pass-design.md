# Bullion — "Honesty Pass" Design (Spec 1 of 2)

**Date:** 2026-07-27
**Status:** COMPLETE — shipped as `bullion_mk18.html` + `bullion_mkultra.html`, pushed and live
(`ed18751`). Achieved coverage matches the target below exactly: **16 measured / 74 directional /
3 unverified** of 93 links, 0 untiered, 0 nodes without a source.
**Predecessor:** Mk17 (`bullion_mk17.html`, current shared map) and `bullion_mkultra.html` (3D fork, seeded from Mk15)
**Location:** `bullion-live-map/` in the `claudekit` repo.
**Implementation plan:** `docs/superpowers/plans/2026-07-27-bullion-honesty-pass.md`

## Goal

Make the map's self-reported trustworthiness true.

`provCoverage()` (`bullion_mkultra.html:3389`) tallies confidence over the graph with
`bump(l.conf || CONF.UNVERIFIED)`. **48 of the 93 runtime links carry no `conf:` field**, so the
Audit Log's coverage bar drops over half the graph into the red "unverified — set by feel; the sign
may be wrong" segment.

**The graph is 93 links, not 86.** Causal claims live in TWO arrays — `LINKS` (86 rows, `:1153`)
and `PLUMBING_LINKS` (16 rows, `:1088`) — merged at load by the `PLUMBING_LINKS.forEach` block
(`:1289`): each plumbing row either **supersedes** the `LINKS` row with the same `(s, t)` pair (9 of
them do) or is **appended** (7). Any analysis that reads `LINKS` alone grades 9 rows that never
reach the screen and misses 7 that do. Runtime tiers today: 21 measured, 24 directional, 48 absent. Every one of those links *does* carry a `stat:` citation string. The map is
defaming its own evidence base: a metadata gap, not an evidence gap, and today the coverage bar is
the most misleading number on the page.

The other 45 links already carry a tier (21 `measured`, 24 `directional`), so the convention exists
in the file and this pass extends it rather than inventing it. Note those values are **quoted string
literals** (`conf:'measured'`), not the `CONF.*` constants; new entries must match that form. Those
45 are themselves re-checked against the fit — a link asserting `measured` that the data does not
support gets demoted (`ffr→tbills` is one), otherwise the pass is only half honest.

**Target coverage after the pass: 16 measured / 74 directional / 3 unverified** of 93, against
today's 21 / 24 / 48. The 3 that stay unverified are `china→tsy` (TIC is monthly), `geo→credit` (no
free geopolitical-risk feed) and `hf→privcredit` ("industry estimates" names no dataset) — each with
its reason stated rather than just a verdict.

Since Mk17, `data.json` carries **23 fields across 366 days**, and 22 of 39 nodes bind to a live
field — so **37 of the 93 links have both endpoints backed by real data** and can be *fitted*
rather than asserted. Four of the six links flagged `aud:false` ("⚠ sign unverified") are among
them, so signs that were guesses can be settled from data. (Pairs resolving to the *same* field on
both ends — `fomc→ffr`, `tsy→yield`, `usd→dxy_fx` — are excluded: regressing a series on itself
always "fits" and proves nothing.)

**Non-goal — this is not the visual pass.** Beginner legibility, visual elevation, motion polish,
and the WebGL/CDN fallback are Spec 2, brainstormed separately. This spec buys the *numbers*; Spec
2 designs against numbers that are already correct.

## The tier model

| Tier | Rule |
|---|---|
| `MEASURED` | An OLS fit exists for this exact pair with \|t\| ≥ 2 on the 80% train split. Fitted slope + t stored on the link. |
| `DIRECTIONAL` | No fit (an endpoint lacks a live field, **or** the fit came back insignificant), but `stat:` names a real institution/dataset. Sign asserted from mechanism; no magnitude claimed. |
| `UNVERIFIED` | `stat:` names no source, or admits an unchecked window / unverified sign. Rendered dashed. |

**A failed fit is not proof a relationship is false.** `sec→equit` is structurally real and will
never produce a daily-frequency signal. An insignificant fit on a data-backed pair therefore stays
`DIRECTIONAL` (when sourced) and gains an honest note — *"tested on 366 days of daily changes; no
significant daily-frequency relationship (t=0.4)"*. The report says "no daily signal," never
"false." This follows the project's standing rule from Mk15.2 and Mk17: **no invented magnitudes.**

## Design decisions

**Where the work lands.** `bullion_mkultra.html` is a named variant and editable in place, so it is
the lab. `bullion_mk17.html` and every earlier version stay byte-frozen (they are shared links).
Once proven in Mk Ultra, `./release.sh 18` cuts `bullion_mk18.html` from Mk17 and the verification
data ports across. `release.sh` is numeric-only — named variants are never routed through it.

**Sign conflicts: data wins when strong.** Where a fitted sign contradicts the hand-set `sign:`,
a fit with \|t\| ≥ 2 flips the arrow and the flip is recorded for the Audit Log showing both the old
hand value and the fitted one. A weak fit keeps the hand sign and records a `PROV_CONFLICTS` entry.
Nothing changes silently, and the map stops drawing arrows the data disputes. No check of this kind
exists today — `validateProvenance()` cross-checks `NODE_ELASTICITY` against `LINKS` but never
checks either against the data.

**Confidence becomes a third visual channel.** The arcs already encode two things: colour = sign
(amplifies / dampens / conditional) and tube radius = strength `w`. Confidence takes opacity + dash,
so the three do not collide — measured solid and brightest, directional solid and softer,
unverified dashed. This *extends* the existing "dashed = unverified" convention rather than
replacing it, so Spec 2 can build on the language instead of undoing it.

**Node copy: date-stamp, and prefer the live reading.** The 8 nodes without a trailing `Source:`
line are not actually uncited — most claims carry inline attributions (`BLS: CES0000000001`,
`CBOE`, `BIS 2022`, `IIF 2023`, `IMF WP/19/25`, `WGC`, `IEA 2022`, `WTO 2023`, `PIIE`). Two real
problems sit underneath:

1. **Six genuinely uncited claims** — `gold`'s "near-zero long-run correlation to equities"; the
   DXY basket weights (ICE); `china`'s "~92% of sub-7nm chips"; `russia`'s "$300B reserves frozen"
   and the shadow-fleet claim; `geo`'s "1.5–2% added to global CPI".
2. **Staleness.** The hardcoded figures are anchored to 2022–2024 ("roughly 158M employed as of
   mid-2024", "$780B of Treasuries as of 2024", "1,037 tonnes in 2023"). A map whose identity is
   *daily-refreshed live data* carrying two-year-old hand-typed teaching figures is a worse honesty
   problem than a missing `Source:` line, and it rots further every month.

Fix: attribute the six, make every hardcoded figure explicitly as-of-dated (a dated figure is never
wrong, only old), and where a node binds to a live field, promote the **live reading** to the
primary number and demote the hand-typed figure to dated historical context. That makes 22 of the
39 nodes self-maintaining, since the daily Action keeps them current.

## Components

| Unit | Responsibility | Depends on |
|---|---|---|
| `calibrate.py` link pass | Fit the 39 data-backed link pairs; emit a LINKS section in `calibration_report.txt` | existing `fit_cell`, train split, weekend bridging |
| `LINKS[].conf` | Per-link confidence tier + fitted slope/t in `stat:` | the report above |
| `validateProvenance()` | Auto-demote any link claiming a tier with no source; record sign conflicts | `LINKS`, `ELASTICITY`, `NODE_ELASTICITY` |
| `buildLinkObjects()` | Render tier as opacity + dash; store `baseOpacity` per link object | `LINKS[].conf` |
| `NODE_LIVE_FIELD` (ported) | Bind nodes to live fields so detail copy can show a live reading | `data.json`, `openDetail` |

`NODE_LIVE_FIELD` / `LIVE_FIELD_LABEL` / `MK17_FMT` exist in `bullion_mk17.html:3219` but **not** in
Mk Ultra, so porting them is a prerequisite for the live-reading half of the node work, not a bonus.

## Testing

- **Python:** `python3 -m unittest discover -s tests` (baseline 41/41) and `python3 -m unittest
  test_calibrate` (baseline 11/11). New link-pass tests must assert the 39-pair candidate
  derivation, the t ≥ 2 promotion boundary, and that an insignificant fit is **not** promoted.
- **Client:** headless-Chrome probe asserting every link has a `conf`; `provCoverage()` segments sum
  to `total`; after `validateProvenance()` no link claims a tier with an empty source; the four
  calibratable `aud:false` links have resolved tiers; any sign flip appears in the flip log.
- **Visual:** the three arc tiers must read as distinct at rest, and a focus → clear-focus cycle
  must restore per-tier opacity rather than flattening it.
- **Freeze:** `shasum -a 256` on `bullion_mk15.html` (`ebfaaaf6…`), `bullion_mk16.html`
  (`ef9fbc55…`), `bullion_mk17.html` (`9989bee3…`) before and after — must be unchanged.

## Out of scope

Spec 2 territory: beginner legibility (progressive disclosure, jargon tooltips, guided tour), visual
elevation, motion polish, the WebGL/CDN blank-screen fallback to the 2D Overview board, vendoring
Three.js inline. Also deferred: porting Mk17's 6 calibrated `ELASTICITY` links and 22-cell metric
grid into Mk Ultra, and the `us10y→spx_pct` promotion question.
