# Bullion Live-Data Pipeline Outage — Session Handoff

**Written:** 2026-08-04 · **For:** a fresh session implementing the approved pipeline-liveness alarm. The outage itself is FIXED, VERIFIED and LIVE — do not re-debug it. Your job is the two-layer alarm that stops it recurring silently.

## Goal

The daily data cron failed **15 runs out of 15** — from its first run on 2026-07-20 through 2026-08-03 — and nobody noticed for 15 days, because a dead fetcher and a quiet one produced identical evidence. The outage is now fixed. What remains is making a stale pipeline *impossible to miss*, so the 15-day silence cannot repeat.

- Spec (approved, authoritative): `docs/superpowers/specs/2026-08-04-bullion-pipeline-liveness-alarm-design.md`
- Plan: **none yet — writing it is your first task.**
- Progress ledger: none for this effort (the outage fix was a single commit, not an SDD run).

## How to resume (do this first)

1. Confirm where you are: `git log --oneline -3` on `main` should show `1e4cf9f` (bot data commit) on top of `66e1802` (the outage fix).
2. Read the spec above in full. It is approved by the user; the design questions are settled — do not re-open them.
3. Invoke `superpowers:writing-plans` to turn the spec into an implementation plan. Brainstorming is **already complete**; do not re-run it.
4. **Immediate next action:** write the implementation plan from the spec, then implement Layer 1 (the map banner) before Layer 2 (the workflow alarm) — Layer 1 is self-contained and testable locally, Layer 2 needs live `workflow_dispatch` runs.

## Current state (active files)

**Branch:** `main`, pushed and up to date with `origin/main`. No feature branch — this project works directly on `main` by the user's standing choice.

**Files changed by the outage fix (committed in `66e1802`, pushed):**
- `.github/workflows/daily-data.yml` — key step now reads `${{ secrets.FRED_API_KEY || secrets.FRED }}`
- `bullion-live-map/bullion_mk18.html` — `CADENCE_TOLERANCE_DAYS` gained `weekly: 10`
- `bullion-live-map/bullion_mkultra.html` — same one-line fix
- `bullion-live-map/tests/freshness_test.html` — now follows `index.html` to the current map instead of a hardcoded filename; weekly cases added
- `bullion-live-map/tests/test_freshness_parity.py` — **new**; browser-free Python↔JS parity guard

**Committed by the bot in `1e4cf9f`:** `bullion-live-map/data.json` — the first data file the automation has ever written.

**Files the alarm work will modify (untouched so far):**
- `bullion-live-map/bullion_mk18.html` — add `pipelineLiveness()` in a new `PIPELINE-LIVENESS-START/END` marker block beside the existing `FRESHNESS-VERDICT` block (~line 4695), plus the `#pipeline-alarm` bar
- `bullion-live-map/bullion_mkultra.html` — same changes
- `bullion-live-map/tests/freshness_test.html` — new cases; **the `FRESHNESS-VERDICT-START/END` and new marker comments are load-bearing, the test extracts code by them — never rename or remove them**
- `.github/workflows/daily-data.yml` — add `issues: write` permission and the alarm job

**Untracked spec/plan files:** `docs/superpowers/` is deliberately mostly untracked. `_config.yml` at repo root has `exclude: [docs/]`, so tracking a doc containing `{{` or `{%` no longer breaks the Pages build — but the convention of leaving them untracked stands unless the user says otherwise.

**Not mine — leave alone:** everything under `.agents/`, `.codex/`, `.claude/agents/`, `.claude/skills/finance-*`, `AGENTS.md`, `CLAUDE.md`, the `docs/superpowers/plans|specs` files from earlier efforts, and the two `audio/narration/.*_done.txt` markers.

## What has changed

- **`66e1802`** — fixed four stacked defects (detail below). Tests after: `python3 -m unittest discover -s tests` **44/44** (was 41), `python3 -m unittest test_calibrate` **33/33**, browser suite **51/51** (it now *runs* — it had been throwing).
- **`1e4cf9f`** — bot-written `data.json`, `generated_at 2026-08-04T09:41:38Z`, 23 fields, **0 flagged**. Verified live on Pages, and the deployed mk18 confirmed serving `weekly: 10`.
- **Repo secret `FRED` was overwritten** via the API with the user's working local key (they explicitly approved this). It is now valid.
- **New spec written** (untracked): the liveness-alarm design.

### The four defects, for context

