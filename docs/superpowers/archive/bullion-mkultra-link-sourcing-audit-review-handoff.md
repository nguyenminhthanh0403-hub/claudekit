# Bullion Mk Ultra — Link Sourcing Audit: Review Follow-up — Session Handoff

**Written:** 2026-08-07 · **For:** whoever has direct ICI.org access (or an ICI subscription/
account) to pin down one unconfirmed primary-source citation. Everything else in this audit
is done; this is a single narrow loose end.

## Goal

The 10-task "Link Sourcing Audit" plan finished and already produced its final aggregated
report. This handoff is NOT about resuming that plan — it's about one specific citation this
review session could not verify despite real effort, and needs a human (or a session with
non-blocked web access) to close out.

- Plan: `docs/superpowers/plans/2026-08-07-bullion-mkultra-link-sourcing-audit.md`
- Spec: `docs/superpowers/specs/2026-08-07-bullion-mkultra-link-sourcing-audit-design.md`
- **Final deliverable (already complete):** `docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md`
  — 93 rows, 22 sections, row-count self-verified at the bottom of the file. This is the
  report users/future sessions should read, not any staging file (the staging files
  `.staging/batch-1.md` … `batch-9.md` no longer exist — the plan's own Task 10 deleted them
  after aggregating).

## How to resume (do this first)

1. Confirm you're on `main` — this whole effort is untracked by design (see "Not mine" below),
   so there's no branch to check out. `git log --oneline -5` just shows unrelated Mk Ultra UI
   commits; this audit never touches `bullion_mkultra.html`.
2. Open `docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md` and search
   for `equit→etf` (around line 255). Read that row's evidence note in full — it already
   documents everything below; this handoff just explains *why* it's phrased that way and what
   the actual immediate next action is.
3. **Immediate next action:** Log into `ici.org` directly (browser, not an automated fetcher —
   see Traps below) and find ICI's monthly **"Release: Active and Index Investing"** series
   (distinct from the annual Fact Book). Locate the **October 2024** edition specifically (or
   whichever edition is the true source of the "57% of equity-fund assets are index, up from
   36% in 2016" claim — October 2024 is the vintage cited by secondary reporting, unconfirmed).
   Confirm or refute the 57%/36% figures against that primary document, then edit the
   `equit→etf` row: change `Unverifiable` → `OK` (with the confirmed release cited by name/date)
   or leave as `Unverifiable`/downgrade further if the figure doesn't check out.

## Current state (active files)

**Branch:** `main`. This whole audit effort is **untracked** — confirmed via `git status`
showing every file under `docs/superpowers/` and `.superpowers/` as untracked noise, matching
the plan's explicit "Global Constraints" instruction to never `git add`/`git commit` anything
this plan produces. There is nothing to commit and no branch state to preserve.

**Files relevant to this handoff:**
- `docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md` — the finished,
  final report. Rows 255 (`equit→etf`) and 256 (`etf→equit`) are the two rows this handoff is
  about; both already carry `Unverifiable` / `flag for discussion` with a detailed evidence note
  explaining the correction and the open question.

**⚠️ Traps — files that look relevant but are stale or misleading:**
- `.superpowers/sdd/task-8-brief.md`, `task-8-report.md`, `progress.md` (top-level, no
  subfolder) — these are **leftover files from a completely different, older effort** ("Bullion
  Mk17 — Breadth of Live Data"). The `.superpowers/sdd/` top-level directory gets reused/
  overwritten across unrelated plans; its loose top-level files are NOT this audit's task 8.
  Do not read them expecting sourcing-audit content.
- The review package this session was originally handed
  (`.superpowers/sdd/2026-08-07-bullion-mkultra-link-sourcing-audit/task-8-review-package.md`)
  **no longer exists on disk** — it was a snapshot of batch-8's pre-aggregation state (Citation
  validity = `OK` for `equit→etf`, no correction yet). By the time this review dug into the
  claim, the plan's aggregation/correction pass had *already* independently caught the same
  problem and fixed it in the final report (see next section). If you go looking for that
  review-package file to re-derive what changed, it's gone — trust the final report + this
  handoff instead.
- ICI.org's own pages (`ici.org/research/stats/combined_active_index_*`, `ici.org/viewpoints`)
  return **HTTP 403** to automated fetchers (WebFetch and similar). This isn't a transient
  network issue — every attempt this session and apparently the prior correction pass both hit
  the same wall. A logged-in human browser session is the realistic way past it, not a retry.

**Not mine — leave alone:** everything else in the repo (Mk Ultra HTML/JS, narration audio,
other `docs/superpowers/*-handoff.md` files for unrelated features like fieldnote-discoverability
and identity-polish).

## What has changed

- Nothing was edited by this review session. This was a pure verification/QA pass over an
  already-produced deliverable — no code, no report edits.
- Independently confirmed (via WebSearch + direct PDF reads, not just trusting secondary
  claims) that the final report's `equit→etf` correction is right to have happened:
  - Downloaded and fully read ICI's actual **2025 Investment Company Fact Book Chapter 2**
    (US-Registered Investment Companies) and **Chapter 4** (US ETFs) end-to-end.
  - Neither chapter contains a "57% of equity-fund assets / 36% in 2016" figure. What Chapter 2
    actually has: index funds = 51% of *long-term* fund assets (year-end 2024, not equity-only);
    equity funds = 60% of *all* investment-company assets (different ratio entirely); index
    domestic equity funds = 18% of US stock market cap (different denominator again).
  - This independently corroborates the final report's evidence note, which had already reached
    the same conclusion via a separate investigation path (it found ICI's monthly "Active and
    Index Investing" release showing e.g. June 2026 domestic-equity-index share at 63.8% —
    a different data point than mine, same underlying fix).

## What has failed / risks / caveats

- **Nothing has failed** in the sense of broken code — this is a research/citation-audit
  project, not software.
- **UNVERIFIED (the actual open item):** the *specific* primary ICI document containing "57%
  of equity-fund assets are index, up from 36% in 2016" has never been located by any pass —
  not the original task-8 implementer, not the correction pass, not this review session. Every
  attempt guessed a URL (e.g. an October 2024 edition of the monthly release) that either 404'd
  or wasn't linkable from search results. The claim is very likely *true* (independently
  corroborated in direction and rough magnitude by the Fact Book's own 51%/60%/18% figures, plus
  the June 2026 monthly-release data point at 63.8%), but "likely true, exact source
  unconfirmed" is exactly why the row is `Unverifiable` rather than `OK` — this is a correct,
  intentional downgrade, not a mistake to silently accept and move past.
