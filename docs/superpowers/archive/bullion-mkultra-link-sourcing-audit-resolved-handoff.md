# Bullion Mk Ultra — Link Sourcing Audit: Resolved (equit↔etf) — Session Handoff

**Written:** 2026-08-08 · **For:** whoever resumes this project next. This handoff closes out
the single open item the prior handoff left (`equit→etf`), plus a second citation problem
found while closing it (`etf→equit`). Both are now fully resolved with primary-source
verification, in both the audit report and the live map itself.

## Goal

The prior handoff (`bullion-mkultra-link-sourcing-audit-review-handoff.md`, 2026-08-07)
described one open item from the finished "Link Sourcing Audit" plan: row `equit→etf` in the
final report was marked `Unverifiable` because nobody could pin down the primary ICI document
behind "57% of equity-fund assets are index, up from 36% in 2016," and ici.org 403s automated
fetchers. This session closed that out — and, while re-checking the neighboring `etf→equit`
row's citation, found and fixed a second, unrelated problem (a cited source that turned out not
to discuss the claim at all).

- Prior handoff (read this first for full background): `docs/superpowers/bullion-mkultra-link-sourcing-audit-review-handoff.md`
- Plan: `docs/superpowers/plans/2026-08-07-bullion-mkultra-link-sourcing-audit.md`
- Spec: `docs/superpowers/specs/2026-08-07-bullion-mkultra-link-sourcing-audit-design.md`
- **Report (updated this session):** `docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md` — rows 255 (`equit→etf`) and 256 (`etf→equit`) both now `OK` (were both `Unverifiable`).
- **Live map (updated this session, UNCOMMITTED):** `bullion-live-map/bullion_mkultra.html`

## How to resume (do this first)

1. Confirm branch: `main`, up to date with `origin/main`. Run `git status` — you should see
   `bullion-live-map/bullion_mkultra.html` as **modified but not committed**. That's this
   session's work; nothing else should be dirty in tracked files.
2. Read the prior handoff (linked above) for why `equit→etf` was flagged in the first place —
   this handoff assumes that context and doesn't repeat it.
3. Read report rows 255 and 256 directly — the evidence notes there are the full, current
   record of what was verified and how; trust them over this handoff's summary.
4. **Immediate next action:** decide whether to commit the `bullion_mkultra.html` changes. It's
   currently sitting uncommitted. This repo's convention (see `git log --oneline -10`) is small,
   scoped commits prefixed `Mk Ultra: ...` — a fitting message would be something like
   `Mk Ultra: fix equit/etf node citations with verified ICI + FEDS sources`.

## Current state (active files)

**Branch:** `main`, clean except for one uncommitted tracked-file change.

