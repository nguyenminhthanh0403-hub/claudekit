# Final-review fix wave — BLOCKED on Fix 1

**Status: BLOCKED.** Fix 1 (sign-align inputs before PCA) was applied exactly as
specified and is a **mathematical no-op**. It changed the exported
`pc1_loadings` by **0.000e+00** — bit-for-bit identical to the buggy values.
The C1 bug is completely unfixed.

Nothing has been committed. All changes are in the working tree only.

---

## 1. Diagnosis: which of (a)/(b)/(c)?

**(b) — the fix was applied correctly, but the math does not do what the fix
design assumed.**

Ruled out explicitly:

- **(a) not applied correctly** — ruled out. All three pieces are present and
  verbatim: `EXPECTED_STRESS_SIGN` at `backfill_baseline.py:61`, rewritten
  `orient_loadings` at `:224`, rewritten `build_baseline` PCA block at
  `:317-327`.
- **(c) stale BASELINE_STATS** — ruled out. `python3 backfill_baseline.py` ran
  successfully against live FRED/Yahoo (`BASELINE_STATS refreshed: 16 fields,
  101 percentile points`) and the splice *did* land: Fix 2's `window_years`
  change is visibly present in the regenerated HTML (`hy_oas` went
  `15` → `3.0`, `sofr` → `8.4`, `cpi_yoy` → `14.8`). Same regeneration,
  same code path, same write — the loadings simply did not move.

### The root cause: PCA is invariant under ±1 column flips

Let `D = diag(EXPECTED_STRESS_SIGN)`, so `D² = I`. Sign-aligning the inputs
forms `X_signed = X·D`, whose covariance is

```
C_signed = Dᵀ C D = D C D
```

If `C v = λv`, then

```
C_signed (D v) = D C D D v = D C v = λ (D v)
```

So the eigenvector of the signed matrix is **exactly `D v`** — the same
vector with the same signs applied. Fix 1 then multiplies it back by `D` to
export "effective loadings":

```
pc1[f] = oriented[f] · SIGN[f] = (SIGN[f] · v[f]) · SIGN[f] = v[f]
```

`SIGN² = 1`, so the sign alignment **cancels itself exactly**. The exported
loadings are algebraically forced to equal the un-aligned PCA loadings.

The algebra quoted in the Fix 1 instructions —
`effective_loading[f]·raw_z[f] == oriented[f]·SIGN[f]·raw_z[f]` — is correct,
but it only proves the *export is faithful to the fit*. It does not (and
cannot) change what the fit found. That is the flaw in the design.

The **only** degree of freedom sign-alignment leaves is the single global
flip, and on this data that flip resolves the same way both rules do (see §2).

**Empirical confirmation of the invariance** (synthetic 800×11 matrix with an
arbitrary common factor, run through the real `pca_first_component`):
`max |v_signed[j]·sign[j] − v_raw[j]| = 1.39e-17` — machine epsilon.

---

## 2. The actual computed numbers

### Regenerated `pc1_loadings` (post-Fix-1) vs. what the OLD code exports

Fitted on the real cached 15yr history; row matrix **493 rows × 11 fields,
2024-08-12 .. 2026-08-06**.

| field | raw unoriented | signed unoriented | signed **oriented** | **EXPORTED (new)** | OLD code | diff |
|---|---|---|---|---|---|---|
| hy_oas | +0.181396 | +0.181396 | −0.181396 | **−0.181396** | −0.181396 | 0.00e+00 |
| ig_oas | +0.189321 | +0.189321 | −0.189321 | **−0.189321** | −0.189321 | 0.00e+00 |
| sofr | −0.295187 | −0.295187 | +0.295187 | **+0.295187** | +0.295187 | 0.00e+00 |
| tbill_3m | −0.488238 | −0.488238 | +0.488238 | **+0.488238** | +0.488238 | 0.00e+00 |
| us10y | −0.585181 | −0.585181 | +0.585181 | **+0.585181** | +0.585181 | 0.00e+00 |
| us2y | −0.478922 | −0.478922 | +0.478922 | **+0.478922** | +0.478922 | 0.00e+00 |
| curve_slope | +0.182359 | −0.182359 | +0.182359 | **−0.182359** | −0.182359 | 0.00e+00 |
| vix | −0.009202 | −0.009202 | +0.009202 | **+0.009202** | +0.009202 | 0.00e+00 |
| spx | +0.003846 | −0.003846 | +0.003846 | **−0.003846** | −0.003846 | 0.00e+00 |
| fed_bs | −0.020647 | +0.020647 | −0.020647 | **+0.020647** | +0.020647 | 0.00e+00 |
| rrp | −0.012564 | +0.012564 | −0.012564 | **+0.012564** | +0.012564 | 0.00e+00 |

