# Bullion Mk Ultra — Brutalist Nav Redesign — Design

**Written:** 2026-09-09 · **Status:** approved by user, ready for `writing-plans`

## Goal

Two changes to `bullion_mkultra.html` (the live public front door), bundled because the
second doesn't make sense without the first:

1. **Reorganize the top-level navigation** from today's four destinations (🌐 3D Map,
   ▦ Overview, 📈 Markets, ⚙ Tools drawer) into exactly three: **Market**, **Analysis**,
   **Causal Link**.
2. **Replace the visual language** so the app stops reading as generic/templated
   "AI-generated dashboard" — current look: dark navy `#0b0e16`, soft gold `#d4b869`
   accent, uniform rounded `#111522` cards, emoji icons in the nav, one uniform sans
   everywhere.

This is a visual/IA redesign, not a data or feature change — `data.json`/`news.json`,
the fetch pipeline, `ELASTICITY`/`NODE_ELASTICITY`, and the 3D scene's rendering logic
are all out of scope and untouched.

## Decisions made (brainstormed 2026-09-09, all user-approved)

Recorded here so a resuming session doesn't have to re-derive them:

- **Visual direction: Brutalist.** Flat solid colors, no gradients, no soft borders —
  thick (2-3px) solid rule lines instead. Oversized bold numerals for hero stats against
  tiny uppercase labels (extreme type-scale contrast, nothing medium). One loud accent
  color. Chosen over two other directions shown side-by-side (Terminal/monospace-Bloomberg,
  Editorial/serif-print) — Brutalist was picked outright, no runner-up to fall back to if
  it doesn't hold up in the full app.
- **Signature accent: italic Greek Δ (delta), blended usage.** Two treatments, both
  approved together, not either/or:
  - **Functional** — Δ prefixes every numeric *change* value app-wide (price % change,
    scenario-driver deltas, anywhere a delta is already the concept), styled in an
    italic serif (Georgia/Times New Roman stack) against the otherwise condensed-sans
    brutalist type. Reads as real quant notation, not decoration.
  - **Textural** — one oversized (~100-110px), heavily faded (≈7% opacity) italic Δ
    ghosted behind each tab's hero stat block, purely atmospheric.
  - Other Greek letters (β for volatility, etc.) are explicitly allowed later if a
    section calls for one, but nothing beyond Δ is scoped into this redesign.
