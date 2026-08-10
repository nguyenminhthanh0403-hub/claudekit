# Bullion pipeline-liveness alarm — design

**Date:** 2026-08-04
**Status:** approved, not yet implemented
**Origin:** the post-mortem in `docs/superpowers/bullion-live-data-pipeline-outage-handoff.md`

## Problem

The daily data cron failed 15 times out of 15 — from its first run on 2026-07-20
through 2026-08-03 — and nobody noticed for 15 days. The map went on serving
data generated 2026-07-25 while looking healthy.

Nothing in the system distinguished "the fetcher ran and had nothing new to say"
from "the fetcher has been dead for two weeks". The signals that should have
carried that difference each failed independently:

- GitHub's scheduled-failure emails went nowhere useful; the repo owner is not
  watching the repo (`/subscription` → 404).
- The map's live badge reports *per-field publication age*, which answers "is
  this number old?" but never "is the fetcher alive?".
- The one place the map could have noticed — `generated_at` — was parsed into
  `BULLION_PROVENANCE.generatedAt` and used only to fill a snapshot field.

A stale pipeline must become impossible to miss, through a channel that does not
depend on a setting nobody remembers to check.

## Design

Two independent layers. Neither is redundant: they fail in different directions.

### Layer 1 — the map banner (catches stale data from any cause)

**`pipelineLiveness(generatedAt, nowISO, toleranceDays)`** — a pure function
placed beside `freshnessVerdict`, inside its own `PIPELINE-LIVENESS-START` /
`PIPELINE-LIVENESS-END` marker block so `tests/freshness_test.html` can extract
and unit-test it the same way it does `freshnessVerdict`.

Returns `{ state, ageDays }`:

| Condition | state | Banner |
|---|---|---|
| `generated_at` within tolerance | `fresh` | hidden |
| `generated_at` older than tolerance | `stale` | shown, with age and date |
| `generated_at` absent or unparseable | `unknown` | **shown**, distinct wording |

**Tolerance: 3 days.** The commit step writes `data.json` on every successful
run — `generated_at` is a timestamp, so the file always differs and always
commits, even on a day when no market data moved. That makes `generated_at` a
true daily heartbeat. Three days absorbs one missed run or a scheduled job
GitHub skipped under load, without concealing a real outage for a week.

**`unknown` shows the banner.** This is the direct lesson from the `weekly`
cadence bug: a missing key in `CADENCE_TOLERANCE_DAYS` returned `'unknown'`,
which the UI rendered as nothing, so three fields could never be flagged however
stale they got. A missing input must never fail open into silence. A data file
carrying no timestamp is a fault, not a reason to stay quiet.

**The bar** — `<div id="pipeline-alarm" hidden>` as the first child of `<body>`,
with `#pipeline-alarm[hidden]{display:none}` written in from the start. The
higher-specificity rule is not optional: the Overview board shipped with exactly
this bug, where an id-selector `display` rule beat the UA `[hidden]` rule and the
element rendered anyway. Rendered from the existing `renderLiveBadge` call path
so it updates wherever live status already updates.

Two suppression rules, both deliberate:

- **Hidden when live data is toggled off.** In simulated mode nothing on screen
  came from `data.json`, so "every number below is from Jul 25" would be false.
- **Shown regardless of the history date picker.** A dead pipeline is a fact
  about the file, not about which date is being viewed.

Applies to `bullion_mk18.html` and `bullion_mkultra.html`. Frozen versions
(mk11–mk17) are not touched.

### Layer 2 — the workflow alarm (catches a failing run, same day)

Added to `.github/workflows/daily-data.yml`, with `permissions:` extended to
include `issues: write`. Uses only the built-in `GITHUB_TOKEN` — no new secret,
nothing that can silently expire. Storing SMTP credentials was considered and
rejected: it would reintroduce the exact silent-bad-secret failure class this
whole outage came from, with no alarm on the alarm.

- **On failure**, look for an open issue labelled `pipeline-alarm`. If none
  exists, create one titled `Daily data fetch is failing`, **assigned to the repo
  owner**, with the run URL and failing step in the body. Assignment matters: an
  assigned issue notifies regardless of watch state, which is currently off.
- **If one is already open**, append a dated comment rather than opening a
  duplicate. Each failure comments, so a broken pipeline emails every day it
  stays broken instead of once.
- **On success**, if an alarm issue is open, close it with a recovery comment.
  Self-healing, so a stale open issue never becomes noise to be ignored.

### Why both

The issue alarm catches *the workflow ran and failed*. The banner catches *the
data is stale for any reason* — including the case the issue alarm structurally
cannot see: **GitHub disables scheduled workflows after 60 days of repository
inactivity.** The workflow then never runs, never fails, and never emails. Only
the banner would say anything.

## Testing

Browser cases in `tests/freshness_test.html`, extending the existing pattern:

- `pipelineLiveness` — fresh, stale, exactly at tolerance, one day past, missing
  timestamp, unparseable timestamp.
- DOM assertions — bar visible with a stale envelope, absent with a fresh one,
  absent when live data is toggled off, present with an envelope lacking
  `generated_at`.

The workflow alarm job is verified by `workflow_dispatch` against a deliberately
broken run, checking that the issue is created and assigned, that a second
failure comments rather than duplicating, and that a success closes it.

## Out of scope

- Replacing the existing per-field live badge. It answers a different question
  (*which* field is stale) and stays as is.
- Any SMTP/email channel beyond the GitHub issue (see rationale above).
- Backporting to frozen mk11–mk17.
