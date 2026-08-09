# Mk Ultra macro engine — design

## Problem

`bullion_mkultra.html`'s "Run AI analysis" button (`runAIAnalysis()`) does two things, both broken:

1. It POSTs to `https://api.anthropic.com/v1/messages` with no `x-api-key` header at all. On the public GitHub Pages deployment this 401s on every single call — every visitor is always silently falling back to `runLocalAnalysis()`, never real AI, despite the UI presenting it as "AI analysis."
2. `runLocalAnalysis()` is a hand-picked linear formula: base score 82, minus six magic-number thresholds (`vix > 17`, curve inversion, `spx < 5312`, `cpi_yoy > 2.4`, etc.). It has no news/sentiment input (by original design — the pipeline is scoped to free FRED/Yahoo REST series only, so an unattended cron can run it), but even within that quantitative-only scope it ignores fields that are already fetched live (`hy_oas`, `ig_oas`, `fed_bs`) and starts from an optimistic anchor rather than a historically-grounded baseline. The `node_impact_multipliers` shown with no active shock are a static illustrative placeholder, unrelated to real conditions.

Wiring in a real API key was considered and rejected: this is a static public page, so any client-side key is extractable by anyone viewing the page source/network tab, exposing the account to unbounded use by strangers — not just per-visit cost. A serverless-proxy or daily-cached-LLM approach would avoid that, but isn't being built now.

## Decision

Replace all three outputs (health score, narrative, node impact multipliers) with a fully deterministic, client-side quantitative engine — no LLM, no external API call, zero marginal cost, works identically for every visitor. Scope is **`bullion_mkultra.html` only** — `bullion_mk18.html` and the frozen mk11-17 are untouched.

Methodology is grounded in how real institutional financial-conditions/stress indices are actually built (Chicago Fed NFCI, OFR FSI, St. Louis Fed STLFSI, ECB CISS — see Sources) rather than hand-picked weights. The one consistent finding across all four: none of them use analyst-judgment weights. They derive weights statistically from the data's own covariance structure (PCA or a dynamic factor model). This design follows STLFSI's approach (PCA on z-scored series) as the most tractable to implement correctly in a static pipeline.

## Architecture

Two new pieces, mirroring the existing `calibrate.py` → baked-JS-constants pattern already used for `ELASTICITY`/`NODE_ELASTICITY`:

1. **`backfill_baseline.py`** (offline, rerunnable): pulls **15 years** of history per relevant FRED/Yahoo series (same series `fetch_bullion_data.py` already tracks — FRED series support this range natively; Yahoo daily history does too), computes per-field mean/std and empirical percentile bands, runs PCA over the z-scored fields, and writes the per-field means/stds, oriented PC1 loadings, and the historical composite-score distribution (for percentile lookup) as baked-in JS constants in `bullion_mkultra.html` — same delivery mechanism as `ELASTICITY`. If a given field's FRED/Yahoo history is shorter than 15 years (e.g. a newer series), use whatever history exists and record the actual window length for the confidence-tier check below.
2. **A client-side scoring module** in `bullion_mkultra.html` that replaces `runLocalAnalysis()` and the `runAIAnalysis()` handler: reads live `data.json` + the baked-in baseline constants, computes score/narrative/multipliers synchronously at click time. No `fetch` to any external host.

## Composite health score

- Fields scored: `hy_oas`, `ig_oas` (credit); `spx` trend-deviation, sector-ETF (`xlk`/`xlf`/`xle`/`xlp`) dispersion (equity valuation); `sofr`, `tbill_3m`, `rrp`, `fed_bs` trend (funding); `us10y`, `us2y`, curve slope (safe assets); `vix` (volatility). This mirrors OFR FSI's 5-category structure adapted to our live fields.
- `cpi_yoy` and `nfp_mom` (growth/inflation) are **excluded from the score** — none of the four reference indices include growth/inflation, since they're monthly-lagged fundamentals, not real-time market-based stress signals. They remain in the narrative as context only.
- Each field is z-scored against its own backfilled historical mean/std, clipped to ±3.
- PCA is run once (in `backfill_baseline.py`) over the z-scored fields; PC1 loadings become the per-field weights. Sign is oriented post-hoc so `vix`'s loading is always positive (every reference methodology agrees rising VIX = more stress — a safe anchor).
- Today's composite = weighted sum of current z-scores using the baked-in PC1 loadings.
- Score mapping: PC1 loadings are applied to every day in the backfilled history to build a historical distribution of the composite itself. `health_score = 100 − percentile_rank(today's composite, that distribution)`. Median historical day lands at 50 — no optimistic anchor.
- If backfilled history for a field is too short for a stable PCA fit, the composite's confidence tier degrades from `measured` to `directional` and the narrative says so.

