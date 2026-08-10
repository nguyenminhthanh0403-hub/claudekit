# Bullion Mk Ultra — Link Sourcing Audit (Phase 1: Research) — Design

## Problem

Raised mid-brainstorm on the field-note credibility bar (see
`docs/superpowers/specs/2026-08-07-bullion-mkultra-fieldnote-bar-design.md`, "Out of scope"): the
102 causal links in `bullion_mkultra.html` carry varying sourcing quality. A quick audit of the
data model found:

- **17 `measured`** links — fitted against FRED data (already covered by the field-note-bar work).
- **81 `directional`** links — theory-only, but most already cite a named institutional source in
  `stat` (FDIC, NY Fed, BIS, OFR, ICI, etc.).
- **4 `unverified`** links — explicitly admit the gap in their own text (*"No named dataset behind
  the uncertainty-premium claim,"* *"'Industry estimates' names no dataset,"* etc.).

The project is already unusually self-critical about this — one `directional` link
(`vix→repo`) logs an internal conflict between its stated sign and a weak fitted result rather
than hiding it. This project's goal is a **full-corpus rigor pass**: audit sourcing across all 102
links, not just the 4 that already admit weakness, checking whether the 81 "directional" citations
are still correctly cited and accurate, not only whether the 4 unverified ones can be fixed.

## Decision: this spec covers research only, not edits

Research (checking a citation, checking a mechanism claim against a definition) is read-only and
fully reversible. Editing live financial claims on a public page is not, and 102 links' worth of
findings shouldn't all be pre-judged for action before anyone has seen them. This spec scopes
**Phase 1: audit and report** only. A second, separate brainstorm/spec will scope **Phase 2:
which findings to act on and how** (update `stat` text, promote/demote a `conf` tier, spin off a
new field note, or leave as-is) once the report exists to react to.

## Source hierarchy

Government and central-bank primary sources — FRED, Treasury (TIC data), FDIC, Federal Reserve
(H.8, FSR), NY Fed, BIS, SEC, IMF, OFR, ICI, EIA, WGC, BLS, CBOE, and similar — are the standard a
claim must check out against, matching how the existing `directional` links already cite these
directly. Wikipedia and standard textbooks are used only to orient quickly on a mechanism or
locate the relevant primary source faster; neither is cited as the final authority in the report's
verdicts or in any text that would eventually ship.

## Verdict schema (one row per link in the report)

| Field | Values | What it checks |
|---|---|---|
| Citation validity | OK / Stale / Unverifiable / N/A | Does the named source actually support the specific number/claim in `stat`? (N/A for links with no citation to check.) |
| Mechanism accuracy | OK / Questionable / Incorrect | Is the causal claim in `why` correct per standard definitions, independent of whether any dataset backs it? |
| Currency | OK / Stale-but-historically-fine / Stale-misleading | Fixed historical facts (e.g. "SVB was ~94% uninsured") don't go stale. A stat presented as current-state when it's actually dated does. |
| Suggested action | none / update stat text / field-note candidate / reconsider confidence tier / flag for discussion | A flag for Phase 2 to weigh — this phase doesn't decide, only surfaces. |
| Evidence note | free text, 1-2 sentences | What was found, with enough detail for Phase 2 to act without re-researching. |

## Batching

The 16 existing code-comment sections in the `LINKS` array (monetary policy spine, sovereign/
fiscal, commercial banking, shadow/non-bank, regulators, capital markets, equity sectors,
sentiment, economic data → policy, FX/dollar, commodities, geopolitics, money & deposits,
mortgage rates, private credit, breadth links) vary from ~2 to ~10 links each. Adjacent small
sections get grouped so each research batch covers roughly 8-13 links from related sections
(shared institutions, related mechanisms) — approximately 8-10 batches total covering all 102
links, no link left unaudited and no link audited twice.

Each batch is dispatched to a `general-purpose` subagent (needs `WebSearch`/`WebFetch` and
multi-step reasoning — not a code-search task) with that batch's full `why`/`stat`/`note`/`conf`
text and a mandate to verify citations and mechanism claims per the hierarchy above, returning its
findings in the verdict schema.

## Report

All batch results are aggregated into a single markdown report:
`docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md` (new `reports/`
subdirectory, untracked like every other file in `docs/superpowers/`, per this project's standing
convention). Organized by the same 16 sections for readability, one table per section, one row per
link. No changes to `bullion_mkultra.html` happen as part of this phase.

## Out of scope

- Any edit to `bullion_mkultra.html` — Phase 2, not this spec.
- Deciding which findings matter enough to act on — Phase 2.
- Re-litigating the field-note credibility bar (already resolved separately).
- Sourcing quality for node `beginner`/`expert`/`breaks` text (node-level content) — this audit is
  scoped to link-level `why`/`stat`/`note` text only. A future audit could extend to nodes if this
  phase proves valuable.
