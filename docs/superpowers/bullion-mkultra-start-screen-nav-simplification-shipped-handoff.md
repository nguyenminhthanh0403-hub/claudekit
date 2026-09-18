# Bullion Mk Ultra Start Screen + Nav Simplification — Session Handoff

**Written:** 2026-09-18 · **For:** a fresh session that touches `bullion_mkultra.html`'s start
screen, top-level nav, or `beginnerMode`/`.adv-control` gating next. This is a
**closeout/reference record** — nothing is in progress, everything below shipped and is live.
Read the prior handoff (`docs/superpowers/bullion-mkultra-brutalist-nav-redesign-shipped-handoff.md`)
first if you need the black/red-orange/gold "brutalist" design-token background this session
builds directly on top of.

## Goal

Two things landed this session, on `bullion-live-map/bullion_mkultra.html`:

1. **A game-style title/start screen**, shown on every page load, that the visitor has to
   click through before reaching the app.
2. **Nav simplification**: reordered the top-level tabs, removed the separate "Tools"
   beginner/advanced toggle button, and made everything it used to gate permanently visible.

No spec or implementation-plan file exists for this — it was done via
`superpowers:brainstorming`'s **bounded** path (short design presented in chat, approved,
implemented directly), which deliberately produces no spec/plan doc. This handoff plus
`git log` are the only record.

## How to resume (do this first)

1. Confirm you're on `main`, in sync with `origin/main` — `git log --oneline -1` and
   `git log --oneline -1 origin/main` should match (`c15b115` as of this writing). The commit
   immediately before it, `ed79fa6`, is the prior handoff's closeout point.
2. There is no ledger/plan to re-read — this was small enough to stay inline. Trust
   `git show c15b115 --stat` and this handoff over any other memory of the work.
3. **Immediate next action: none required.** This is a closed loop, shipped and pushed. See
   "What's next" below for optional, explicitly-deferred follow-ups only.

## Current state (active files)

**Branch:** `main`, pushed and in sync with `origin/main` at `c15b115`.

**Files created / changed (commit `c15b115`):**
- `bullion-live-map/bullion_mkultra.html` — every change described below lives here; no new
  files were created, per this project's one-file-per-map-version convention.

**Scratch workspace / traps:**
- ⚠️ This session ran a local `python3 -m http.server 8934` from inside `bullion-live-map/` to
  verify changes via headless Chrome (serving over `http://localhost`, not `file://`, since the
  page fetches `data.json`/`news.json`). That server was killed before this handoff was
  written — don't assume port 8934 is live; start your own if you need to re-verify visually.