## Node impact multipliers (baseline, no active shock)

Reuses the existing `NODE_ELASTICITY` matrix (`bullion_mkultra.html:3833`) rather than inventing new coefficients: for each of the 5 real drivers it already covers (`ffr`, `vix`, `cpi_yoy`, `dxy`, `wti_px`), compute that driver's current deviation from its own backfilled historical mean, and run that deviation through the existing sourced/tiered elasticity coefficients — i.e., treat "how far today actually is from normal" as the shock push, instead of a hypothetical dropdown value.

- Every node multiplier inherits the confidence tier already on its underlying `NODE_ELASTICITY` cell (measured/directional) — no new tier invented.
- Nodes with no `NODE_ELASTICITY` row for any of the 5 drivers (`Dealers`, `HF`, `China`, `Russia`, `Geopolitics`, `Treasury` — several were deliberately deleted in prior sessions for being unsourced) stay at exactly 0, labeled "no live-data-backed reading" — consistent with the project's existing "no invented magnitude" precedent (Mk15.2).
- Active shock-scenario propagation (the dropdown-driven hypothetical push) is unchanged — this only replaces what renders when no shock is active.

## Narrative (deterministic template)

Same 3-sentence shape as today, every clause backed by a real computed number:

1. Regime + top driver: "Financial conditions sit at the *N*th percentile of the past *K* years, driven primarily by *[category with the largest PC1-weighted contribution today]*."
2. Growth/inflation context, explicitly framed as backdrop not score input: "Core CPI is running at *X*% against the Fed's 2% target; payrolls are [trending/flat]."
3. Node-level takeaway: names the largest positive and negative `NODE_ELASTICITY`-driven current-deviation multipliers from the section above.

Pure string templating over real values — deterministic, zero cost, same input always produces the same output (testable).

## Confidence tiering / audit log

Surfaces in the existing `openAuditLog()` panel as a new section, matching the project's established measured/directional/unverified convention:

- Composite score: `measured` (named methodology — PCA, à la STLFSI — with backfill window and last-recomputed date shown), degrading to `directional` if a field's backfill history is too thin.
- Node multipliers: inherit the tier from their underlying `NODE_ELASTICITY` cell.
- Growth/inflation: `measured` (real FRED source) but flagged "excluded from score by design," not silently dropped.
- Which nodes got a real vs. 0/no-data baseline reading is listed explicitly.

## UI/copy changes

- Delete the dead `fetch('https://api.anthropic.com/v1/messages', ...)` call and the `BACKEND_URL` proxy stub — both dead code now.
- Rename "Run AI analysis" → "Run macro analysis" (or similar) — the UI should say what's actually running, consistent with this project's honesty-first ethos.

## Testing

- `test_backfill_baseline.py`: PCA sign-orientation correctness (VIX loading must end up positive), z-score/percentile math against a synthetic known distribution, output schema validation for the baked-in constants.
- A parity test mirroring the project's existing `test_freshness_parity.py` pattern: a small Python reference implementation recomputes the composite score + node multipliers from `data.json` + the baseline constants and asserts it matches what the JS module produces (extracted via headless Chrome) — so the two can't silently drift.
- Browser verification in `bullion_mkultra.html` via headless Chrome (standing project convention, isolated `--user-data-dir`): 0 console errors, real (non-placeholder) numbers rendering, health-bar color/width matching the computed score, audit log showing the new methodology section.

## Sources

- [National Financial Conditions Index: About the NFCI — Federal Reserve Bank of Chicago](https://www.chicagofed.org/research/data/nfci/about)
- [OFR Financial Stress Index — Office of Financial Research](https://www.financialresearch.gov/financial-stress-index/)
- [The St. Louis Fed's Financial Stress Index, version 3.0 — FRED Blog](https://fredblog.stlouisfed.org/2022/01/the-st-louis-feds-financial-stress-index-version-3-0/)
- [CISS — a composite indicator of systemic stress in the financial system — ECB](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1426.pdf)