**max diff = 0.000e+00.** Note columns 2 and 3 differ only where `SIGN = −1`
(curve_slope, spx, fed_bs, rrp) — exactly the `D v` relationship above.

**The two loadings the fix was supposed to correct are unchanged and still
negative: `hy_oas = −0.181396`, `ig_oas = −0.189321`.** Wider credit spreads
still LOWER the stress reading.

Cross-check against the pre-fix HTML (extracted before regeneration):
`hy_oas −0.181395`, `ig_oas −0.189320` — matching to 5 decimals (the 1e-6
wobble is power-iteration seed noise, not a real change).

### `sum(loadings)` before/after orientation

```
sum(v_raw_unoriented)     = -1.333021
sum(v_signed_unoriented)  = -1.639007   -> new sum-rule flips? YES
sum(v_signed_oriented)    = +1.639007

OLD anchor rule (vix loading > 0): vix_raw = -0.009202 -> flips? YES
```

Both the new sum rule and the old vix-anchor rule decide **flip**, so even the
one genuine degree of freedom lands identically. The new orientation rule is a
real robustness improvement in principle (it no longer hinges on a field
carrying 0.0% of the weight), but on this data it is not load-bearing.

### What PC1 is actually measuring

```
PC1 variance explained: 61.8%
loading² share:  us10y 34.2% | tbill_3m 23.8% | us2y 22.9% | sofr 8.7%
                 ig_oas 3.6% | curve_slope 3.3% | hy_oas 3.3%
                 fed_bs 0.0% | rrp 0.0% | vix 0.0% | spx 0.0%
```

**89.6% of PC1's weight sits on the four nominal rate-level series.** Credit,
volatility and equities together carry ~10%. This is the original C1 finding,
untouched.

The mechanism is visible in the per-field z-score dispersion *inside the fit
window*:

```
field         mean_z    std_z
us10y         +1.555    0.211
tbill_3m      +1.299    0.204
us2y          +1.265    0.168
sofr          +0.782    0.244
hy_oas        -0.422    0.727
ig_oas        -0.473    0.609
vix           +0.068    0.601
spx           -0.007    0.996
```

The rate series sit ~1.3–1.6σ above their 15yr means and barely move (std_z
≈ 0.2), while spx/fed_bs/rrp are z-scored against their own 2yr window so they
have std_z ≈ 1.0. PCA weights by *covariance*, and the four rate series move
together tightly and persistently — so PC1 locks onto the level-drift of the
rate complex. No amount of pre-fit sign flipping changes which direction has
the most covariance.

### Behavioural repro (via `node`, against the regenerated shipped HTML)

| scenario | composite | score |
|---|---|---|
| all fields at their own mean | ~0.00 | **100** |
| synthetic CRISIS (hy +2σ, ig +2σ, vix +2σ, spx −2σ) | **−0.715** | **100** |
| synthetic CALM (hy −1σ, ig −1σ, vix −1σ, spx +1σ) | **+0.358** | **100** |
| reviewer repro (VIX 45, HY OAS 8%, SPX −35%) | **−0.505** | **100** |

Crisis category contributions: `Credit −0.7414`, `Volatility +0.0184`,
`Equity valuation +0.0077`.

Two separate problems are visible here:

1. **Direction still inverted.** The crisis composite (−0.715) is *lower* than
   the calm composite (+0.358) — credit stress subtracts. Unchanged by Fix 1.
2. **The composite scale is offset from the percentile table** (a second,
   previously unreported issue). The table spans `[+1.540, +3.383]`, but every
   scenario above — including all-fields-at-their-mean — produces a composite
   well *below* +1.540, so `_percentileRank` saturates at 0 and every one of
   them scores **100**. This is the regime mismatch the existing
   `test_all_fields_at_their_own_mean...` docstring gestures at, but it is
   worse than "doesn't land near 50": a large region of realistic input space
   is unreachable and pins at maximally-healthy. This would need addressing
   regardless of how C1 is resolved.

---

## 3. Candidate corrections (evaluated, NOT applied)

Run read-only against the real cached history, refitting and rebuilding the
percentile table for each. Reported for the coordinator's decision only — no
repo code was changed.