- ⚠️ The start screen's decorative "constellation" HTML/CSS was first-drafted by the
  `delegate` skill (per the newly-adopted delegate-first policy — see global memory
  `delegate-skill-global-workflow` if you want that context, it's not project-specific). The
  first draft had three real bugs, all fixed before integration — worth knowing if you ever
  ask delegate to touch this file again and get something that looks plausible but is broken:
  duplicate `id="brand-eyebrow"` reused across three elements, `preserveAspectRatio="none"` on
  the star SVG (distorts circles into ellipses on non-square viewports), and a `:nth-child`
  animation-delay selector that silently didn't cover all 16 star elements. None of this is in
  the shipped code — flagged only as a pattern to watch for.

**Not mine — leave alone:** `bullion_mk11.html` through `bullion_mk18.html` (frozen
prototypes), `fetch_bullion_data.py`/`fetch_bullion_news.py` (Python fetch pipeline, untouched
this session), `data.json`/`news.json` (bot-managed, regenerated daily — the push in this
session had to rebase past several same-day bot commits to these files, see below), and the
five untracked handoff files sitting in `docs/superpowers/` / `docs/superpowers/archive/`
(pre-existing leftovers from prior sessions, not this session's concern — one more,
`bullion-rate-hike-probability-brainstorm-handoff.md`, was moved into `archive/` by this
handoff's own write-up per the handoff-archiving convention, since it fell outside the
"keep the 2 most recent" rule and was untracked).

## What has changed

- **Start screen** (part of commit `c15b115`): a full-screen `#start-screen` overlay, first
  child of `<body>`, shown on every load. Giant "BULLION" wordmark (`var(--font-display)`,
  gold, matching the header `<h1>`'s own deliberately-kept-gold wordmark precedent), the
  existing three-ring brand-mark logo scaled up, a faded oversized italic Δ behind the title
  (same technique as the pre-existing `.hero-stat-ghost`), a decorative 16-element
  constellation (SVG dots + connecting lines, gentle staggered twinkle, `prefers-reduced-motion`
  aware), a pulsing bone-white (`#e8dfc8`) "Click to Start" — a real unstyled `<button>`, not a
  styled button, per explicit user request, so it stays keyboard/screen-reader operable — and
  "MK ULTRA" pinned at the bottom as the version label (there's no numeric semver tracked
  anywhere in this codebase; "Mk Ultra" is the actual current build name, used as-is rather
  than inventing a number).
  - **Color iteration:** the constellation was first drafted in gold-dim to match the wordmark,
    but the user said that clashed with the app's actual black/red-orange brand identity — the
    stars/lines now use `var(--accent)` (`#ff3300`) instead. The wordmark and logo stayed gold,
    matching the header's own kept-gold "typographic voice" exception documented in the prior
    handoff.
  - Dismissing the start screen calls `showView('causal-link')`, and the app's own default
    view on load was changed from `showView('market')` to `showView('causal-link')` too (plus
    the static tab markup's `active`/`aria-selected` state moved from Market to Causal Link),
    so there's no flash of the wrong tab before JS runs. This means the 3D map — and its
    pre-existing first-run guided coach (`#coach`, the "Start here" / "That card is the point" /
    "Reading the lines" 3-step walkthrough, unchanged content-wise except one stale copy fix
    below) — is now the first thing a visitor actually reaches, instead of being orphaned
    behind a tab click nobody was forced to make.
- **Nav simplification** (same commit): tablist order changed to **Causal Link | Market |
  Analysis** (was Market | Analysis | Causal Link). The separate `#mode-toggle-btn` ("Tools")
  button — the *only* UI control that ever toggled `beginnerMode` — was removed entirely.
  Analysis's tab button lost its `.adv-control` class and is now always visible (previously
  hidden until Tools was opened). So were `#live-badge`, `#live-toggle-btn` (Live Data),
  `#expand-all-btn`, `#collapse-all-btn`, `#reset-view-btn`, and `#audit-log-btn` — all six were
  the complete list of `.adv-control`-tagged elements in the app, and all six are now
  unconditionally visible rather than permanently unreachable (see "What has failed / risks"
  below for why "permanently unreachable" was the alternative that got explicitly ruled out).
  - `applyBeginnerMode()`, `onFirstInteraction()`, and the event-listener wiring were all
    trimmed of their now-dead references to `#mode-toggle-btn` (would otherwise throw
    `TypeError: Cannot read properties of null` on load, since the element no longer exists).
  - Coach step 3's copy ("Ready for live market data, scenarios and sources? Open **Tools**,
    top-right.") was stale after the button's removal — updated to point at **Analysis** and
    the toolbar instead.
  - The `.tools-ready` pulse-glow CSS/keyframe (a first-interaction nudge that used to glow the
    Tools button) was removed as genuinely dead code, since its target element is gone.

## What has failed / risks / caveats

**Nothing has failed.** Commit `c15b115` is pushed and live; verified via a headless Chrome
CDP probe (see idioms below) both before and after — no duplicate IDs, start screen renders
and dismisses correctly into Causal Link + coach, nav tab order and labels correct, Tools
button confirmed absent, all six previously-gated controls confirmed visible via
`getComputedStyle`. The project's JS-parse safety check passed after every edit round. Python
test suite: 128 tests, same 1 pre-existing failure (`test_every_known_field_has_metadata`) + 1
pre-existing error (`test_fetch_bullion_news`) as the prior handoff documented, both in the
unrelated Python fetch pipeline — re-confirmed unchanged this session.

- **UNRESOLVED — a real, known, user-flagged-but-undecided side effect:** removing the Tools
  button means `beginnerMode` (declared `let beginnerMode = true;`) now has **no UI path to
  ever become `false`** — nothing sets it. Two things still key off it:
  1. The guided coach (`renderCoach()` requires `beginnerMode` truthy) — this is fine, it's
     supposed to always be available now.
  2. `openDetail()`'s node-detail-card text (`bullets = (!beginnerMode && d.expert) ? d.expert
     : d.beginner`, around line 3392) — this is **not** fine as a permanent state: it means
     every node detail card now renders the plain-English/"beginner" description forever, and
     the technical/cited "expert" description (which every node's data actually has, per this
     project's content standard) is **permanently unreachable through any UI**, with no toggle
     left to bring it back.
  - This was surfaced to the user in this session's final summary but **no decision has been
    made** on whether to fix it. If asked to "let me see the technical descriptions again" or
    similar, this is almost certainly the same root cause — the fix needs a product decision
    (bring back some toggle? Auto-pick based on something else? Show both?) before touching
    `openDetail()`.
- **Deliberately left as inert rather than deleted:** `#app.beginner-on .adv-control {
  display: none !important; }` (CSS) and `document.getElementById('app').classList.toggle
  ('beginner-on', beginnerMode);` (JS, inside `applyBeginnerMode()`) both still exist. Nothing
  currently carries `.adv-control`, so neither does anything right now — left in place
  intentionally (cheap hook if advanced-mode gating is ever wanted again; cheap to actually
  remove later once it's confirmed nobody wants it back) rather than ripped out as an
  unrequested cleanup.
- **Cosmetic, explicitly accepted, not a bug:** the start screen's constellation stars render
  as soft glowing "bubbles" rather than crisp pinpoints — a consequence of how the SVG's
  `0 0 100 100` viewBox scales onto a real viewport (large radii × large scale factor). The
  user was shown this in a screenshot and was fine with it (they'd used "bubble or stars"
  language themselves when requesting the feature) — noted here only so a future "sharpen the
  stars" request goes straight to the `.starfield-deco` SVG's circle-radius/viewBox values
  instead of the twinkle animation.
- **Push required a rebase, not a fast-forward:** `git push` was initially rejected because
  this project's daily automated data pipeline (`data.json`/`news.json` bot commits) landed
  several commits on `origin/main` during this session. Confirmed via `git diff --name-only`
  that those bot commits touched only `data.json`/`news.json`/news images, never
  `bullion_mkultra.html`, so `git rebase origin/main` was clean with zero conflicts. If this
  happens again, the same check (diff the remote-only commit range for filename overlap before
  rebasing) is the safe move, not an unconditional `git pull`/merge.

## What's next (ordered)

Nothing is required. If a future session wants to pick up open threads, in priority order:

1. **Decide the node-detail expert-text question** (see UNRESOLVED above) — this is the one
   real open item, and it needs the user's input, not a unilateral code fix.
2. If asked to make the start-screen stars crisper/smaller, edit `.starfield-deco`'s SVG
   viewBox / circle radii, not the `bullion-twinkle` keyframe.
3. Nothing else outstanding from this session.

## Verification idioms used in this project (for the resuming session)

- **JS-parse safety check** (same as the prior handoff documented — still the right move
  after editing any JS string literal in this file):
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
- **`headless-chrome-verification` skill** (CDP probe template) — this session served the app
  via `python3 -m http.server <port>` from inside `bullion-live-map/` (not `file://`, since
  `data.json`/`news.json` are fetched) and used the reusable `cdp_probe.mjs` template's
  `evalJS`/`screenshot` helpers to: check for duplicate DOM ids, read start-screen text/state,
  screenshot it, click `#start-screen-cta` via `evalJS(...).click()` (not a coordinate click —
  see the template's own gotcha #6 about canvas/WebGL elements stealing coordinate clicks),
  wait on real wall-clock time (not `--virtual-time-budget` — the 3D scene has an active WebGL
  `requestAnimationFrame` loop, same hazard the prior handoff documented), then assert nav tab
  order/labels and `getComputedStyle(...).display` on the six previously-gated elements.
- **Python test suite:** `cd bullion-live-map && python3 -m unittest discover -s tests -v` —
  as of this writing: 128 tests, 1 pre-existing failure + 1 pre-existing error, both in the
  Python fetch-pipeline tests, unrelated to `bullion_mkultra.html` (same two the prior handoff
  documented, re-confirmed unchanged this session).