- A companion row, `etf→equit` (line 256, same report), has an analogous unresolved primary-
  source mismatch (a Fed FSR citation that couldn't be matched to an actual FSR section — the
  real match appears to be separate FEDS staff working papers instead). Lower priority than
  `equit→etf` since its mechanism/currency are unaffected either way, but worth the same kind of
  follow-up if someone is already doing ICI/Fed primary-source digging.
- Both `ici.org` and (less critically) some `federalreserve.gov` search paths are blocked to
  automated tools in this environment — don't burn time retrying WebFetch on ICI's own domain;
  it 403s reliably.

## What's next (ordered)

1. A human with ICI.org access (or logged-in browser session) confirms or refutes the 57%/36%
   `equit→etf` figure against the actual "Active and Index Investing" monthly release, October
   2024 edition or whichever edition is correct.
2. Update `docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md` row 255
   (`equit→etf`): either restore `Citation validity = OK` with the confirmed release cited by
   exact name and date, or leave `Unverifiable` if it can't be pinned down even with direct
   access, or downgrade further if the figure turns out not to check out at all.
3. (Lower priority, optional) Same treatment for row 256 (`etf→equit`)'s Fed FSR mismatch, if
   convenient while already in ICI/Fed primary-source mode.
4. No other follow-up needed — every other row in all 93 was spec-compliant (8-column schema,
   valid enums, no Wikipedia/textbook used as final authority) and the specific claims this
   review spot-checked independently (the `privcredit→credit` IMF GFSR staleness math, the
   `options→equit` OCC citation-validity judgment call) both held up under live re-verification.

## Verification idioms used in this project (for the resuming session)

- This is a documentation/research audit, not code — "verification" means re-deriving a cited
  number from the actual primary source (download the PDF/report, read it directly, don't trust
  a secondary paraphrase), the same way this session re-read ICI's Fact Book chapters directly
  via the Read tool rather than trusting WebFetch's lossy page-summary or a news aggregator.
- Row-count / schema completeness is self-checked at the bottom of the final report (the "Row
  count verification" table) — trust that table's Expected/Actual columns over re-counting by
  hand.
- If ICI.org 403s a fetch, that's expected and not worth retrying with a different query —
  it needs an actual browser session, not a smarter search term.
