# Bullion Mk12 — Calibrate & Backtest (Design)

**Date:** 2026-07-22
**Status:** Approved scope, pending spec review
**Predecessor:** Mk11 (provenance audit, beginner mode, affected-only scenarios, CPI-rise fix)

## Thesis

Mk11 made the map's **arrows** true: every causal sign is sourced and tiered,
and `validateProvenance()` enforces sign-consistency at load. But the map still
prints its own biggest caveat in the impacts panel — *"directions are sourced,
magnitudes are not calibrated to live data."* Almost every coefficient is a
hand-set guess whose sign is defensible but whose size is a vibe.

Mk12 makes the **sizes** true where the data can support it, and — the headline —
makes the map **grade itself** against the year of history the live pipeline has
been quietly accumulating. The deliverable is not "better guesses"; it is a model
that shows, quantitatively and out-of-sample, where it tracks reality and where
it does not.

## Background / current state

- `bullion_mk11_constellation.html` — single-file D3 map. Two elasticity tables:
  - `ELASTICITY` — scenario engine, **driver → data-field** (fields are live time
    series). Drivers: `ffr, vix, cpi_yoy, dxy, wti_px`.
  - `NODE_ELASTICITY` — node recolouring, **driver → concept-node** (nodes have
    **no** time series).
- `data.json` — v2 envelope, 365 days of daily history, loaded into the page as
  `BULLION_LIVE_HISTORY`. The transmission model (`applyManual` / `applyTransmission`)
  is already in the page.
- `audit_fit_elasticities.py` — Mk11 one-off that fitted the two fittable cells
  (`wti→spx` adopted, `ffr→vix` rejected as unidentifiable). This is the seed for
  Mk12's calibration harness.

### Data reality (coverage as of 2026-07-22, 365 days)

| Field | Days | Fittable? |
|---|---|---|
| ffr | 362 | yes (driver) |
| vix | 257 | yes |
| dxy | 252 | yes |
| gold_px | 252 | yes |
| spx | 251 | yes |
| us10y | 249 | yes |
| us2y | 249 | yes |
| wti_px | 245 | yes |
| nfp_mom | 12 | **no — data-starved** |
| cpi_yoy | 11 | **no — data-starved** |

This coverage is the hard constraint on scope: only cells whose **both** driver
and target are dense daily series can be fitted or credibly backtested.

## Component A — Offline calibration (`calibrate.py`)

Extends `audit_fit_elasticities.py` into a repeatable calibration pass.

**What it fits:** every `ELASTICITY` cell where both driver and target are dense
series — the `{ffr, vix, dxy, wti_px}` drivers against the
`{us2y, us10y, vix, spx_pct, gold_pct, wti_pct}` targets (~10–15 cells, exact set
enumerated at build time from the live table).

**Method:**
- **First differences, not levels.** The Mk11 `ffr→vix` failure proved that levels
  regressions on persistent series produce spurious, wrong-signed fits. All fits
  are on consecutive-day changes, aligned on dates where both series are present.
- Pure stdlib OLS (Python 3.9 — no numpy/scipy/pandas; `statistics.linear_regression`
  is 3.10+). Reuse the hand-rolled OLS already in `audit_fit_elasticities.py`
  (slope, intercept, r, R², t-stat, regressor span).
- **Train/test split.** Fit on the first ~80% of aligned days; reserve the last
  ~20% untouched for the backtest, so a calibrated cell's accuracy score is
  genuinely out-of-sample rather than fit-to-the-test.

**Adoption rubric (unchanged from Mk11):** promote a cell to **MEASURED** only if
the fitted sign matches the hand sign, `|t| > 2`, and the regressor actually
varied over the window. Otherwise keep the hand value and attach the fit as a
DIRECTIONAL caveat. The script emits a report; adoption into the HTML is
**human-in-the-loop** (chosen over an auto-loaded fitted-values JSON) so every
coefficient stays reviewable in source with an explicit sourced comment — the
same discipline used for `wti→spx` in Mk11.

**Output:** a committed calibration report (per-cell: n, span, fitted slope, r, t,
verdict, adopt/keep) plus the hand-adopted coefficient/tier edits in the HTML.

## Component B — In-page live backtest (headline feature)

Both the history and the model are already loaded in the browser, so the backtest
runs **client-side** with no server and no build step.

**Algorithm (first-difference, contemporaneous):**
- For each consecutive-day pair `(t-1, t)` in `BULLION_LIVE_HISTORY` where the
  required driver and target fields are present on both days:
  - predicted `Δtarget = Σ ELASTICITY(driver → target) × Δdriver`
  - actual `Δtarget = target[t] − target[t-1]`
