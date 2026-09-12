# Bullion Mk Ultra Brutalist Nav Redesign — Session Handoff

**Written:** 2026-09-12 · **For:** a fresh session that touches `bullion_mkultra.html`'s nav, CSS design tokens, or beginner-mode behavior next. This is a **closeout/reference record** — nothing is in progress, everything below shipped and is live. Read this before assuming any of the old (pre-2026-09-10) navy/gold/4-tab structure still applies; it doesn't.

## Goal

Two things landed this session, on `bullion-live-map/bullion_mkultra.html`:

1. **Fed rate-decision odds feature** (executed from a prior handoff — see "Files created/changed" below) — a Markets-tab card showing Kalshi/Polymarket market-implied FOMC odds.
2. **Whole-app visual + IA redesign** — the app's nav collapsed from 4 destinations (3D Map / Overview / Markets / a slide-out Tools drawer) to 3 top-level tabs (**Market**, **Analysis**, **Causal Link**), and the visual language moved from navy/gold/rounded-cards/emoji to a flat "brutalist" system: near-black background, a single red-orange `#ff3300` accent (gold reserved only for literal data), no border-radius, no gradients, an italic Greek Δ used both as a functional change-value prefix and as a faded background texture.

Both are done, reviewed, and pushed live. Authorities, for when either of these needs revisiting:
- Design spec: `docs/superpowers/specs/2026-09-09-bullion-mkultra-brutalist-nav-redesign-design.md`
- Implementation plan (amended mid-execution with Task 8b): `docs/superpowers/plans/2026-09-10-bullion-mkultra-brutalist-nav-redesign.md`
- Progress ledger: **deleted** — per `superpowers:subagent-driven-development`'s own convention, a plan's `.superpowers/sdd/<plan>/progress.md` workspace is removed once the final whole-branch review is clean and pushed. Trust `git log` and this handoff over any expectation that the ledger still exists.

## How to resume (do this first)