**Files changed, UNCOMMITTED:**
- `bullion-live-map/bullion_mkultra.html` — three spots edited:
  - `etf` node's `expert` array (~line 1286-1289): now cites the verified 57% figure, the exact
    ICI release name/date, and FEDS 2018-060 (dropped the old bare "Source: ICI, Fed Financial
    Stability Report").
  - `equit→etf` link `stat` field (~line 1501): now cites the 57% figure + ICI Sept 2024 release
    + the separately-verified Fact Book trend series (19%→52%, 2010→2025).
  - `etf→equit` link `stat` field (~line 1502): now cites FEDS 2018-060 specifically (Section
    2.4, Table 4, "index-inclusion effects") — FEDS 2016-071 was removed, see below.
  - The `equit` node itself was **not** touched — this fix was scoped to `etf`'s side only.

**Files changed, untracked (per this plan's "never git add/commit" convention — see prior
handoff's "Not mine" section):**
- `docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md` — rows 255 and
  256 rewritten in place with full resolution evidence. This is still the authoritative final
  report; nothing else in it changed this session.

**⚠️ Traps:**
- `bullion-live-map/bullion_mk18.html` — a separate, older HTML file that
  `scripts/generate_narration.py`'s `SOURCE_HTML` and its test suite point at for narration-text
  sync. It still has the **old, stale** `etf` expert text ("Source: ICI, Fed Financial Stability
  Report"). **This was left deliberately un-synced** — the user explicitly said "mk18 there's no
  need to touch anymore" this session. Do not "fix" it without re-confirming that's still wanted;
  treat it as a frozen/deprecated snapshot, not a live artifact.
- Scratch PDFs downloaded during verification (ICI's Sept 2024 monthly release via Wayback
  Machine, the 2025 and 2026 ICI Fact Books, both FEDS papers) live in this session's ephemeral
  scratchpad, **not** in the repo. They will not persist. A future session re-verifying or
  re-deriving these numbers must re-download from the sources named in the report rows, not look
  for cached copies in the project.
- Johnny/Alfred narration audio was investigated (via a dedicated Explore-agent pass) and
  deliberately **not** touched — both personas' spoken scripts for `etf`/`equit` are pure
  mechanism/flavor text with zero stats or citations, so this citation fix required no audio
  regen. Don't assume a future citation change to these two nodes automatically needs the same —
  check `JOHNNY_SCRIPTS` and the node's `beginner` array first; only `expert` text and
  `LINKS.stat` changed here, and neither feeds narration.
- ici.org 403s automated fetchers (WebFetch, curl) but loads fine through a real Chrome browser
  session (claude-in-chrome) — this isn't a permanent access wall, just bot-detection. See
  memory `ici-org-access-and-sourcing.md` for the full pattern, including which sibling/related
  domains (icifactbook.org, federalreserve.gov) are NOT blocked and can be curl'd directly.

**Not mine — leave alone:** everything else under `docs/superpowers/` (other plans/specs/
handoffs for unrelated features — fieldnote-discoverability, identity-polish, etc.), and the
other tracked handoff files (`mk12-handoff.md`, `mkultra-spec2-brainstorm-handoff.md`,
`honesty-pass-handoff.md`, `mkultra-spec2-plan-handoff.md`) which stay in place per this
project's handoff-archiving convention (tracked files aren't moved).

## What has changed

- **Report row 255 (`equit→etf`): `Unverifiable` → `OK`.** Verified the "57%" figure by pulling
  ICI's Sept 2024 "Release: Active and Index Investing" (via a Wayback Machine snapshot — ici.org's
  live site only keeps the trailing ~14 months of these under stable URLs) and computing combined
  domestic+world equity index share directly from ICI's own published Active/Index total-net-assets
  table: (11,038.8 + 2,244.0) / (11,038.8 + 2,244.0 + 7,360.5 + 2,631.7) = **57.07%** — reproducing
  the disputed figure to the rounded point from primary data. Also downloaded and full-text-searched
  (via `pdftotext`) both the 2025 and 2026 ICI Investment Company Fact Books (fetched from
  icifactbook.org, a separate domain that is NOT behind ici.org's automated-fetcher block) and
  confirmed neither contains this equity-specific figure — closing off that dead end definitively
  rather than leaving it ambiguous. The "36% in 2016" baseline could not be independently
  re-derived (no Wayback Machine snapshot of ici.org's stats pages exists that far back under any
  URL pattern tried) and is **not** asserted anywhere in the live map text as a result — only the
  reproducible 57% figure and the separately-verified Fact Book trend (19% of long-term fund
  assets in 2010 → 52% in 2025) are cited.
- **Report row 256 (`etf→equit`): `Unverifiable` → `OK`.** The prior "Fed FSR" citation was
  already known wrong. Of the two FEDS staff-paper candidates the prior pass had surfaced, this
  session downloaded both directly from federalreserve.gov (not blocked) and checked their actual
  content: **FEDS 2018-060** ("The Shift from Active to Passive Investing: Potential Risks to
  Financial Stability?") has an entire subsection (2.4, plus Table 4) on "index-inclusion
  effects" — exactly the claimed mechanism (an asset added to an index sees valuation, volatility,
  and comovement effects as index-tracking flows move with it). **FEDS 2016-071** ("Mutual Fund
  Flows, Monetary Policy and Financial Stability") turned out to be a mismatch — full-text grep
  found zero occurrences of "passive," "index fund," or "comovement"; it's actually about
  monetary-policy-driven fund-flow dynamics and redemption/liquidity risk, an unrelated topic.
  It was removed as a citation everywhere (report row, link `stat`, node `expert` text).
- `bullion_mkultra.html` edited in the three spots listed above (uncommitted). All edits
  verified to parse as valid JS via targeted `node -e` + `eval()` checks on the specific extracted
  lines/objects (not a full-file parse — see Verification idioms below for why that's the right
  check here).

## What has failed / risks / caveats

- **Nothing has failed.**
- **UNVERIFIED (intentionally, and handled correctly):** the "36% in 2016" half of the original
  equit→etf claim was never confirmed against a primary source. This is not a loose end to chase
  — the live map text was deliberately written to omit it rather than assume it. If a future
  session is tempted to add a "...up from 36% in 2016" style clause anywhere in this project,
  treat it as a fresh unverified claim needing its own primary-source check, not something to
  inherit from this session's work or from secondary reporting.
- `bullion_mkultra.html` changes are **uncommitted**. This is the main actionable risk — decide
  and commit (or explicitly decide not to) before this thread of work is considered closed.
- This session did not re-audit the full 93-row report end-to-end — only rows 255/256 were
  touched. No other `Unverifiable`/"flag for discussion" rows are known to remain from this
  specific plan's output, but that's based on the prior handoff's characterization, not a fresh
  full re-scan this session.

## What's next (ordered)

1. Decide whether to commit `bullion-live-map/bullion_mkultra.html`. If yes, scope the commit to
   just this file, following the existing `Mk Ultra: ...` message convention (see `git log`).
2. No narration/audio regen needed for this change (confirmed above) — skip
   `regen_narration_v2.py` unless a future, separate change actually touches `JOHNNY_SCRIPTS` or
   a node's `beginner` array for `etf`/`equit`.
3. If someone later wants to sync `bullion_mk18.html`'s stale `etf` expert text to match, that
   was explicitly deferred this session per the user's direction — confirm it's still wanted
   before touching that file.

## Verification idioms used in this project (for the resuming session)

- ici.org blocks automated fetchers (WebFetch, curl → 403) but works fine via a real Chrome
  browser session (claude-in-chrome). For older editions of pages the live site has rolled past,
  use the Wayback Machine's CDX API (`web.archive.org/cdx/search/cdx?url=...&output=text`) to
  find snapshot timestamps rather than guessing archive.org URLs directly.
- icifactbook.org and federalreserve.gov are **not** behind that same block — `curl` works
  directly, and `pdftotext -layout` (via `brew install poppler`) extracts searchable text much
  faster than paging through Chrome's canvas-rendered PDF viewer, which the browser-automation
  extension can't read via `get_page_text`/`read_page`, and whose in-viewer find (Cmd+F) doesn't
  respond to scripted key events either.
- To verify a specific numeric claim against a primary source: download the actual document,
  extract full text, grep/compute the number yourself — don't trust a secondary paraphrase, and
  don't assume a plausible-sounding source title is the right one without checking its actual
  content. This session's FEDS 2016-071 near-miss (right format, right era, completely unrelated
  content) is the cautionary example for why the content check matters, not just the title match.
- To sanity-check a hand-edited JS object literal in `bullion_mkultra.html` without running the
  whole app: extract the specific line(s) with a small `node -e` script and `eval()` them in
  isolation (wrap in `[...]` for array-of-objects context, or `(...)` + strip a trailing comma for
  a single object). A naive full-file parse (splitting on `<script>` tags with regex) throws an
  unrelated false-positive ("Invalid regular expression: missing /") on this file — that's not a
  real syntax error, just a bad test harness; don't mistake it for actual breakage.