- Restrict scoring to the **held-out tail** (the ~20% the calibration did not see)
  for fitted cells; hand-set cells are out-of-sample on all days.

**Metrics, per target field and aggregate:**
- **Direction hit-rate** — fraction of moved days where `sign(predicted) == sign(actual)`.
- **Magnitude fit** — R² and RMSE of predicted vs. actual `Δ`.

**UI surface:** a new Audit Log section — **"Model accuracy — backtested on N days
(out-of-sample)"** — a per-field table of hit-rate + R², rendered from the live
history at open time. Colour each field by how well it tracks (reuses the
measured/directional/unverified palette).

**Honesty caveats stated in the panel (not hidden):**
- This is a **contemporaneous same-day** test — it measures whether the model's
  co-movement matches history, **not** whether it can *forecast* (no lag modelled).
- Fitted cells scored on the held-out tail are out-of-sample; hand-set cells are
  out-of-sample throughout. The distinction is labelled per row.
- Node colours (`NODE_ELASTICITY`) are **not** in the backtest — their targets have
  no series. The panel says so, so a good field-level score is never mistaken for
  validation of the node layer.

## Non-goals (YAGNI)

- **No fitting of `NODE_ELASTICITY`.** Concept nodes have no time series. The node
  colour layer stays hand-set and honestly labelled, exactly as Mk11 left it.
- **No `cpi_yoy` / `nfp_mom` fits.** ~11 observations cannot support a coefficient;
  these cells stay hand-set and are flagged data-starved.
- **No feedback loops / multi-pass dynamics / time-lag modelling.** That was a
  separate candidate direction, deliberately excluded — it would add unverified
  structure against the provenance discipline Mk11 established.
- **No new nodes/layers.** Breadth without calibration just multiplies unverified
  claims.

## Folded-in fixes (carried from Mk11 review)

1. **`runManual` bug** (~line 3398–3400): it calls `validateProvenance()` and
   re-binds the Audit Log click listener on *every* slider move — the comment says
   "once, at boot," but the code sits in the wrong function. Move validation +
   binding to boot; stop the duplicate-listener accumulation.
2. **The 0.05 colour/expand threshold.** Single-driver scenarios light only 1–2
   nodes because most coefficients fall under it. Make a deliberate call — a lower
   global cutoff, or a per-scenario relative cutoff — informed by the calibrated
   magnitudes rather than left implicit.
3. **The two weakest hand-asserted scenarios** — `fiscal_tightening`'s
   "unjustified" asymmetry vs. stimulus, and `deregulation`'s 2006-vintage sign
   assumption. Either defend, re-sign, or label louder.

## Provenance integrity

- Calibration never silently overwrites a coefficient. Every adopted fit lands in
  source with a sourced comment naming the script, n, span, slope, r, t.
- `validateProvenance()` continues to run at load and must stay green (sign
  consistency between `ELASTICITY`, `NODE_ELASTICITY`, and `LINKS`). Any fit that
  would flip a sign is a conflict to resolve explicitly, not adopt blindly.
- The backtest is descriptive, not a gate: a poor field score is surfaced, not
  suppressed — that is the whole point.

## Risks / open questions

- **In-sample flattery.** Mitigated by the train/test split; without it, calibrated
  cells would score their own training data. The held-out tail is ~50 days — small,
  so report n alongside every score and avoid over-claiming.
- **Contemporaneous ≠ causal.** Same-day co-movement can reflect a common driver
  (e.g. vix/spx is partly an identity). Keep the existing per-cell caveats; the
  backtest sits beside them, it does not replace them.
- **Sparse-driver scenarios stay uncalibrated.** `cpi_rise` etc. remain hand-set;
  the map must not imply otherwise.
- **Regime dependence.** One year is one regime. A cell that fits 2025–26 may fail
  out of period. State the window explicitly.

## Success criteria

1. `calibrate.py` runs stdlib-only, emits a per-cell report, and its adopted fits
   are reflected in the HTML with sourced comments and correct tiers.
2. At least the cells that pass the rubric are promoted to MEASURED; the rest keep
   hand values with the fit shown as caveat. No cell is silently changed.
3. The Audit Log shows a per-field "Model accuracy" table computed live from
   loaded history, on the held-out window, with the three honesty caveats visible.
4. `validateProvenance()` stays green.
5. The three folded fixes are resolved.
6. Everything remains a single openable file with no build step; the calibration
   script is offline and not part of the daily pipeline.