1. Workflow read `secrets.FRED_API_KEY`; the secret is named `FRED`. **An unset GitHub secret expands to `""` rather than erroring**, so every run died at the key guard without reaching the fetch.
2. The `FRED` secret's *value* was also invalid — all 16 FRED series returned HTTP 400, which FRED uses for "api_key is not registered".
3. Mk17 added the `weekly` cadence to `fetch_bullion_data.py` but not to the copy inlined in the maps. A cadence missing from that table returns `'unknown'`, which the UI renders as **nothing** — so `fed_bs`/`mortgage_30y`/`nfci` could never be flagged. **This is why the map said "17 of 23" when the truth was 20.**
4. `tests/freshness_test.html` — the test that existed to catch #3 — fetched `bullion_mk11_constellation.html`, long since reduced to a redirect stub, so it threw `marker comments not found` instead of asserting.

## What has failed / risks / caveats

- **Nothing has failed.** All four defects are fixed, and every fix was verified end-to-end against the live site, not just locally.
- **UNVERIFIED:** nothing from the outage fix. The alarm design, by contrast, is **entirely unimplemented** — spec only, zero code.
- **Trap — the user is NOT watching the repo** (`/subscription` → 404). This is why 15 failure emails made no noise. The alarm issue must be **assigned** to the repo owner; assignment notifies regardless of watch state. Setting the user as watching is also part of the approved work and has **not been done yet**.
- **Trap — `unknown` must show the banner.** A data file with no `generated_at` renders the bar in distinct wording. Do not "tidy" this into silence; failing open into silence is the exact bug (#3) that caused the miscount.
- **Trap — `#pipeline-alarm[hidden]{display:none}` is required from the start.** An id-selector `display` rule beats the UA `[hidden]` rule; the Overview board already shipped this exact bug once.
- **Trap — frozen versions.** `bullion_mk11`–`mk17` are frozen byte-for-byte. Only `mk18` and `mkultra` get changes. Freeze-check before committing.
- **Decision carried forward, overriding the obvious approach:** SMTP email was considered and **rejected**. It needs credentials in a repo secret, reintroducing the exact silent-bad-secret class that caused this outage, with no alarm on the alarm. The GitHub-issue channel uses only `GITHUB_TOKEN`.
- **Why both layers, non-negotiable:** GitHub disables scheduled workflows after 60 days of repo inactivity. The workflow then never runs, never fails, and never emails — the issue alarm structurally cannot see this. Only the map banner would.
- **`data.json` commits daily even when no market data moved**, because `generated_at` is a timestamp so the file always differs. This is what makes it a reliable heartbeat — do not "optimise" that commit away, it is load-bearing for the 3-day tolerance.

## What's next (ordered)

1. `superpowers:writing-plans` against `docs/superpowers/specs/2026-08-04-bullion-pipeline-liveness-alarm-design.md`.
2. Implement Layer 1 in `bullion_mk18.html` + `bullion_mkultra.html`: `pipelineLiveness()` in its marker block, the `#pipeline-alarm` bar, wired into the `renderLiveBadge` call path.
3. Add the browser cases to `tests/freshness_test.html` (fresh / stale / at-tolerance / one-past / missing / unparseable, plus the four DOM assertions).
4. Implement Layer 2 in `.github/workflows/daily-data.yml`: `issues: write`, create-or-comment on failure with assignment, close on success.
5. Verify Layer 2 with a deliberately-broken `workflow_dispatch` run: issue created + assigned, second failure comments rather than duplicating, success closes it. **Restore the workflow afterward and confirm a clean green run.**
6. Set the user as watching the repo (`PUT /repos/{owner}/{repo}/subscription`, `{"subscribed": true}`).
7. Freeze-check mk11–mk17, run all three suites, commit, push, verify live on Pages.

## Verification idioms used in this project (for the resuming session)

- **Python tests:** `cd bullion-live-map && python3 -m unittest discover -s tests` (44/44) and `python3 -m unittest test_calibrate` (33/33).
- **Browser tests:** serve the folder (`python3 -m http.server 8901` from `bullion-live-map/`) — `file://` breaks `fetch`. Then drive headless Chrome via the `headless-chrome-verification` skill's `cdp_probe.mjs` template, poll `#out` until it stops saying `running…`. **Always isolate with `--user-data-dir`**; macOS has no `timeout` command.
- **GitHub API:** anonymous calls 403 even on this public repo. Use `TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill 2>/dev/null | sed -n 's/^password=//p')`, then `curl -H "Authorization: token $TOKEN" ...`, then `unset TOKEN`. **Never print the token.**
- **Did CI actually work?** Check `/actions/workflows/daily-data.yml/runs` for `conclusion`, and read the failing step's log at `/actions/jobs/{id}/logs`. A plausible-looking `data.json` proves nothing about whether the automation ran — that is the whole lesson of this outage.
- **Did a push reach Pages?** Trust `git show origin/main:<path>`; the Pages CDN caches ~5 min, so a stale live URL right after a push is normal. Confirm deployment via the Actions run list, not `curl -sI | grep last-modified` (a failed build leaves the old header in place indefinitely).
- **Freeze check:** `git diff --stat -- bullion-live-map/bullion_mk1[1-7].html` must be empty.