1. Confirm you're on `main`, in sync with `origin/main` — `git log --oneline -1` and `git log --oneline -1 origin/main` should match (`78ae07b` as of this writing). If they don't match, something has moved since this handoff was written; re-orient from `git log` before trusting anything else here.
2. If you're about to touch the nav/CSS again, read the **Design** section of the spec above in full first — it's the record of *why* every visual choice was made (Brutalist over two other directions shown side-by-side, the accent-color swap, the whole-app icon sweep, keeping the 3D map untouched as Causal Link's centerpiece), not just *what* changed.
3. If you're about to touch `beginnerMode`/`.adv-control` gating, read "What has changed" below first — this session tightened it back up after the redesign accidentally loosened it (see the beginner-mode entry).
4. **Immediate next action: none required.** This is a closed loop — the redesign is live and matches the approved design. The "What's next" section below lists optional, explicitly-deferred polish items only, none of them urgent or broken.

## Current state (active files)

**Branch:** `main`, pushed and in sync with `origin/main` at `78ae07b`.

**Files created / changed (spanning commits `7263bc3`..`78ae07b`, plus the earlier `4be6917`):**
- `bullion-live-map/bullion_mkultra.html` — every change described in this handoff lives here; no new files were created, this project's convention is one HTML file per map version.
- `docs/superpowers/specs/2026-09-09-bullion-mkultra-brutalist-nav-redesign-design.md` — the approved design record (commit `a980c4b`).
- `docs/superpowers/plans/2026-09-10-bullion-mkultra-brutalist-nav-redesign.md` — the implementation plan, amended in place (commit `6130993`) to add Task 8b when execution surfaced a real plan gap. Read this plan file's own "Amendment" note near the top before assuming the original 9-task structure is the whole story.

**Scratch workspace / traps:**
- ⚠️ The SDD ledger this whole execution was tracked against (`.superpowers/sdd/2026-09-10-bullion-mkultra-brutalist-nav-redesign/progress.md`) **no longer exists** — it was deleted after the final whole-branch review came back clean, per that skill's own "delete this plan's workspace" convention. Do not go looking for it; `git log` on the commit range above plus this handoff are the record now.
- ⚠️ Five untracked handoff-related files sitting in `docs/superpowers/` and `docs/superpowers/archive/` (`bullion-mkultra-data-source-enrichment-handoff.md`, `bullion-mkultra-imf-gold-reserves-handoff.md`, `bullion-mkultra-markets-tab-handoff.md` in `archive/`; `bullion-mkultra-news-categories-shipped-handoff.md` — see archiving note below — and this handoff's own predecessor, `bullion-rate-hike-probability-brainstorm-handoff.md`, both previously in `docs/superpowers/`) are leftovers from a **prior, unrelated session's** handoff-archiving pass. Not touched by this session's redesign work beyond the two archiving moves noted below.

**Not mine — leave alone:** `bullion_mk11.html` through `bullion_mk17.html` (frozen prototype versions, untouched), `fetch_bullion_data.py`/`fetch_bullion_news.py` (Python fetch pipeline — the redesign touched zero Python), `data.json`/`news.json` (bot-managed, regenerated daily).

## What has changed

- **Fed rate-decision odds** (commit `4be6917`): Markets-tab card showing Kalshi + Polymarket FOMC-decision odds, isolated fetch (a Kalshi/Polymarket outage can't block the rest of `data.json` from updating). Predates the redesign; its card got swept into the new visual system along with everything else in later commits.
- **9-task redesign + Task 8b** (commits `7263bc3`..`f08fd9c`): design tokens → emoji/icon sweep → 3-tab nav shell → Market tab restyle → Analysis tab (old drawer promoted to a real tab) → Causal Link 2D board restyle → Causal Link 3D chrome + control relocation → consistency pass → **Task 8b** (added mid-execution: the Analysis tab's *internal* content — health bar, scenario stats, glossary, chain-reaction cards, the "Run macro analysis" button — had never been restyled by any task, traced to the design spec's Phase 4 wording never saying "restyle" the way Phases 3/5 did).
- **Two real regressions caught by review, both fixed same-session, neither ever reached a user:**
  - A Task 2 emoji-removal edit silently replaced straight JS-string quotes with curly Unicode quotes in an unrelated `COACH` array entry — a parse-time `SyntaxError` that broke **all** page JS with zero console signal. Caught only because the next task's own click-through verification failed on a script that wouldn't parse. Fixed same-session (commit `1a72aa8`).
  - Task 1's `--border` token change (deliberately, from a near-invisible dark navy to pure white — that's the intended "hard rule line" look) exposed a pre-existing layout quirk: `.metrics-grid` has 9 cells in a 2-column layout, leaving one grid slot with no DOM element, which used to blend into the dark background and now rendered as a glaring white block. Fixed same-session (commit `e7adc50`), plus a stale `tests/freshness_test.html` fixture (still expecting emoji this redesign correctly removed) updated in the same commit.
- **Final whole-branch review's fix wave** (commit `6eaadb3`, following the mandatory review after all 10 tasks completed) — found and fixed several cross-task gaps no single task's narrow review could have caught: the spec's signature functional Δ device had landed on the Market tab only (Analysis tab's `.stat-delta`/`.manual-delta`/`.impact-val` had zero functional Δ); `#header` itself was never repointed to the new design tokens (still literally pre-redesign navy, visible on all 3 tabs 100% of the time); `.board-card.hub`'s CSS accent border never actually rendered (an inline JS style was silently winning — a false claim in the now-deleted ledger, corrected here); `#controls-drawer-btn` survived as a fully redundant 4th nav button undermining the redesign's own "4→3 destinations" goal (removed); tab/tabpanel ARIA metadata never followed the IA rename (added); several more navy/rounded leftovers on the Market tab's own news list and Fed-odds card.
- **Beginner-mode re-gating** (commit `78ae07b`, a user-requested follow-up after the final review): converting the old Tools drawer into the Analysis tab had silently loosened `beginnerMode`'s protection — a deleted force-close line meant a first-time visitor could reach the full analyst toolkit (node picker, chain tracer, manual drivers) one click away, where before it needed an explicit switch to advanced mode. The user was asked directly and said to restore the old protection level. Fixed by adding the app's own pre-existing `.adv-control` class to `#tab-analysis` — the same CSS-based gating mechanism (`#app.beginner-on .adv-control { display: none !important; }`) already used for every other advanced-only affordance, applied to one more element. Confirmed via grep before the fix that `#tab-analysis` is the *only* path that can trigger `showView('analysis')`, so this one-attribute change fully closes the gap.

## What has failed / risks / caveats

**Nothing has failed.** Every commit above is committed, reviewed, and pushed live; the two regressions described above were caught and fixed within the same session, before this handoff was written — nothing shipped broken to `origin/main`.

- **UNVERIFIED (low-risk):** the WebGL render-fallback card's copy fix (part of the final fix wave) was verified by reading the source, not by actually rendering a WebGL failure state — the function is closure-scoped and wasn't easy to trigger live in a headless probe. The copy change itself is a plain string edit with no logic behind it, so the risk of this being wrong is low, but if you're ever debugging that specific fallback card, double-check its rendered text matches what the source says.
- **Deferred / parked, explicitly ruled fine to leave (not bugs, don't "fix" without checking first — several were deliberate calls):**
  - `#hint-banner` is dead code (styled, but unconditionally `display:none` a few lines below its own rule, superseded by the coach-mark tour) — pre-existing from before this redesign, not this redesign's job to prune.
  - `#board-view`'s new `aria-label` (added in the final fix wave) is inert — `aria-labelledby` wins in the accessible-name computation, so Causal Link's two sub-views (3D `#stage`, 2D `#board-view`) currently compute the same accessible name. Not broken, just not maximally distinct for a screen reader.
  - Four navy-leftover surfaces (`.orb-nudge-tip`, `#johnny-disclaimer-tip`, `#hint-banner`, `#all-hidden-message`) got their *color* fixed in the final wave but not their *shape* (some still have `border-radius: 6px` or `999px` pill shapes) — deliberately out of scope for that fix, since shape was never flagged as a problem on those elements, only color.
  - A handful of gold color uses (`.gterm` underline/hover, `.scenario-explain`/`.manual-intro` left-rules, `.rel-field-note`'s dashed border, `a.src-link`, plus headings and the `#header h1` "Bullion" wordmark) are deliberately kept — the final review confirmed these form a coherent "typographic voice" role (editorial/heading text) distinct from UI/brand chrome, not scattered leftovers.
  - **Multi-ID `aria-controls="stage board-view"`** on the Causal Link tab (final fix wave) is ARIA-spec-valid but unconventional, flagged by the implementer as a candidate for cleanup if a shared wrapper element around `#stage`/`#board-view` is ever added later.

## What's next (ordered)

Nothing is required. If a future session wants to pick up polish work, in rough priority order:

1. Delete `#hint-banner`'s dead CSS/markup (it's unreachable — `display:none` always wins).
2. If full ARIA correctness matters more later, add a shared wrapper around `#stage`/`#board-view` and give it a single accessible name distinct between the 3D/2D sub-views.
3. Decide whether the 4 navy-leftover surfaces' *shapes* (radius/pill) should also flatten to match the rest of the brutalist system, or are fine as an intentional soft-touch exception for tooltip-style overlays.

None of these block anything or represent regressions — they're the explicitly-parked tail of an otherwise-complete redesign.

## Verification idioms used in this project (for the resuming session)

- **JS-parse safety check** (this project hit a real silent-breakage class this session — always run this after editing any JS string literal in `bullion_mkultra.html`):
  ```bash
  cd bullion-live-map && python3 -c "
  import re
  html = open('bullion_mkultra.html', encoding='utf-8').read()
  scripts = re.findall(r'<script(?:(?!type=\"importmap\")[^>])*>(.*?)</script>', html, re.S)
  main = max(scripts, key=len)
  open('/tmp/extracted_main_script.js','w',encoding='utf-8').write(main)
  "
  node --check /tmp/extracted_main_script.js && echo "PARSES OK"
  ```
  Watch specifically for curly/smart Unicode quotes (' ' " ") accidentally substituted for straight ones in JS string delimiters — this exact defect broke all page JS silently once this session (commit `3d67ef4`, fixed in `1a72aa8`).
- **`headless-chrome-verification` skill** (CDP probe, reusable driver template) is how every task in this redesign was screenshot-verified. Two known hazards specific to this file: (1) **never call `openAuditLog()` in a headless/virtual-time probe** — it opens a real `window.open()` popup with an animated render that can stall the probe indefinitely; verify its wiring by reading the DOM/JS instead. (2) **never use `--virtual-time-budget` while the Causal Link tab's 3D scene is active** — Chrome can hang indefinitely under an active WebGL `requestAnimationFrame` loop; use the skill's reusable `cdp_probe.mjs` template (real wall-clock watchdog) instead, with a bounded fixed-time wait after switching to the 3D view rather than polling for "ready."
- **Python test suite:** `cd bullion-live-map && python3 -m unittest discover -s tests -v` — as of this writing: 128 tests, 1 pre-existing failure (`test_every_known_field_has_metadata`) + 1 pre-existing error (`test_fetch_bullion_news`), both in the Python fetch-pipeline tests, unrelated to `bullion_mkultra.html` (confirmed independently multiple times this session — an HTML-only diff cannot cause either).
- **`tests/freshness_test.html`** — browser-based, run via the CDP probe (no headless runner script exists for it). Should read 63/63 as of this session; if it regresses, check for stale hardcoded expected strings before assuming a real bug (this exact test had 7 stale emoji-expecting assertions this session, fixed in commit `e7adc50`).
