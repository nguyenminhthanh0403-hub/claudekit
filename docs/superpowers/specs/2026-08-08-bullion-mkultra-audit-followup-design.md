# Bullion Mk Ultra — Link Sourcing Audit Follow-Up — Design

## Problem

The 2026-08-07 "Link Sourcing Audit" (`docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md`)
did full primary-source verification of all 93 live edges in `bullion_mkultra.html` and produced
findings — but the findings themselves were never applied. 20 rows carry an unresolved
`Suggested action`: 17 `update stat text`, 3 `flag for discussion`. This spec closes all 20 out.

This is explicitly **not** a new audit. It's implementation of research the audit already did —
almost every row's `Evidence note` already states the specific fix. No re-verification against
primary sources is in scope here except where noted below.

**Also fixing in passing:** the report's own roll-up table says `flag for discussion: 5`, but
only 3 rows in the body actually carry that verdict (`repo→hf`, `credit→equit`, `geo→credit`) —
a bookkeeping error in the audit's own summary, corrected as part of this pass.

## Scope: the 20 rows and their fixes

Only the `stat` field is touched on any row. No row's evidence note found the mechanism (`why`)
itself wrong — every one is a citation/currency/framing issue with the mechanism confirmed sound.
`note`/`fieldNote` fields are untouched.

