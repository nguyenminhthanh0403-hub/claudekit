# Mk Ultra — IMF Central-Bank Gold Reserves — Design

**Written:** 2026-08-12 · **Status:** approved by user, ready for `superpowers:writing-plans`

## Background

This is the first concrete scoping of the objective stated in
`docs/superpowers/bullion-mkultra-data-source-enrichment-handoff.md` (2026-08-11): grow
`bullion-live-map`'s live-data footprint beyond FRED + Yahoo's unofficial chart API.

That handoff named two candidate providers — an "official" Yahoo Finance tier and
Investopedia — as starting points. Research done in this brainstorming session found both to be
dead ends as originally imagined:

- **Yahoo Finance has no official/keyed first-party API.** Yahoo retired it years ago. The only
  options are the current unofficial chart endpoint, the `yfinance` library (a wrapper around the
  same unofficial endpoints), or paid third-party resellers on RapidAPI. None of these represent a
  reliability upgrade over what the project already does.
- **Investopedia has no data API at all.** It is a pure editorial/reference site; the only
  programmatic access is third-party scraping of its articles, a licensing/ToS gray area, not a
  real integration path.

Broadening the search across the data sources already named as citation standards in this
project's `CLAUDE.md` (FRED, BLS, Fed, BIS, WGC, IIF, WTO) surfaced two real candidates with actual
public APIs that fill genuine gaps (nodes with zero live backing today): IMF central-bank gold
reserves data, and WTO trade data. This design scopes **only the IMF gold-reserves field** — WTO
trade data is a separate, later candidate, not part of this spec.

## Goal

