# Bullion — Honesty Pass (Spec 1 of 2)

## Context

`bullion_mkultra.html` (39 nodes / 86 links) reports its own trustworthiness in the Audit Log
via `provCoverage()` (`bullion-live-map/bullion_mkultra.html:3389`), which tallies
`bump(l.conf || CONF.UNVERIFIED)` over `LINKS`. **No link in the file carries a `conf:` field**,
so all 86 fall into the red "unverified — set by feel; the sign may be wrong" segment. Every one
of those links *does* carry a `stat:` citation string. The map is therefore defaming its own
evidence base: this is a metadata gap, not an evidence gap, and the coverage bar is currently the
most misleading number on the page.

Meanwhile `data.json` now carries **23 fields over 366 days** (Mk17), and 22 of 39 nodes map to a
live field — which means **39 of the 86 links have both endpoints backed by real data** and can be
fitted rather than asserted. Four of the six links currently flagged `aud:false` ("⚠ sign
unverified") are among them, so their signs can finally be settled from data instead of feel.

**Outcome:** every causal claim on the map carries a confidence tier earned by a stated rule, the
Audit Log's coverage numbers become true, wrong-signed arrows get caught by a check that does not
exist today, and the teaching copy stops asserting undated two-year-old figures.

This is **Spec 1 of 2**. Spec 2 (a separate brainstorm/plan) is the Mk Ultra experience pass:
beginner legibility, visual elevation, motion polish, and the WebGL/CDN blank-screen fallback.

**Approved decisions from brainstorming (do not silently revisit):**
- All three verification surfaces in one pass: link tiers, the 6 dashed signs, node citations.
- Land in `bullion_mkultra.html` first (editable named variant), **then** cut `bullion_mk18.html`
  via `./release.sh 18` and port the verification data. `mk17` and earlier stay byte-frozen.
- Sign conflicts: **data wins when strong** (|t| ≥ 2 → flip the arrow, log the flip showing both
  values); hand sign kept and a conflict logged when weak.
- Tier is encoded **in the arcs themselves**, not just in numbers.
- Node copy: cite + as-of-date every figure, **and** prefer the live `data.json` reading where the
  node has one.

## Tier model

| Tier | Rule |
|---|---|
| `MEASURED` | An OLS fit exists for this exact pair with \|t\| ≥ 2 on the 80% train split. Fitted slope + t stored on the link. |
| `DIRECTIONAL` | No fit (endpoint lacks a live field, **or** the fit came back insignificant), but `stat:` names a real institution/dataset. Sign asserted from mechanism; no magnitude claimed. |
| `UNVERIFIED` | `stat:` names no source, or admits an unchecked window / unverified sign. Rendered dashed. |

**A failed fit is not proof a relationship is false.** `sec→equit` is structurally real and will
never show a daily-frequency signal. An insignificant fit on a data-backed pair stays
`DIRECTIONAL` (if sourced) and gains an honest note — *"tested on 366 days of daily changes; no
significant daily-frequency relationship (t=0.4)"*. The report says "no daily signal," never
"false."

## Work items

**0. Spec doc first.** Write `docs/superpowers/specs/2026-07-27-bullion-honesty-pass-design.md`
from this plan (project convention per `superpowers:brainstorming`) and commit it before code.

**1. Extend `calibrate.py` with a link pass.**
Reuse the existing Mk17 fitting machinery in `bullion-live-map/calibrate.py` (`fit_cell`,
first-differenced daily changes, 80% train split, per-field weekend bridging, t ≥ 2) — do not write
a second regression. Add a `LINK_CANDIDATES` derivation: every `LINKS` pair whose source and target
both resolve to a `data.json` field (39 pairs; the node→field map is `NODE_LIVE_FIELD` in
`bullion_mk17.html:3219`, extended with the driver/alias nodes `ffr`, `fomc`, `cpi`, `nfp`,
`dxy_fx`, `tsy`). Emit a new **LINKS** section in `calibration_report.txt` with slope, t, n, and
the MEASURED/insignificant verdict per pair.

**2. Tier all 86 links in `bullion_mkultra.html`.**
Write `conf:` onto every entry in the `LINKS` array (`:1180`–`:1235` region) per the tier model,
using the report from item 1. MEASURED links also get the fitted slope and t appended to their
`stat:` clause. Nothing gets a magnitude it did not earn (Mk15.2 / Mk17 precedent).

**3. Sign audit + conflict resolution.**
Where a fitted sign contradicts the hand-set `sign:`: |t| ≥ 2 → flip `sign:`, and record the flip
(old value, fitted value, t) for the Audit Log; |t| < 2 → keep `sign:` and push a
`PROV_CONFLICTS` entry. Extend the existing `demote()` closure in `validateProvenance()`
(`:3349`) to cover `LINKS` as well as `ELASTICITY`/`NODE_ELASTICITY`, so a link claiming a tier
with an empty source is auto-demoted at load — the mechanism exists, links were never wired in.

**4. Resolve the 6 `aud:false` links.**
`usd→oil`, `dxy_fx→credit`, `oil→equit`, `gold→tsy` are data-backed: settle them from the fit.
`china→tsy` and `geo→credit` have no free daily series (TIC is monthly; geopolitical risk has no
free feed) — they stay `UNVERIFIED`/dashed with the *reason* stated in `note:`, not merely the
verdict. Once `conf` exists, `aud:false` is redundant with `conf === UNVERIFIED`; keep `aud` as-is
for now and let `conf` drive rendering, so no other reader of `aud` breaks.

**5. Port `NODE_LIVE_FIELD` into Mk Ultra (prerequisite for item 6).**
Mk Ultra has no `NODE_LIVE_FIELD` / `LIVE_FIELD_LABEL` / `MK17_FMT` — copy them from
`bullion_mk17.html:3219` plus the "Live reading" line in `openDetail` (`:1927`–`:1932`).

**6. Node copy: 8 nodes.**
`nfp`, `vix`, `usd`, `dxy_fx`, `gold`, `china`, `russia`, `geo` — add the trailing `Source:` line
the other 31 nodes already use, attribute the 6 genuinely uncited claims (gold's "near-zero
long-run correlation to equities"; the DXY basket weights → ICE; china's "~92% of sub-7nm chips";
russia's "$300B reserves frozen" + shadow-fleet claim; geo's "1.5–2% added to global CPI"), and
as-of-date every hardcoded figure. Where the node has a live field, the live reading becomes the
primary number and the hand-typed figure becomes dated historical context.

**7. Arc encoding + legend.**
In `buildLinkObjects()` (`:1589`) switch the dashed branch from `l.aud === false` to
`conf === UNVERIFIED`, and set base opacity by tier (measured brightest, directional softer,
unverified dashed). Color still = sign, tube radius still = strength `w`; confidence is the new
channel, so the three encodings do not collide. Add an EVIDENCE block to the legend and move the
existing "Dashed = sign unverified" row into it.

**8. Tier badges in the detail panel.**
Add a tier badge to each relationship row beside the existing arrows (`:2436`–`:2440`). The
`.tier.measured|directional|unverified` colour rules already exist (`:4240`) but are inside the
Audit Log's injected CSS string — hoist them to the main stylesheet rather than duplicating.

**9. Cut Mk18 and port.**
`./release.sh 18` (numeric-only; never route `mkultra` through it), then port items 2/3/4/6 into
`bullion_mk18.html`. 2D tier encoding rides the existing `stroke-dasharray` + `.link-line.unaudited`
hook (`bullion_mk17.html:1549`, `:1554`) with stroke-opacity for the measured/directional split.
Confirm `index.html` → mk18 and that mk15/16/17 hashes are unchanged.

## Traps (learned, not guessed)

- **`clearFocus` hardcodes link opacity.** `lo.mat.opacity = 0.55` (`:2206`) and the focus-dim
  write `0.85 : 0.06` (`:2193`) will flatten all three tiers to identical after the first
  focus/clear cycle. Store `baseOpacity` on each `linkObj` (pushed at `:1639`) and restore to it.
- **One shared material per link** covers every dash sub-tube plus the arrowhead (comment at
  `:1608`) — set tier opacity once on `mat`, not per mesh.
- **Headless probe:** inject before the **last** `</body>` (there is a decoy `</body>` inside a JS
  string mid-file — use `rfind`). **Never call `openAuditLog()`** in a probe; its animated modal
  stalls headless virtual-time and hangs. Verify the coverage panel through `provCoverage()` /
  `BACKTEST_MAP` predicates over globals instead. macOS has no `timeout`.
- **WebGL in headless:** plain `--headless=new --disable-gpu` renders a blank globe. Use
  `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader` for visual checks.
- **Never `git add .`/`-A`** — `docs/`, `.claude/`, `CLAUDE.md`, `.DS_Store` are pre-existing
  untracked files. Stage only the files a task touches.
- **`.superpowers/sdd/task-N-report.md` files have repeatedly held stale content from unrelated
  older tasks.** Do not trust one unless its content matches the task expected.

## Verification

- **Python:** `cd bullion-live-map && python3 -m unittest discover -s tests` (currently 41/41) and
  `python3 -m unittest test_calibrate` (currently 11/11). New tests for the link pass must assert:
  the 39-pair candidate derivation, the t ≥ 2 promotion boundary, and that an insignificant fit is
  **not** promoted to MEASURED.
- **Client (headless probe):** every link has a `conf`; `provCoverage()` segments sum to `total`;
  after `validateProvenance()` no link claims a tier with an empty source; the 4 calibratable
  `aud:false` links have resolved tiers; any sign flip appears in the flip log.
- **Visual (Chrome MCP or swiftshader screenshot):** the three arc tiers read as distinct at rest,
  a focus → clear-focus cycle restores per-tier opacity (the `:2206` trap), and the legend EVIDENCE
  block matches what the arcs actually draw.
- **Freeze check:** `shasum -a 256` on `bullion_mk15.html` (`ebfaaaf6…`), `bullion_mk16.html`
  (`ef9fbc55…`), and `bullion_mk17.html` before and after — must be unchanged.
- **Live:** after push, `git show origin/main:<path>` is the source of truth; the Pages CDN lags
  ~30–90s and a brand-new mk-file URL can 404 briefly. That is not a failure.

## Out of scope (Spec 2)

Beginner legibility (progressive disclosure, jargon tooltips, guided tour), visual elevation,
motion/micro-interaction polish, the WebGL/CDN blank-screen fallback to the 2D board, and vendoring
Three.js inline. Also deferred: porting Mk17's 6 calibrated ELASTICITY links and 22-cell metric
grid into Mk Ultra, and the `us10y→spx_pct` promotion question.