| # | Section | Edge | Fix |
|---|---|---|---|
| 1 | Monetary policy spine | `fed→cpi` | "Fed research" is too vague to name as a checkable source. **No new specific paper is invented** (would violate this project's own citation-verification rule — see "Design decision" below); reword to honestly frame the 12–18 month transmission lag as a standard, widely-accepted monetary-policy stylized fact, without a false specific-paper citation. |
| 2 | Sovereign / fiscal | `tsy→yield` | Keep the ACM (Adrian-Crump-Moench) term-premium model citation (real, correct, standard tool) but add a caveat: the model measures term premium, it doesn't itself demonstrate that issuance drives it — that causal step is standard fixed-income economics, not something the cited model directly shows. No new specific study is invented. |
| 3 | Sovereign / fiscal | `tsy→dealers` | "25 dealers" → 26 (MUFG Securities Americas added Jan 2026, per Bloomberg). |
| 4 | Commercial banking | `fed→banks` | Soften "BTFP stopped the regional-bank run" → "helped stem" (First Republic still failed ~2 months after BTFP launched; Fed's own framing is "helped avert," not "stopped"). |
| 5 | Deposit flight (plumbing) | `mmf→banks` | "Roughly $1T" → tighten to the $875B–$960B range actually reported (FDIC: $874.1B to June 2023; Fed H.8: $960B, Apr 2022–Apr 2023). |
| 6 | Deposit flight (plumbing) | `ffr→banks` | "$515B" unrealized securities losses → $620.4B, and correct the quarter to Q4 2022 (FDIC Quarterly Banking Profile) — the $515B figure was Q1 2023's, mismatched to the wrong quarter. |
| 7 | Funding markets (plumbing) | `repo→hf` | **Resolved judgment call:** soften "precisely what broke the Treasury market in March 2020" → frames the basis-trade unwind as a key contributor rather than the sole cause (dash-for-cash and dealer SLR constraints also contributed, per BIS/OFR/Fed FSR). |
| 8 | Mortgage/agency channel (plumbing) | `gse→mbs` | "$12T" → note current total 1-4 family mortgage debt outstanding is $14.6T (2025, Fed/Statista) — the $12T FHFA testimony figure is dated by natural market growth, not error. |
| 9 | Who stands behind the backstops (plumbing) | `banks→fdic` | "$20B" attributed to FDIC → FDIC's own current estimate is $16.7B; the $20.4B figure traces to a June 2024 CBO report, not FDIC. Fix both the number and the attribution. |
| 10 | Capital markets | `credit→equit` | **Resolved judgment call:** soften "-0.7" → a range, roughly -0.5 to -0.7, wider in stress periods (2025 typical readings run -0.5 to -0.6; -0.7+ is a stress-period reading, not the norm). |
| 11 | Equity sectors | `ffr→tech` | No named source at all currently. Add one: FRED's DGS2 (2-Year Treasury Constant Maturity) series, and reframe the "~370bps" 2Y move to acknowledge it's window-dependent (audit found ~320bps to ~370-400bps depending on whether the yield trough or calendar year-open is used as baseline) rather than stating one precise figure as if unambiguous. |
| 12 | FX / dollar | `ffr→usd` | "Rose about 19% in 2022" is a mid-year-peak/YTD framing, not full-year — correct to the actual full calendar-year close-to-close change, ~9.4% (94.63 → 103.52), and note the underlying figure was picking up an intra-year peak, not sustained gains (Q4 gave back nearly 10%). |
| 13 | FX / dollar | `usd→dxy_fx` | Cited IMF WP/19/25 is real but is about a different topic (fuel-price competitiveness, not dollar/EM-GDP linkage). Swap to IMF WP/15/179 ("Collateral Damage: Dollar Strength and Emerging Markets' Growth") and adjust the magnitude from "~1.5%" to that paper's own finding (~1.9% EM GDP decline per 10% USD rise), since we're now citing a different paper's actual number. |
| 14 | Commodities | `oil→cpi` | "$10/bbl" framing only matches the underlying (IMF/Fed) literature's percentage-basis framing when oil is near $100/bbl; at today's ~$65-90/bbl range, add a note that the rule of thumb is percentage-based (~10% oil move ≈ 0.3-0.4pp CPI), with "$10/bbl" as an example at higher price levels rather than a fixed rule regardless of price. |
| 15 | Geopolitics | `china→tsy` | "~$780B" current China Treasury holdings → ~$659B (May 2026 TIC data, most recent available) — the $780B figure is now 12-16% stale. "$1.3T peak" (Nov 2013) stays as-is, already accurate. |
| 16 | Geopolitics | `china→oil` | "China drives a large share of marginal oil demand" is now stale per the same agencies cited (IEA): China was >60% of global oil-demand growth 2013-2023, but <20% of 2024's rise, with IEA now naming India as the country leading demand growth through the decade. Reword to reflect this shift rather than presenting China's dominance as current. |
| 17 | Geopolitics | `geo→cpi` | "1.5 to 2% added to global CPI" conflates several distinct estimates. Tighten to IMF WP 22/031's actual finding: supply disruptions added "about 1%" to **global core inflation** specifically in **2021** — fix both the number and the scope (core vs. headline, one year vs. a broader window). |
| 18 | Geopolitics | `geo→credit` | **Resolved judgment call:** add a citation to the Caldara & Iacoviello Geopolitical Risk (GPR) Index (policyuncertainty.com/gpr.html), stated honestly including its own counterintuitive finding — a 2025 study regressing GPR against credit spreads found a small average spread *decrease*, not increase, associated with a 1-SD GPR rise. This complicates rather than cleanly supports the edge's "uncertainty widens spreads" framing; state that complication rather than citing the index as if it simply confirms the claim. |
| 19 | Private credit (Mk13) | `privcredit→credit` | "$1.6 to 1.7T AUM" reads as current but is a mid-2023 IMF GFSR snapshot. Date it explicitly ("as of mid-2023") and note current (2026) industry estimates run well above $2T, heading toward ~$4T by 2030 (Moody's, Morgan Stanley), reflecting ~20%/year growth off the IMF base rather than a static figure. |
| 20 | Breadth links (Mk15) | `energy→equit` | "~4%" S&P 500 energy-sector weight → current (June 2026) weight is ~3.0%, per S&P DJI/FactSet — note the ~4% figure was accurate in the 2022-2023 post-Russia/Ukraine-shock window specifically, not as a standing baseline. |

## Design decision: no new unverified citations

Two rows (`fed→cpi`, `tsy→yield`) have evidence notes that suggest "naming a specific paper" as
the ideal fix, but neither the audit nor this spec has actually identified and verified a specific
correct paper for either. Inventing one now would repeat exactly the mistake this project's own
prior sessions have hard-learned to avoid (see `feedback-verify-dont-assume-node-citations`
memory, and this week's `etf→equit` fix, which replaced a wrong-but-plausible-sounding FEDS paper
only after actually downloading and content-checking it). For these 2 rows only, the fix is to
**stop asserting a specific citation** and instead honestly characterize the claim as a standard,
textbook/stylized-fact-level mechanism — not to fabricate a paper name to fill the gap. All other
18 rows use numbers, papers, or index names the audit itself already verified by direct inspection
(the same rigor the original audit applied), so adopting them here is safe.

## Process

1. Work the 20 rows in the table order above. For each: read the current `stat` field at its
   line in `bullion_mkultra.html`, apply the fix, verify with the same `node -e` + `eval()`
   isolation check used for today's `oil→equit` field-note edit and last session's `equit→etf`
   fix (a naive full-file parse false-positives on this file — not a real check here).
2. After all 20 `stat` edits are applied and verified, update the audit report
   (`docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md`) row by row:
   change `Suggested action` to `none` (or a short "resolved: ..." note) for all 20, and fix the
   roll-up table's `flag for discussion` count from 5 to 3.
3. One commit covering all 20 `bullion_mkultra.html` `stat` edits together, message themed
   `Mk Ultra: apply link-sourcing audit's 20 outstanding citation/currency fixes`. The report
   stays untracked, same as every prior session in this project.

## Out of scope

- Any row not in the 20-row table above (the other 73 audited rows were already `OK`/`none`).
- Re-auditing or re-verifying sources the audit already checked by direct inspection — this spec
  trusts the audit's own primary-source work, except for the 2 rows flagged above.
- Changing `why`, `note`, or `fieldNote` fields — no row's evidence note found the mechanism text
  itself wrong.
- The oil→equit field note (already shipped, uncommitted, earlier this session — separate work).
- The deferred "third voice" narration spec (explicitly out of scope for this session, per user
  direction).
