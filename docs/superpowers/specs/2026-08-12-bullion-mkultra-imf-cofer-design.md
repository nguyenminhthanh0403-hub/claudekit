# Mk Ultra — IMF COFER (USD Reserve-Currency Share) — Design

**Written:** 2026-08-12 · **Status:** approved by user, ready for `superpowers:writing-plans`

## Background

This is the fast-follow named as a non-goal in the prior IMF gold-reserves design
(`docs/superpowers/specs/2026-08-12-bullion-mkultra-imf-gold-reserves-design.md`): "IMF COFER (USD
reserve-currency share) ... would be a low-marginal-cost follow-up once this field's IMF-integration
plumbing exists." That plumbing now exists (`fetch_bullion_data.py`'s `parse_imf_sdmx`-style pattern,
proven against the live IMF SDMX 3.0 API).

**Correction to the prior handoff:** the stale "~60% of FX reserves... as of 2022" citation was
previously misattributed to the `dxy_fx` node ("EM FX / Global FX"). It is actually on the **`usd`**
node ("US Dollar (DXY)") — verified by reading the live source at `bullion_mkultra.html` line 1210.
`dxy_fx`'s own stale citation is unrelated (EM external debt, from IIF/IMF WP/19/25) and out of scope
here.

## Goal

Add a new live field, `usd_reserve_share` (percent of allocated global official FX reserves held in
USD), sourced from IMF's free, keyless COFER (Currency Composition of Official Foreign Exchange
Reserves) dataflow, and use it to replace the reserve-share half of the `usd` node's stale sentence.

## Non-goals

- The trade-invoicing half of the original sentence ("40 to 50% of trade invoices... as of 2022") —
  COFER does not cover invoicing shares and no live source for it is in scope. Per the user's explicit
  choice, this becomes its own honestly-dated static sentence rather than being dropped or left
  implying it is still current.
- `dxy_fx` node — its stale citation is a different metric (EM external debt) with no COFER
  relationship; not touched by this plan.
- Any other COFER breakdown (EUR share, JPY share, "unallocated" reserves, etc.) — only the USD
  allocated share is scoped.
- Any change to `bullion_mk11.html` through `bullion_mk17.html` (frozen files). `bullion_mk18.html` is
  NOT frozen (see `tests/test_freshness_parity.py`) but per the user's prior, still-standing choice on
  this exact question (made during the gold-reserves work), only gets the minimal tolerance-table sync
  needed to keep that parity test green — not the full node-text/live-map feature.

## Data flow / architecture

**Source:** IMF's COFER dataflow, `IMF.STA:COFER(7.0.1)`, same free/keyless SDMX 3.0 REST API used for
`cb_gold_reserves`. Key: `G001.AFXRA.CI_USD.SHRO_PT.Q` — `G001` (World), `AFXRA` (Allocated foreign
exchange reserves), `CI_USD` (claims in US dollar), `SHRO_PT` (Shares, i.e. already a percentage — no
unit conversion needed), `Q` (quarterly, the only frequency this indicator publishes at; no monthly
data exists, confirmed against the live API).

**Structurally simpler than gold reserves:** IMF publishes a genuine `COUNTRY=G001` ("World") series
for COFER with real data (confirmed live, e.g. 2026-Q1 = 57.13%) — unlike IRFCL gold reserves, where
`G001` returned nothing and an 11-country basket was required. This is a single fetch and parse, not a
basket-sum-and-intersect.

**Fetch:** `fetch_bullion_data.py` gains `fetch_usd_reserve_share(start, end)`, parallel in shape to
`fetch_imf_gold_reserves_basket` but without the multi-country composition step. Uses the same
`c[TIME_PERIOD]=ge:...` filter syntax discovered during the gold-reserves work (not `startPeriod`,
which that endpoint family silently ignores — to be re-verified against this specific dataflow during
implementation rather than assumed identical). Returns the same `(value, ref_date, published, history)`
4-tuple shape as every other fetcher, and does not raise — returns the all-None/empty tuple on any
failure, matching the established convention.

**Integration:** folds into the existing `latest_out`/`history_by_date` pipeline in `main()`, subject to
the same all-or-nothing completeness gate as every other field.

