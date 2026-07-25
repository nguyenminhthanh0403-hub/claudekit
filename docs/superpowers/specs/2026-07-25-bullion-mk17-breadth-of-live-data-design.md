# Bullion Mk17 — "Breadth of Live Data" Design

**Date:** 2026-07-25
**Status:** Approved (brainstorm), pending implementation plan
**Predecessor:** Mk16 (`bullion_mk16.html`, current shared map) — cut from Mk15 lineage.
**Location:** `bullion-live-map/` in the `claudekit` repo.

## Goal

Expand the durable daily data pipeline with **13 new free live-data fields** and wire
them into a new `bullion_mk17.html` (cut from Mk16), promoting every candidate link that
`calibrate.py` can fit to a `MEASURED` badge. This lights up ~11 currently-static nodes
with real data and adds a system-stress reading, without introducing any new dependency.

**Explicit non-goal — MCP:** the refresh runs as a headless GitHub Action
(`fetch_bullion_data.py` → `data.json`), chosen precisely because it survives without a
Claude session. MCP servers live in a session and die with it, so they cannot feed this
cron. All new data comes from free REST series (FRED + Yahoo), the same pattern already in
place. FOMC hike/cut odds stay simulated (no free durable source) — out of scope.

## Scope: the 13 new fields

Node count stays **39** — NFCI attaches to the existing `vix` node as a secondary
"financial conditions" reading, so the Overview board layout (`perCol [3,3,6,3,8,10,6]`)
is unchanged.

### FRED series (9) → add to `FRED_SERIES`

| FRED id | field | binds to node | cadence |
|---|---|---|---|
| `NFCI` | nfci | vix (secondary readout) | weekly |
| `M2SL` | m2 | m2 | monthly |
| `MORTGAGE30US` | mortgage_30y | mortgage | weekly |
| `BAMLH0A0HYM2` | hy_oas | credit | daily |
| `BAMLC0A0CM` | ig_oas | credit | daily |
| `SOFR` | sofr | repo | daily |
| `DTB3` | tbill_3m | tbills | daily |
| `WALCL` | fed_bs | fed | weekly |
| `RRPONTSYD` | rrp | repo | daily |

### Yahoo symbols (4) → add to `YAHOO_SYMBOLS`

| Yahoo symbol | field | binds to node | cadence |
|---|---|---|---|
| `XLK` | xlk | tech | daily |
| `XLF` | xlf | fins | daily |
| `XLE` | xle | energy | daily |
| `XLP` | xlp | defn | daily |

## Component 1 — Pipeline (`fetch_bullion_data.py`)

- Add the 9 FRED entries to `FRED_SERIES` and the 4 to `YAHOO_SYMBOLS` (decimals per
  field: rates/spreads/indexes to 2, NFCI to 2, M2/WALCL levels to 1, ETF prices to 2).
- Add a matching `FIELD_META` entry (`class`/`cadence`/`source`) for **every** new field —
  `build_envelope` raises without it, by design (this is the provenance guarantee).
- **New `weekly` cadence tolerance (~10 days).** Rationale: NFCI (Wed), WALCL/H.4.1 (Thu),
  and MORTGAGE30US/PMMS (Thu) publish ~7 days apart. The existing `daily` bucket (7d)
  would false-alarm on a normal weekly series that slips a day or spans a holiday; the
  `monthly` bucket (45d) would let a genuinely dead weekly feed sit silent for six weeks.
  10d = 7 + slack for a holiday / one-week publication slip, mirroring the existing
  `daily` comment ("absorbs a three-day weekend plus a holiday").
  - Corrected during brainstorm: **M2SL is monthly** (not weekly), **RRPONTSYD is daily**
    (not weekly). Only NFCI / WALCL / MORTGAGE30US are truly weekly.
- Update `SOURCE_NOTE` to list the new sources.
- Cadence assignment summary:
  - daily (7d, existing): hy_oas, ig_oas, sofr, rrp, tbill_3m, xlk, xlf, xle, xlp
  - weekly (~10d, NEW): nfci, mortgage_30y, fed_bs
  - monthly (45d, existing): m2

## Component 2 — Map wiring (`bullion_mk17.html`)

1. **Cut the version:** `./release.sh 17` copies mk16 → mk17, bumps `<title>`/`og:title`/
   `<h1>` to Mk17, repoints `index.html`. `release.sh` only creates mk17 and edits
   `index.html`, so all prior version files stay byte-identical — verify mk16 (and mk15,
   the frozen `ebfaaaf6…` reference) are unchanged after the release cut.
2. **Metric cells + provenance sub** for each new field, following the existing
   `m-<field>` / `p-<field>` pattern (see the US10Y cell ~line 586 in mk16).
3. **Live bindings:** new fields flow into `BULLION_LIVE_DATA` automatically via the
   per-field-latest snapshot; add the slider-drivable subset to `LIVE_OVERRIDABLE`.
4. **Node detail readouts:** surface each field on its node's detail panel per the
   binding table above (nfci as a secondary "financial conditions" line on the `vix`
   node — display only, it does not originate new graph edges).

## Component 3 — Calibration (`calibrate.py` + client maps)

- Add candidate field→node cells for the new fields to the fit list.
- Run stdlib OLS on first-differenced daily changes over the 80% train split; classify
  each cell with `verdict()`:
  - **MEASURED** — fitted sign agrees with hand sign AND significant t. Promote into
    `ELASTICITY` / `NODE_ELASTICITY` and the client `BACKTEST_MAP`.
  - **DIRECTIONAL** — keep hand sign + note; do NOT claim a fitted beta.
- Regenerate `calibration_report.txt`.
- **Realistic expectation:** several new links will land DIRECTIONAL — that is the honest
  outcome (weekly/monthly series first-differenced against daily drivers often will not
  fit cleanly), not a failure. NFCI stays display-only (no new edges from it).

## Component 4 — Verification & release

- Extend `test_calibrate.py` for the new cells (keep it green).
- Headless-probe idioms (learned Mk14/15): inject the probe before the **last**
  `</body>` (line ~3379 has a `</body>` inside a JS string); **never** call
  `openAuditLog()` (its animated modal stalls headless virtual-time → hang); macOS has no
  `timeout` cmd; verify accuracy-panel logic via the `BACKTEST_MAP` / `backtestModel()`
  predicate, not the modal.
- Chrome-MCP check: 0 console errors; new metric cells populate from live data; backtest
  accuracy panel still grades; Overview board still 7 cols / 39 cards / 9 bold hubs.
- `release.sh` has already repointed `index.html` → mk17. Commit + push `main`; confirm
  live on Pages via `git show origin/main:<path>` (CDN caches ~5 min, so a stale live URL
  right after push is normal, not a failure).

## Execution method

superpowers **subagent-driven-development**: per-task review gate + an opus whole-branch
review before merge, matching Mk12 / Mk14 / Mk15. Session ledger in `.superpowers/sdd/`.

## Risks / non-goals

- **No FOMC-odds source** (still simulated) and **no MCP** — out of scope by design.
- **Yahoo fragility:** 4 more unofficial-API symbols; the pipeline already degrades
  gracefully to the simulated baseline on any fetch failure (file:// or 404).
- **`release.sh` is numeric-only** — it correctly handles `17`; do NOT route named
  variants (mkultra) through it.
- **Mk Ultra is out of scope** for wiring — it still gets the new `data.json` values
  automatically (all versions fetch the same file), but its link set is not updated here.
