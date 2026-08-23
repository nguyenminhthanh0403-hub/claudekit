# Mk Ultra — Multi-Year Calibration History — Design

**Written:** 2026-08-23, derived directly from an in-conversation accuracy review (no
separate brainstorming session — the tradeoffs below were worked through interactively
before this doc was written).

## Problem

`calibrate.py` fits every `ELASTICITY` cell and `LINKS` row against `data.json`'s
`history`, which only ever carries the trailing ~365 days (`fetch_bullion_data.py`
rebuilds it from scratch on every cron run — it is not an accumulating log). Three
monthly-cadence FRED series — `cpi_yoy`, `nfp_mom`, `m2` — publish roughly 12 points a
year, so a 366-day window yields only 8-12 daily first-differences per series: any link
touching them (`cpi→fomc`, `nfp→fomc`, `oil→cpi`, `ffr→m2`, `m2→cpi`, `m2→gold`) hits
`calibrate.py`'s own `MIN_LINK_N=30` floor and is correctly left `DIRECTIONAL` — not
because the relationship is false, but because there is not enough data to test it.
Confirmed against the live `calibration_report.txt` (2026-08-23): those 6 links show
n=3..9.

## Goal

Give `calibrate.py` a wider-window history file so those 6 links become genuinely
testable (n≥30), without changing what the live map fetches on page load.

## Non-goals (rejected during the conversation that led to this doc)

- **Adding new equity tickers (Nasdaq, a Vanguard fund).** `spx` (S&P 500) is already
  live and is the single strongest-fitted link in the graph (`vix→spx`, t=-22.2).
  Nasdaq is ~90%+ correlated with `spx` day-to-day; a Vanguard fund like VOO/VTI tracks
  the S&P 500 at ~0.999 correlation. Neither adds real new information, and neither
  addresses the actual bottleneck, which is monthly-cadence FRED series having too few
  data points — not a missing equity series.
- **Bumping `fetch_bullion_data.py`'s `HISTORY_DAYS` directly.** Two problems: (1) that
  history ships as-is in `data.json`, which `bullion_mkultra.html` fetches on every
  page load — a 5-6x wider window means a 5-6x larger client payload for a feature
  users never see (the date-picker doesn't need years of daily granularity). (2) FRED
  rejects a realtime-range request once its vintage count exceeds 2000
  (`backfill_baseline.py`'s `_fetch_fred_history_only` docstring, verified against the
  live API 2026-08-09) — `fetch_fred_series`'s realtime-range request (used to recover
  each observation's publication date) would hit that cap over a multi-year window for
  a daily series like `DGS2`. `backfill_baseline.py` already solved this for its own
  15-year pull; this effort reuses that solution rather than re-deriving it.
- **A rolling/expanding-window backtest.** Real, but separate scope — noted as a
  follow-up in the conversation, not addressed here.

## Design

A new script, `fetch_calibration_history.py`, reuses `backfill_baseline.fetch_all_history()`
(the same fetcher the annual `BASELINE_STATS` refresh already relies on) to pull a
**6-year** window — long enough to clear `MIN_LINK_N=30` for monthly series with real
margin (~72 monthly observations vs. the ~39 needed for a 31-point 80%-training split),
short enough to avoid mixing in pre-2020 rate regimes (ZIRP, the 2008 GFC) that may not
represent how these series relate today. It writes a separate file,
`calibration_history.json`, in the same `{"history": {date: {field: value}}}` envelope
shape `calibrate.py` and `audit_fit_elasticities.py` already accept — so neither needs
a code change to consume it; `calibrate.py` is invoked as
`python3 calibrate.py calibration_history.json bullion_mkultra.html <report_path>`.

`calibrate.py` gains one small, backward-compatible change: `main()`'s hardcoded output
filename (`'calibration_report.txt'`) becomes an optional third CLI argument, defaulting
to the same value. This lets the wide-window run write its own report
(`calibration_report_multiyear.txt`) instead of silently overwriting the tracked report
that documents the production `data.json` window — the two audits stay distinguishable.
No existing caller passes a third argument, so this is a pure addition; `test_calibrate.py`
has no test on `main()`'s I/O today (confirmed by reading it), so nothing breaks.

`calibration_history.json` is gitignored — a regenerable offline artifact (rerunning the
script reproduces it byte-for-byte modulo new daily data), analogous to `raw_cache_johnny/`
already in `.gitignore`. `calibration_report_multiyear.txt` IS tracked, same convention as
the existing `calibration_report.txt`.

## Files touched

- Create: `bullion-live-map/fetch_calibration_history.py`
- Create: `bullion-live-map/tests/test_fetch_calibration_history.py`
- Modify: `bullion-live-map/calibrate.py` (optional 3rd arg for report output path)
- Modify: `bullion-live-map/.gitignore` (add `calibration_history.json`)
- Create (generated, then committed): `bullion-live-map/calibration_report_multiyear.txt`
- Modify (conditionally, per the adoption pass): `bullion-live-map/bullion_mkultra.html` —
  only if the wider window actually promotes a link to `measured`, or flags a `[FLIP]`
  that the user confirms.

## Error handling

Same "never publish a partial artifact" convention as `fetch_bullion_data.py` and
`backfill_baseline.py`: if any expected field's history comes back empty,
`fetch_calibration_history.py` prints which field(s) and exits non-zero without writing
`calibration_history.json`, leaving any previous run's file untouched.

## Testing

Pure-function unit tests for the field-major→date-major transpose and the
completeness check (no network needed), plus one guard test using the project's
established module-level fake-injection pattern (`import fetch_calibration_history as
fetch_calibration_history_module`, replace `.fetch_all_history`/`.load_key` with fakes,
matching `tests/test_fetch_bullion_data.py`'s style exactly).

## Adoption policy for newly-testable links

Unchanged from this project's existing rubric (`calibrate.py`'s `link_verdict`): promote
to `measured` only on sign-match with `|t|>2`; a `[FLIP]` (data contradicts the current
hand-asserted arrow at significance) is surfaced to the user, never auto-applied — the
same policy that produced the 4 sign flips (`credit→equit`, `usd→oil`, `vix→defn`,
`mortgage_30y→credit`) during the original 2026-07-27 honesty pass.

## Open questions

- None blocking. The 6-year window is a judgment call, not a hard requirement — if the
  resulting `calibration_report_multiyear.txt` still shows any of the 6 target links
  under n=30 (unlikely, but FRED could have gaps), the fix is bumping
  `CALIBRATION_WINDOW_YEARS`, not a design change.
