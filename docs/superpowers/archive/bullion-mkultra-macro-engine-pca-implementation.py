"""Archived: the PCA-weighted composite scoring implementation removed from
backfill_baseline.py on 2026-08-11.

This code is CORRECT (does what it says) but its OUTPUT was found inverted
under real financial stress -- see the full diagnosis:
  - docs/superpowers/plans/2026-08-09-bullion-mkultra-macro-engine.md
    (search "## Addendum (2026-08-11)")
  - docs/superpowers/archive/bullion-mkultra-macro-engine-pca-sign-invariance-proof.md
  - docs/superpowers/specs/2026-08-11-bullion-mkultra-composite-score-fix-design.md
    (the replacement methodology's design)

Root cause, briefly: PCA fit over the only window where all 11 original
composite fields had comparable history (~2yr, bounded by hy_oas/ig_oas's
short FRED retention) put ~90% of its weight on nominal rate levels, not
stress. A proposed sign-alignment fix was proven a mathematical no-op (PCA
is invariant to per-column sign flips).

Preserved here, not deleted, in case a materially longer fitting window
becomes viable later (blocked as of 2026-08-11 by hy_oas/ig_oas's ~3yr real
FRED data ceiling -- verify that constraint still holds before reviving
this) and PCA-discovered weights are worth retrying. Not imported or
executed by anything -- copy relevant pieces back into backfill_baseline.py
if reviving.
"""
import math
import random


def build_zscore_rows(history, stats_by_field, fields):
    """Dates (sorted) and z-scored rows where every field in `fields` is present.

    Each row is clipped to +/-3 per field, matching the client-side engine's
    clipping so the historical composite distribution used for percentile
    lookup is built the same way the live score will be computed.
    """
    date_sets = [set(history[f].keys()) for f in fields]
    common = sorted(set.intersection(*date_sets)) if date_sets else []
    rows = []
    for d in common:
        row = []
        for f in fields:
            s = stats_by_field[f]
            z = (history[f][d] - s["mean"]) / s["std"] if s["std"] else 0.0
            row.append(max(-3.0, min(3.0, z)))
        rows.append(row)
    return common, rows


def pca_first_component(rows, n_iter=500, seed=1):
    """First principal component via power iteration on X^T X / n (rows are
    already z-scored, i.e. approximately mean-zero per column, so this is
    power iteration on the covariance matrix without building it explicitly).
    """
    n_fields = len(rows[0])
    n_rows = len(rows)
    rnd = random.Random(seed)
    v = [rnd.random() - 0.5 for _ in range(n_fields)]

    def normalize(vec):
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    v = normalize(v)
    for _ in range(n_iter):
        xv = [sum(row[j] * v[j] for j in range(n_fields)) for row in rows]
        w = [sum(xv[i] * rows[i][j] for i in range(n_rows)) / n_rows for j in range(n_fields)]
        v = normalize(w)
    return v


def orient_loadings(loadings, fields, anchor_field="vix"):
    idx = fields.index(anchor_field)
    if loadings[idx] < 0:
        return [-x for x in loadings]
    return list(loadings)


def percentile_table(values, n_points=101):
    ordered = sorted(values)
    last = len(ordered) - 1
    return [ordered[round(p / (n_points - 1) * last)] for p in range(n_points)]


# === Composite-specific block from build_baseline() ===
# This block was part of build_baseline() and is preserved here to document
# how the PCA-based composite score was computed before removal.
#
# The row matrix that feeds the PCA fit AND the percentile table must use
# a date range consistent with EVERY composite field's own baseline
# window -- not just whatever the raw date intersection happens to
# allow. TRENDING_FIELDS (spx/fed_bs/rrp) are z-scored against only
# their trailing RECENT_WINDOW_YEARS mean/std (see the loop above); any
# row older than that window compares those three fields' actual level
# against a mean that didn't apply to that era, producing an artificial
# step-discontinuity (verified empirically: dates >2yr old clip to
# z=-3 on all three trending fields simultaneously, producing a
# composite value ~6 units away from anything in the recent window --
# not a gradual trend, a computation artifact). So the row matrix is
# restricted to the same trailing window, for every field, even though
# MEAN_REVERTING_FIELDS' own stats (fields_out, above) still use their
# full FULL_WINDOW_YEARS sample -- only the composite's row matrix
# (PCA fit + percentile table) is windowed, not each field's baseline.
#
# Setup code (from build_baseline):
#   recent_cutoff = (datetime.now(timezone.utc) - timedelta(days=365 * RECENT_WINDOW_YEARS)).strftime("%Y-%m-%d")
#   history_for_rows = {f: {d: v for d, v in h.items() if d >= recent_cutoff} for f, h in history.items()}
#
# KNOWN UNRESOLVED ISSUE (2026-08-11): even with the windowing above,
# PCA fit over this ~2yr sample concentrates ~90% of its weight on
# nominal rate levels, not stress -- vix/spx/credit-spreads contribute
# ~0%, because the window contains no real stress episode for them to
# correlate around. This makes the resulting composite score unreliable
# (verified: a synthetic full crisis scored 100/"Healthy"). A sign-
# alignment fix was attempted and proven mathematically impossible
# (PCA is invariant to per-column sign flips -- see git history /
# session notes for the proof). computeCompositeScore in
# bullion_mkultra.html is consequently NOT called from the live UI as
# of this commit. This function and its output are otherwise left
# intact for whoever revisits the methodology.
#
# Original location in build_baseline() (final assignments and return):
#   dates, rows = build_zscore_rows(history_for_rows, fields_out, COMPOSITE_FIELDS)
#   loadings = orient_loadings(pca_first_component(rows), COMPOSITE_FIELDS, anchor_field="vix")
#   pc1 = dict(zip(COMPOSITE_FIELDS, loadings))
#   composite_series = [sum(row[i] * loadings[i] for i in range(len(loadings))) for row in rows]
#
#   return {
#       "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
#       "fields": fields_out,
#       "pc1_loadings": pc1,
#       "composite_percentiles": percentile_table(composite_series) if composite_series else [],
#       # The composite's OWN lookback window -- distinct from any single
#       # field's window_years (which can be up to FULL_WINDOW_YEARS). The
#       # narrative (Task 6) must cite this, not a field's window_years, when
#       # describing how far back the composite score's percentile ranking goes.
#       "composite_window_years": RECENT_WINDOW_YEARS,
#   }