Add one new live field, `cb_gold_reserves` (total official/central-bank gold reserves), sourced
from the IMF's free, keyless SDMX 3.0 REST API, and use it to replace the `gold` node's currently
static, increasingly stale expert-text line ("Central-bank gold demand hit 1,037 tonnes in 2023...
Source: World Gold Council").

**Why this field specifically:** the World Gold Council itself has no public API — Goldhub is a
web dashboard, not a REST endpoint — but the central-bank reserves data WGC's own research cites is
compiled from IMF statistics. The `gold` node already cites WGC narratively with no live backing,
so this is a real gap-fill, not a novel addition to the map's scope.

**Important metric distinction, resolved during brainstorming:** IMF publishes reserves as a
**stock** (total gold held, at a point in time) — not the **flow** figure ("net tonnes purchased
that year") the current static WGC line shows. These are different metrics. Per the user's explicit
choice, the live stock figure **replaces** the static flow line entirely, rather than sitting
alongside it — the old sentence should not be preserved in a way that implies it's still current.

## Non-goals

- WTO trade data (a second real candidate found during research) — separate future effort, not
  scoped here.
- IMF COFER (USD reserve-currency share) — the `dxy_fx` node has the same kind of stale static IMF
  citation ("~60% of FX reserves... as of 2022") and would be a low-marginal-cost follow-up once
  this field's IMF-integration plumbing exists, but is explicitly out of scope for this plan to
  keep it focused.
- Any Yahoo or Investopedia integration — ruled out by research above.
- Any change to `bullion_mk11.html` through `bullion_mk18.html` (frozen files).

## Data flow / architecture

**Source:** IMF's SDMX 3.0 REST API at `data.imf.org`. Free, no API key, no new GitHub secret —
unlike a FRED/Yahoo-style addition, nothing needs provisioning in `daily-data.yml` or
`annual-baseline-refresh.yml`.

**Fetch:** `fetch_bullion_data.py` gains a new `fetch_imf_series()` function, structurally parallel
to the existing `fetch_fred_series()`. It requests the IMF endpoint with
`Accept: application/vnd.sdmx.json` and parses the response with stdlib `json` — no new pip
dependency, consistent with this script's current zero-third-party-dependency convention (confirmed
during this session: only `json`, `os`, `sys`, `urllib.error`, `urllib.request`, `datetime` are
imported today). The SDMX-JSON response shape is more deeply nested than FRED's flat series format;
`fetch_imf_series()` is responsible for descending to the single numeric value the rest of the
pipeline expects, in the same `(field_name, value)` shape `fetch_fred_series()` already produces.

**Integration into the existing pipeline:** the resolved value is folded into the same `latest_out`
dict FRED/Yahoo fields populate, so it flows through the existing all-or-nothing completeness gate
in `main()` unchanged. If the IMF fetch fails for any reason, `data.json` is not written — identical
behavior to any existing field failing today, no new failure-handling code path required.

**Cadence:** expected quarterly (IMF reserves data; exact publication lag confirmed during
implementation by observing real fetches, per this project's existing practice of calibrating
`CADENCE_TOLERANCE_DAYS` from observed lag rather than assumption). `CADENCE_TOLERANCE_DAYS`
currently has `daily`/`weekly`/`monthly`/`fomc` tiers only — this adds a new `"quarterly"` tier.

**Open research item carried into the implementation plan (not resolved by this design):** the
exact IMF dataflow/key for a world-aggregate gold reserves figure needs confirming. IMF may not
publish a single "World" entity for gold reserves specifically — if not, the field becomes a summed
basket of top public holders (e.g. US, Germany, Italy, France, Russia, China, India, Turkey) instead
of a true global total. This is a research task for the plan's first step, mirroring how the
existing FRED/Yahoo fields were originally scoped.

## Components / files touched

- **`bullion-live-map/fetch_bullion_data.py`**
  - New `IMF_SERIES`-shaped config, following the existing `{external_id: (field_name, ...)}`
    pattern used by `FRED_SERIES`.
  - New `fetch_imf_series()` function.
  - New `FIELD_META["cb_gold_reserves"]` entry (`class`, `cadence`, `source`).
  - New `"quarterly"` tier in `CADENCE_TOLERANCE_DAYS`.
- **`bullion-live-map/backfill_baseline.py`**
  - New `BASELINE_STATS` entry for `cb_gold_reserves`, added to `EXPECTED_BASELINE_FIELDS` so the
    existing `missing_baseline_fields()` completeness guard (added `6d45ad2`, this project's most
    recent baseline-hardening work) enforces it rather than silently omitting it.
  - Classification into `MEAN_REVERTING_FIELDS` vs `TRENDING_FIELDS` — likely mean-reverting, since
    a reserves level is a slow-moving stock rather than a trending flow, but confirmed once real
    data is pulled and its actual behavior is visible, not assumed up front.
- **`bullion_mkultra.html`**
  - `LIVE_FMT` / `NODE_LIVE_FIELD` / `LIVE_FIELD_LABEL` maps gain the new field.
  - The `gold` node's `expert` array has its static "Central-bank gold demand hit 1,037 tonnes in
    2023... Source: World Gold Council" line replaced with live-sourced reserves text citing IMF.
- **No workflow file changes** — no new secret needed.
- **`bullion-live-map/tests/`** — see Testing below.

## Error handling

Follows the project's existing convention exactly: `fetch_imf_series()` raises on any HTTP error,
unexpected SDMX-JSON shape, or missing/null value — same as `fetch_fred_series()` does today.
`main()`'s existing all-or-nothing gate means an IMF outage or an unannounced format change fails
the whole daily run (no `data.json` write) rather than silently shipping a partial map, exactly how
a FRED or Yahoo failure is already handled. No new failure-handling code path is required — only a
new field that plugs into the pipeline that already exists.

## Testing

- Unit test for `fetch_imf_series()` against a mocked SDMX-JSON response fixture — both a
  well-formed payload and a malformed/unexpected-shape one, proving the failure path raises rather
  than silently returning garbage.
- `backfill_baseline.py`'s `missing_baseline_fields()` guard test extended to cover the new field.
- **Live-fetch dry run** against the real IMF endpoint (not just the mocked fixture) as manual/final
  verification — this project's existing idiom (both `fetch_bullion_data.py` and
  `backfill_baseline.py` were run for real against live FRED/Yahoo APIs as part of the most recent
  session's verification, not just synthetic fixtures).
- Browser verification via the `headless-chrome-verification` skill confirming the `gold` node
  renders the new live text correctly.
- `sha256sum` check confirming `bullion_mk11.html` through `bullion_mk18.html` stay byte-unchanged.

## Alternatives considered

1. **Baseline-only, no visible node-text change.** Same fetch and baseline wiring, but without
   touching the `gold` node's displayed copy. Smaller diff, avoids any risk of the new stock figure
   being misread as the old flow figure — but ships an invisible number nobody sees, no user-facing
   payoff. Not chosen.
2. **Bundle IMF COFER (`dxy_fx` node) into the same plan.** Low marginal cost once IMF SDMX plumbing
   exists for the first field, since `dxy_fx` has the identical stale-static-citation problem. Not
   chosen for this plan — doubles the node/content surface touched in one pass; better as a fast
   follow-up once this field's plumbing is proven. Recorded above as an explicit non-goal.