- **Accent color: `#ff3300` (red-orange), replacing gold as the UI/brand color.** Gold
  (`#d4b869` or similar) survives only as literal data coloring (the word/number "GOLD"
  can still read warm) — it is no longer the button/nav/link accent. Explicitly chosen
  over keeping gold-as-accent: the user wants a clean signal that this is a new visual
  era, not a re-skin of the old gold-on-navy identity every prior version (mk11 through
  today's Mk Ultra) has shared.
- **Sweep scope: whole app.** Every emoji/icon and generic soft-rounded-card treatment
  gets swept in this redesign — nav, Markets-tab cards, the Fed-odds card just shipped,
  drawer/Tools buttons, the disclaimer modal, persona-orb hint text. Not scoped down to
  "new surfaces only." Exception, explicitly out of scope: the news list's ▲▼ sentiment
  glyphs are plain Unicode triangles, not emoji, and stay as-is unless a later pass wants
  to Greek-ify them too.
- **3D map: stays the default/centerpiece of Causal Link, rendering untouched.** The
  Three.js scene's glow/gradients/orbit camera are NOT restyled — only the chrome around
  it (nav, detail panel, causal-relationships list, legend-and-controls) gets the
  brutalist treatment. This is a deliberately accepted visual seam between the WebGL
  scene and its new frame, chosen over demoting 3D to a secondary view behind a
  2D-board-first Causal Link tab (which would have been easier to make fully consistent,
  but was explicitly rejected — 3D non-negotiable as centerpiece).
- **Build strategy: direct on `main`, in phases — not a worktree/branch.** Explicitly
  chosen over the isolated-worktree approach this project used for its last big UI
  feature (the custom-node-selection work, see project memory), despite the daily
  `daily-data.yml` cron bot committing to the same file's neighbor (`data.json`) every
  morning. Accepted trade-offs, stated plainly so a resuming session doesn't mistake
  them for oversights: the live site will show a part-migrated UI for the whole build
  period (old tabs/new tabs coexisting commit-to-commit), and a bot commit could in
  principle land between redesign commits (low actual collision risk in practice, since
  the bot only ever touches `data.json`/`news.json`/`news-images/`, never
  `bullion_mkultra.html` — but the ordering is not isolated the way a worktree would
  make it).

## Where today's features land

| Today | Becomes |
|---|---|
| 📈 Markets tab (index cards, Fed-odds card, news ticker) | **Market** tab, same content, brutalist restyle |
| ⚙ Tools drawer (scenario simulator, manual driver sliders, health score, AI/rule narrative, backtest) | **Analysis** tab — promoted from a slide-out drawer to a real top-level tab. The drawer pattern and its ⚙ entry button both go away. |
| 🌐 3D Map (Three.js constellation, default view) | **Causal Link** tab, default sub-view. Rendering untouched; chrome (nav/detail panel/relationship list/legend) restyled. |
| ▦ Overview (2D fallback board, same node/link graph) | **Causal Link** tab, secondary sub-view via an in-tab toggle (not a sibling top-level tab). Fully restyled — flat HTML/CSS, no seam. |
| Disclaimer modal, persona-orb hints, misc icons | Swept in place, no relocation — just visual treatment changes. |

`showView()` collapses from its current three states (`3d` / `board` / `markets`) plus
the separate drawer-open/closed boolean, into three top-level states (`market` /
`analysis` / `causal-link`) where `causal-link` carries its own internal `3d`/`board`
sub-toggle (replacing today's sibling-tab relationship between 3D Map and Overview).

## Visual system

- **Background:** `#0d0d0d` (near-black), replacing `#0b0e16` (navy).
- **Surfaces:** cards mostly eliminated. Structural separation comes from thick
  (2-3px) solid white/black rule lines (`border-top`/`border-bottom`), not rounded
  bordered boxes. Where a contained tile is genuinely needed (index stat tiles), it's
  flat, square-cornered, no shadow, no gradient, no `border-radius`.
- **Accent:** `#ff3300`, single color, applied consistently (active nav state, Δ
  glyphs, rule-line emphasis where a section needs to stand out).
- **Type:** a condensed sans for labels/nav/uppercase text (system stack —
  `"Arial Narrow", "Helvetica Neue", Arial, sans-serif` — or a free condensed webfont
  such as Archivo Narrow off Google Fonts, per this project's existing CDN allowlist,
  if system-font coverage across the mkultra userbase's browsers turns out inconsistent
  — decide at implementation time, not blocking this spec). Numerals get extreme
  type-scale contrast: large/bold for hero stats, small/uppercase/letter-spaced for
  their labels, nothing medium-sized in between.
- **Δ (delta) usage — the one signature typographic device:**
  - Functional: `Δ` prefixes every numeric change value app-wide, italic serif
    (Georgia/Times New Roman stack), small, inline with the number it modifies.
  - Textural: one `Δ` per tab's hero stat block, ~100-110px, ~7% opacity, positioned
    behind the stat number (absolute-positioned, `z-index` below the readable content,
    `pointer-events: none`).
- **Icons/emoji:** removed everywhere except the news list's ▲▼ sentiment glyphs
  (explicitly out of scope, see Decisions above).

## Build order

Each phase ships as its own complete, working commit directly to `main` — never a
partial/broken intermediate state, per this project's existing "never publish a
truncated state" discipline (echoing `fetch_bullion_data.py`'s own completeness gate,
applied here to commits instead of data).

1. **Design tokens** — swap the CSS custom-property values (background, accent,
   type stack) at the `:root` level only. Lowest-risk phase: shifts the whole site's
   feel before any structural/markup change, and is trivially revertible on its own if
   it doesn't look right in practice once every existing card/button inherits it.
2. **Global emoji/icon sweep** — independent of the nav restructure below; can ship
   as its own commit. Touches nav labels (temporarily, ahead of phase 3's structural
   change), drawer/Tools buttons, disclaimer modal, persona-orb hint text.
3. **Nav shell + Market tab** — collapse the tab bar to the new 3-item structure,
   rewire `showView()`, restyle the Market tab's content (index cards, Fed-odds card,
   news ticker) to the flat/ruled system. Smallest, newest surface — lowest risk to
   restyle first.
4. **Analysis tab** — promote the Tools drawer's content (scenario simulator, manual
   drivers, health score, narrative, backtest) into a real tab; retire the drawer
   pattern and its trigger button.
5. **Causal Link tab** — 2D board gets the full brutalist re-skin as the in-tab
   secondary view; 3D chrome (nav/detail panel/relationship list/legend) restyled
   around the untouched Three.js scene.
6. **Consistency pass + verification** — sweep for anything phases 1-5 missed
   (e.g. a stray card style, a leftover emoji), confirm the whole app reads as one
   coherent system end to end.

## Testing

- The existing Python test suite (`tests/`) must stay green throughout. It doesn't
  assert on CSS/visual state, but phase 3's `showView()`/tab-ID rewrite needs a check
  that nothing else (tests, `tests/freshness_test.html`, `release.sh`, etc.) string-matches
  the old tab IDs (`tab-3d`/`tab-board`/`tab-markets`) or DOM structure being replaced.
- Each phase gets a `headless-chrome-verification` screenshot pass before its commit
  (same verification method used for the Fed-odds card, 2026-09-08) — confirm the
  phase's surface renders correctly and nothing else regressed, not just that the code
  is syntactically valid.
- No new automated visual-regression tooling is being added — out of scope / YAGNI for
  a personal project; manual QA is Stage 4 of this project's own standing workflow.

## Explicit non-goals

- No change to `data.json`/`news.json` shape, the fetch pipeline, or
  `ELASTICITY`/`NODE_ELASTICITY` values.
- No change to the 3D scene's own rendering (lighting, node glow, orbit controls,
  Three.js version).
- No new Greek letters beyond Δ scoped into this pass (β etc. explicitly deferred).
- No worktree/branch isolation (explicitly rejected — see Decisions above).
- No visual-regression test automation.