| approach | hy_oas | crisis | calm | reviewer repro | direction correct? |
|---|---|---|---|---|---|
| **Fix 1 as specified (shipped)** | −0.1814 | 100 | 100 | 100 | **NO** |
| **A: `\|PCA\|` × expected sign** | +0.1814 | 100 | 100 | 100 | **NO** |
| **B: sign-aligned equal-weight z** | +0.0909 | **6** | 100 | **5** | **YES** |

- **Candidate A** (keep PCA magnitudes, force each exported loading to its
  expected sign) fixes the *loading signs* — `hy_oas` becomes +0.1814 — but
  still fails the ground-truth test, because rate levels still carry ~90% of
  the weight and the scale-offset problem (§2, item 2) still pins everything at
  100. Fixing the signs alone is not sufficient.
- **Candidate B** (drop PCA; equal-weight the sign-aligned z-scores, the
  classic simple-FCI construction) is the only one of the three that produces
  correct ordering: crisis 6, reviewer repro 5, calm 100. It also produces a
  percentile table (`[+0.118, +1.377]`) that the scenarios actually land
  inside. Its cost is that it discards the PCA weighting entirely, which is the
  branch's headline feature — that is a product decision, not mine to make.

Candidate B is not a recommendation to ship as-is; calm still pins at 100,
so the scale-offset issue (§2 item 2) survives it too.

---

## 4. Current repo state

**Nothing committed.** `git log` head is unchanged at `21ddb37 Mk Ultra: gate
audit-log node-coverage claim on having actually run the analysis`.

```
 M backfill_baseline.py
 M bullion_mkultra.html
 M tests/test_backfill_baseline.py
 M tests/test_macro_engine_js_parity.py
?? __pycache__/            (untracked, gitignored noise)
?? tests/__pycache__/
```

Applied in the working tree (all of Fixes 1–7 were written before the failure
was confirmed):

| fix | state |
|---|---|
| **1** sign-align before PCA | Applied verbatim. **No-op — does not fix C1.** |
| **2** `window_years` = real span | Applied, **works**: hy_oas/ig_oas 15→3.0, sofr→8.4, cpi_yoy→14.8, nfp_mom→14.9 |
| **3** `computeCompositeScore` missing-data gate | Applied, works (test passes) |
| **3a** narrative null-score branch | Applied |
| **3b** `runMacroAnalysis` null-score UI branch | Applied |
| **4** shock routing via `currentLiveSource()` | Applied |
| **5** real `noDataNodes` in shock branch | Applied |
| **6** two "AI" copy strings | Applied |
| **7** crisis-vs-calm ground-truth test | Applied — **and it correctly FAILS**, catching C1 |

`bullion_mkultra.html` also carries the regenerated `BASELINE_STATS`
(`generated_at: 2026-08-10`). Its `pc1_loadings` are numerically equivalent to
the previous ones; the real change in it is Fix 2's `window_years`.

### Test results

```
python3 -m unittest tests.test_backfill_baseline     -> Ran 12 tests, OK
python3 -m unittest tests.test_macro_engine_js_parity -> Ran 11 tests, FAILED (failures=1)
   FAIL: test_synthetic_crisis_scores_worse_than_synthetic_calm
   AssertionError: 100 not less than 100
```

Baseline before this wave was 74 tests / OK. The suite is now 76 (the two new
tests), with 1 failure — **the new Fix 7 guard, doing exactly its job**. Every
other test passes, including the three other new/updated ones
(`test_severely_missing_fields_returns_unavailable_not_a_fabricated_score`,
`test_missing_fields_degrade_tier_to_directional` at 5 fields, and both
rewritten `orient_loadings` tests).

I did not run the full `discover` suite to completion as a final step since
the wave is blocked; the two targeted suites above cover every file touched.

---

## 5. Why I stopped

Per the brief: *"If ANYTHING here doesn't work as specified — a test that
doesn't pass after the fix, a repro case that still shows the wrong direction
— STOP and report BLOCKED rather than pushing through or improvising a
different fix."* Both trigger conditions are met. I did not commit, because
committing Fix 1 would put load-bearing comments into the codebase asserting a
correction that provably did not occur.

## 6. What the coordinator needs to decide

The premise of Fix 1 — "sign-align inputs before fitting, and PCA will find
the stress direction" — cannot work for any dataset: it is an identity
transformation on the exported loadings. The real problem is that **PC1 of
this window is a rate-level factor, not a stress factor**, and Fix 1 does not
address that. A correction has to change either what is fitted, what is
selected, or how weights are formed — not the input polarity. Candidate B is
the only evaluated option that produces correct ordering; the composite/table
scale offset (§2 item 2) likely needs fixing alongside whatever is chosen.