**Cadence / tolerance:** real cadence is quarterly, confirmed via live query (only `Q` and derived `A`
frequencies exist, no `M`). Observed lag as of 2026-08-11: latest available point is 2026-Q1 (quarter
ended 2026-03-31), ~134 days old. `CADENCE_TOLERANCE_DAYS` has no `"quarterly"` tier today — this adds
one, set to **180 days** (a ~40% cushion over the observed 134-day lag, matching the cushion ratio this
project's existing overrides use). Unlike `monthly`'s tier (calibrated from multiple fields observed
over time), this is a first calibration from a single data point and should be revisited once more
COFER quarters have been observed in production — flag this in a code comment, not just here.

**Ref/publish date:** like gold reserves, COFER's SDMX response carries no separate publication/vintage
date, only a reference period. `ref_date` and `published` are both set to the end-of-quarter date (e.g.
`2026-03-31` for `2026-Q1`).

## Components / files touched

- **`bullion-live-map/fetch_bullion_data.py`**
  - `IMF_COFER_BASE_URL`, `IMF_COFER_INDICATOR` (`AFXRA`), `IMF_COFER_CURRENCY` (`CI_USD`),
    `IMF_COFER_TRANSFORM` (`SHRO_PT`) constants.
  - `fetch_usd_reserve_share(start, end)` — network wrapper + inline pure parse (or a separate
    `parse_cofer_sdmx` pure function if the response shape genuinely differs enough from
    `parse_imf_sdmx` to warrant its own parser; to be determined during implementation against the
    real payload shape, not assumed identical).
  - New `"quarterly": 180` tier in `CADENCE_TOLERANCE_DAYS`.
  - `FIELD_META["usd_reserve_share"]` entry (`class: measured`, `cadence: quarterly`,
    `source: IMF COFER`).
  - `main()` wiring: one more explicit fetch-and-append block, same pattern as `cb_gold_reserves`.
  - `SOURCE_NOTE` gains a sentence.
- **`bullion-live-map/backfill_baseline.py`**
  - `usd_reserve_share` added to `TRENDING_FIELDS` (27-year history shows a clear secular decline, not
    mean reversion) and `FORWARD_FILL_FIELDS` (quarterly-native data is even sparser than
    `cb_gold_reserves`'s monthly).
- **`bullion-live-map/bullion_mkultra.html`**
  - `usd` node's `expert` array: the reserve-share sentence becomes live-tracking text (no hardcoded
    number, matching every other live-bound node's convention); the invoicing clause becomes its own
    honestly-dated sentence. **Self-review correction:** the original combined source line ("BIS and
    IMF COFER (reserve and invoicing shares, 2022)") most plausibly attributes the reserve-share figure
    to COFER and the invoicing figure to BIS (BIS is the standard publisher of trade-invoicing-currency
    data; COFER does not cover invoicing at all) — so the source line splits accordingly rather than
    dropping BIS outright: the reserve-share sentence cites "IMF COFER", and the now-separate invoicing
    sentence keeps its own "Source: BIS" so that fact is not left uncited once it is no longer bundled
    with COFER's line. ICE (DXY index weights) is unrelated to either and stays on its own line.
  - `LIVE_FIELD_LABEL`, `LIVE_FMT` (percentage formatter, e.g. `v=>(+v).toFixed(1)+'%'`), and
    `NODE_LIVE_FIELD` (`usd: ['dxy', 'usd_reserve_share']`) gain the field.
- **`bullion-live-map/bullion_mk18.html`**
  - Only `CADENCE_TOLERANCE_DAYS`'s new `"quarterly": 180` entry synced into its JS mirror, to satisfy
    `tests/test_freshness_parity.py::test_live_maps_match_python_cadence_tolerances`. No node-text or
    live-field-map changes, per the user's standing choice on this exact question.
- No new GitHub Actions secret, no workflow file changes — COFER needs no API key.
- **`bullion-live-map/tests/`** — see Testing below.

## Error handling

Identical convention to `cb_gold_reserves`: any HTTP error, unexpected SDMX-JSON shape, or missing/null
value causes `fetch_usd_reserve_share()` to return `(None, None, None, {})` rather than raise. `main()`'s
existing all-or-nothing gate means a COFER outage or format change fails the whole daily run (no
`data.json` write), identical to how every other field's failure is already handled. No new
failure-handling code path required.

## Testing

- Unit tests for the COFER response parser against mocked SDMX-JSON fixtures (well-formed and
  malformed/unexpected-shape), proving the failure path returns empty rather than raising or returning
  garbage.
- `backfill_baseline.py`'s completeness-gate test (`missing_baseline_fields()`) extended to cover the
  new field.
- **Live-fetch dry run** against the real COFER endpoint (not just the mocked fixture), following this
  project's established idiom.
- `tests/test_freshness_parity.py` must stay green for both live maps after the new `"quarterly"` tier
  is added to Python and synced into both `bullion_mkultra.html` and `bullion_mk18.html`.
- Browser verification via the `headless-chrome-verification` skill confirming the `usd` node renders
  the new live percentage and the split node text correctly.
- `sha256sum` check confirming `bullion_mk11.html` through `bullion_mk17.html` stay byte-unchanged.

## Alternatives considered

1. **Reuse `parse_imf_sdmx` unchanged for COFER.** The IRFCL and COFER dataflows are both IMF SDMX 3.0
   and may share an identical response shape, in which case the existing parser could be reused
   directly instead of writing a near-duplicate. Not decided here — the implementation plan's first
   step should fetch a real COFER payload and diff its shape against IRFCL's before choosing to reuse or
   fork the parser, the same "verify before assuming" discipline the gold-reserves work applied to its
   own open research item.
2. **Drop the trade-invoicing clause instead of preserving it as static.** Simpler diff, but discards a
   real (if unsourced-live) data point. Not chosen — the user's explicit preference was to preserve it,
   honestly dated.
