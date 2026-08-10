# Bullion Mk Ultra — Link Sourcing Audit (Phase 1: Research) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one aggregated markdown report auditing citation validity, mechanism accuracy, and currency for every link in the live `bullion_mkultra.html` causal graph — no code or content changes to the file itself.

**Architecture:** The 93-edge runtime graph is split into 9 research batches (~10-12 edges each, grouped by the file's own section comments). Each batch is a self-contained research task producing one staging markdown file. A final aggregation task merges all 9 staging files into one report, organized by the original 16 sections, then deletes the staging files.

**Tech Stack:** Markdown output only. Research via `WebSearch`/`WebFetch`. No build, no tests in the traditional sense — each task's "test" is a structural completeness check (right number of rows, no duplicates, no gaps).

## Global Constraints

- **Read-only w.r.t. the app:** No task in this plan edits `bullion-live-map/bullion_mkultra.html`. Every task's output is a new markdown file under `docs/superpowers/reports/`.
- **Untracked output, per project convention:** Every file under `docs/superpowers/` (including this plan and the report it produces) stays **untracked** — do not `git add` or `git commit` any file created by this plan. This matches every existing file in `docs/superpowers/` (specs, plans, handoffs), confirmed via `git status` showing them all as untracked noise, not tracked content.
- **Source hierarchy:** government/central-bank primary sources (FRED, US Treasury/TIC, FDIC, Federal Reserve H.8/FSR, NY Fed, BIS, SEC, IMF, OFR, ICI, EIA, WGC, BLS, CBOE, and similar) are what a claim must check out against. Wikipedia and standard textbooks may be used only to orient quickly on an unfamiliar mechanism or to locate the primary source faster — **never** cited as the final authority in a verdict.
- **Verdict schema — every row in every output file uses exactly these 8 columns, in this order:** `Section | Edge (s→t) | Conf tier | Citation validity | Mechanism accuracy | Currency | Suggested action | Evidence note`.
  - Citation validity ∈ {OK, Stale, Unverifiable, N/A}
  - Mechanism accuracy ∈ {OK, Questionable, Incorrect}
  - Currency ∈ {OK, Stale-but-historically-fine, Stale-misleading}
  - Suggested action ∈ {none, update stat text, field-note candidate, reconsider confidence tier, flag for discussion}
  - Evidence note: 1-2 sentences, specific enough that a later phase can act without re-researching.
- **IMPORTANT correction from the spec:** the design spec (`docs/superpowers/specs/2026-08-07-bullion-mkultra-link-sourcing-audit-design.md`) describes "102 links across 16 sections." That figure counts raw source-code object literals across both the `LINKS` array (86 entries, starts `bullion_mkultra.html:1390`) and the `PLUMBING_LINKS` array (16 entries, starts `bullion_mkultra.html:1325`). But the file's own merge step (`bullion_mkultra.html:1509-1524`, comment block "MERGE PLUMBING INTO THE GRAPH") makes `PLUMBING_LINKS` **supersede** any `LINKS` entry with the same `(s,t)` pair rather than append a second edge — 9 of the 16 `PLUMBING_LINKS` entries do this. The actual runtime graph — what `FIELDNOTE_NODE_IDS`, the renderer, and every visitor-facing surface reads — has **93 edges, not 102**. This plan's task tables below already reflect the correct, merged, 93-edge graph. **Do not independently re-derive the edge list by grep/scanning for `{s:` patterns** — the 9 original `LINKS` entries listed in the "Superseded — do not audit" table at the end of this plan are dead code, overwritten at runtime, and must not appear as separate rows in any output.
- **Reading a source object:** each edge below lists its array and starting line. Use `Read` with that `offset` and `limit: 6` on `bullion-live-map/bullion_mkultra.html` — object literals span 1-5 lines depending on how many of `why`/`stat`/`note`/`fieldNote` they carry. Confirm the `s`/`t` you read match the table before using the text.

---

### Task 1: Audit Batch 1 — Monetary policy spine, Sovereign/fiscal, Deposit flight (plumbing)

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-1.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:**
- Consumes: verdict schema and source hierarchy from Global Constraints above.
- Produces: `docs/superpowers/reports/.staging/batch-1.md`, one of 9 staging files Task 10 aggregates.

**Edges in this batch (10):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| Monetary policy spine | fed→fomc | LINKS | 1392 | directional |
| Monetary policy spine | fomc→ffr | LINKS | 1393 | directional |
| Monetary policy spine | ffr→yield | LINKS | 1394 | directional |
| Monetary policy spine | ffr→credit | LINKS | 1395 | directional |
| Monetary policy spine | fed→cpi | LINKS | 1396 | directional |
| Sovereign / fiscal | tsy→yield | LINKS | 1399 | directional |
| Sovereign / fiscal | tsy→dealers | LINKS | 1400 | directional |
| Deposit flight (plumbing) | ffr→mmf | PLUMBING_LINKS | 1327 | directional |
| Deposit flight (plumbing) | mmf→banks | PLUMBING_LINKS | 1330 | directional |
| Deposit flight (plumbing) | ffr→banks | PLUMBING_LINKS | 1333 | directional |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text.

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: FRED", "Source: NY Fed"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard monetary-policy/fiscal mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-1.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-1.md`. Confirm it is exactly 10, confirm each of the 10 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 2: Audit Batch 2 — Commercial banking, Funding markets (plumbing), Backstops (plumbing), Dealer capacity (plumbing)

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-2.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:** same as Task 1.

**Edges in this batch (11):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| Commercial banking | fed→dealers | LINKS | 1403 | directional |
| Commercial banking | fed→banks | LINKS | 1404 | directional |
| Commercial banking | banks→credit | LINKS | 1407 | directional |
| Commercial banking | banks→fins | LINKS | 1408 | directional |
| Funding markets (plumbing) | mmf→repo | PLUMBING_LINKS | 1338 | directional |
| Funding markets (plumbing) | repo→dealers | PLUMBING_LINKS | 1341 | directional |
| Funding markets (plumbing) | repo→hf | PLUMBING_LINKS | 1344 | directional |
| Funding markets (plumbing) | vix→repo | PLUMBING_LINKS | 1347 | directional |
| Backstops (plumbing) | fdic→banks | PLUMBING_LINKS | 1353 | directional |
| Backstops (plumbing) | fed→repo | PLUMBING_LINKS | 1356 | measured |
| Dealer capacity (plumbing) | dealers→yield | PLUMBING_LINKS | 1385 | directional |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text.

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: FDIC", "Source: BIS, OFR, Fed FSR"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only, never as the final cited authority.

Note: `vix→repo`'s `stat` text says the fitted sign disagrees with the shown sign "but only at |t|=0.3 — too weak to act on (logged as a conflict)." Treat this self-reported conflict as part of the evidence to verify, not a red flag to independently resolve — the file already logs it honestly; your job is to confirm the surrounding citations (BIS, OFR, Fed FSR) actually support the sign shown.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard banking/funding-market mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-2.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-2.md`. Confirm it is exactly 11, confirm each of the 11 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 3: Audit Batch 3 — Shadow/non-bank, Mortgage/agency channel (plumbing), Who stands behind the backstops (plumbing), Regulators

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-3.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:** same as Task 1.

**Edges in this batch (12):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| Shadow / non-bank | repo→banks | LINKS | 1412 | directional |
| Shadow / non-bank | mmf→tsy | LINKS | 1415 | directional |
| Shadow / non-bank | hf→yield | LINKS | 1417 | directional |
| Mortgage/agency channel (plumbing) | gse→mbs | PLUMBING_LINKS | 1361 | directional |
| Mortgage/agency channel (plumbing) | yield→mbs | PLUMBING_LINKS | 1364 | directional |
| Mortgage/agency channel (plumbing) | mbs→banks | PLUMBING_LINKS | 1367 | directional |
| Mortgage/agency channel (plumbing) | fed→mbs | PLUMBING_LINKS | 1370 | directional |
| Who stands behind the backstops (plumbing) | tsy→gse | PLUMBING_LINKS | 1377 | directional |
| Who stands behind the backstops (plumbing) | banks→fdic | PLUMBING_LINKS | 1380 | directional |
| Regulators | sec→equit | LINKS | 1422 | directional |
| Regulators | sec→credit | LINKS | 1423 | directional |
| Regulators | cftc→oil | LINKS | 1424 | directional |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text.

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: NY Fed primary dealer statistics, OFR", "Source: FRED MORTGAGE30US vs DGS10"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only, never as the final cited authority.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard shadow-banking/mortgage-market mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-3.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-3.md`. Confirm it is exactly 12, confirm each of the 12 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 4: Audit Batch 4 — Capital markets, Equity sectors, Sentiment, Economic data → policy

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-4.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:** same as Task 1.

**Edges in this batch (12):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| Capital markets | yield→credit | LINKS | 1427 | measured |
| Capital markets | yield→equit | LINKS | 1428 | measured |
| Capital markets | yield→fins | LINKS | 1429 | directional |
| Capital markets | credit→equit | LINKS | 1431 | measured (has fieldNote) |
| Equity sectors | equit→tech | LINKS | 1434 | measured |
| Equity sectors | equit→fins | LINKS | 1435 | measured |
| Equity sectors | equit→defn | LINKS | 1436 | directional |
| Equity sectors | ffr→tech | LINKS | 1437 | directional |
| Sentiment | vix→equit | LINKS | 1440 | measured |
| Sentiment | vix→defn | LINKS | 1441 | measured |
| Economic data → policy | cpi→fomc | LINKS | 1444 | directional |
| Economic data → policy | nfp→fomc | LINKS | 1445 | directional |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text. Note: `credit→equit` already has a `fieldNote` (from the 2026-08-06 discoverability pass). Audit its `stat`/citation as normal; do not alter or re-evaluate the `fieldNote` text itself — that's out of scope for this audit (see spec's "Out of scope").

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: FRED", "HY spreads and the S&P move inversely... (FRED)"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only, never as the final cited authority.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard capital-markets/equity mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-4.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-4.md`. Confirm it is exactly 12, confirm each of the 12 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 5: Audit Batch 5 — FX/dollar, Commodities

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-5.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:** same as Task 1.

**Edges in this batch (10):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| FX / dollar | ffr→usd | LINKS | 1448 | directional |
| FX / dollar | usd→dxy_fx | LINKS | 1449 | directional |
| FX / dollar | usd→gold | LINKS | 1450 | measured |
| FX / dollar | usd→oil | LINKS | 1451 | measured (has fieldNote) |
| FX / dollar | usd→equit | LINKS | 1452 | measured |
| FX / dollar | dxy_fx→credit | LINKS | 1453 | directional |
| Commodities | oil→cpi | LINKS | 1456 | directional |
| Commodities | vix→gold | LINKS | 1457 | directional |
| Commodities | oil→equit | LINKS | 1458 | measured |
| Commodities | gold→tsy | LINKS | 1459 | directional |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text. Note: `usd→oil` already has a `fieldNote`. `oil→equit` is the link identified as a strong future field-note candidate in the separate credibility-bar spec (not this plan's concern) — audit its citation/mechanism/currency as normal, same as any other edge.

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: WGC", "Source: EIA"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only, never as the final cited authority.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard FX/commodities-pricing mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-5.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-5.md`. Confirm it is exactly 10, confirm each of the 10 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 6: Audit Batch 6 — Geopolitics

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-6.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:** same as Task 1.

**Edges in this batch (10):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| Geopolitics | russia→oil | LINKS | 1462 | directional |
| Geopolitics | russia→gold | LINKS | 1463 | directional |
| Geopolitics | china→equit | LINKS | 1464 | directional |
| Geopolitics | china→tsy | LINKS | 1465 | unverified |
| Geopolitics | china→oil | LINKS | 1466 | directional |
| Geopolitics | geo→oil | LINKS | 1467 | directional |
| Geopolitics | geo→cpi | LINKS | 1468 | directional |
| Geopolitics | geo→credit | LINKS | 1469 | unverified |
| Geopolitics | russia→geo | LINKS | 1470 | directional |
| Geopolitics | china→geo | LINKS | 1471 | directional |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text. Note: `china→tsy` and `geo→credit` are two of the file's 4 `unverified` links and already state their own gap (e.g. "No named dataset behind the uncertainty-premium claim"). Your job is to check whether a real primary source now exists that could close that gap, not just confirm the gap is real.

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: US Treasury TIC data"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. For the 2 `unverified` edges above, search specifically for whether a named dataset now exists that didn't before. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only, never as the final cited authority.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard geopolitical-risk/sovereign-debt mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-6.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-6.md`. Confirm it is exactly 10, confirm each of the 10 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 7: Audit Batch 7 — Money & deposits (Mk13), Mortgage rates (Mk13)

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-7.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:** same as Task 1.

**Edges in this batch (12):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| Money & deposits (Mk13) | credit→deposits | LINKS | 1474 | directional |
| Money & deposits (Mk13) | deposits→banks | LINKS | 1475 | directional |
| Money & deposits (Mk13) | deposits→m2 | LINKS | 1476 | directional |
| Money & deposits (Mk13) | fdic→deposits | LINKS | 1477 | directional |
| Money & deposits (Mk13) | ffr→deposits | LINKS | 1478 | directional |
| Money & deposits (Mk13) | ffr→m2 | LINKS | 1479 | directional |
| Money & deposits (Mk13) | m2→cpi | LINKS | 1480 | directional |
| Money & deposits (Mk13) | m2→gold | LINKS | 1481 | directional |
| Mortgage rates (Mk13) | yield→mortgage | LINKS | 1484 | measured |
| Mortgage rates (Mk13) | mbs→mortgage | LINKS | 1485 | directional |
| Mortgage rates (Mk13) | ffr→mortgage | LINKS | 1486 | directional |
| Mortgage rates (Mk13) | mortgage→credit | LINKS | 1487 | measured |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text. Note: `mortgage→credit` is one of the two hand-sign-flip links excluded from a field note in the separate credibility-bar spec on statistical grounds (|t|=2.0, n=40) — audit its citation/mechanism/currency normally; that prior exclusion was about field-note voice, not about whether its `stat` citation is valid.

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: NY Fed Household Debt report", "Source: FRED MORTGAGE30US vs DGS10"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only, never as the final cited authority.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard household-credit/mortgage-market mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-7.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-7.md`. Confirm it is exactly 12, confirm each of the 12 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 8: Audit Batch 8 — Private credit (Mk13), Breadth links (Mk15) part 1

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-8.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:** same as Task 1.

**Edges in this batch (10):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| Private credit (Mk13) | privcredit→credit | LINKS | 1490 | directional |
| Private credit (Mk13) | ffr→privcredit | LINKS | 1491 | directional |
| Private credit (Mk13) | banks→privcredit | LINKS | 1492 | directional |
| Private credit (Mk13) | hf→privcredit | LINKS | 1493 | unverified |
| Breadth links (Mk15) | tsy→tbills | LINKS | 1496 | measured |
| Breadth links (Mk15) | tbills→mmf | LINKS | 1497 | directional |
| Breadth links (Mk15) | ffr→tbills | LINKS | 1498 | directional |
| Breadth links (Mk15) | vix→options | LINKS | 1499 | directional |
| Breadth links (Mk15) | options→equit | LINKS | 1500 | directional |
| Breadth links (Mk15) | equit→etf | LINKS | 1501 | directional |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text. Note: `hf→privcredit` is the 4th `unverified` link — its `stat` says *"'Industry estimates' names no dataset."* Check whether a real named primary source exists now.

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: US Treasury, SIFMA"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. For `hf→privcredit`, search specifically for whether a named dataset now exists that didn't before. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only, never as the final cited authority.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard private-credit/Treasury-market mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-8.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-8.md`. Confirm it is exactly 10, confirm each of the 10 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 9: Audit Batch 9 — Breadth links (Mk15) part 2

**Files:**
- Create: `docs/superpowers/reports/.staging/batch-9.md`
- Read-only: `bullion-live-map/bullion_mkultra.html` (edges below)

**Interfaces:** same as Task 1.

**Edges in this batch (6):**

| Section | Edge | Array | Line | Conf |
|---|---|---|---|---|
| Breadth links (Mk15) | etf→equit | LINKS | 1502 | directional |
| Breadth links (Mk15) | oil→energy | LINKS | 1503 | measured |
| Breadth links (Mk15) | energy→equit | LINKS | 1504 | directional |
| Breadth links (Mk15) | mortgage→house | LINKS | 1505 | directional |
| Breadth links (Mk15) | credit→house | LINKS | 1506 | directional |
| Breadth links (Mk15) | house→equit | LINKS | 1507 | directional |

- [ ] **Step 1: Read each edge's source text**

Read `bullion-live-map/bullion_mkultra.html` at each `Line` above with `limit: 6`. Confirm the `s`/`t` in the object match the table row before using its `why`/`stat`/`note`/`fieldNote` text.

- [ ] **Step 2: Research citation validity**

For each edge with a named source in `stat` (e.g. "Source: S&P DJI, EIA"), verify via `WebSearch`/`WebFetch` that the named source actually supports the specific claim/number stated. Mark `N/A` if the edge cites no source to check. Use the source hierarchy from Global Constraints — Wikipedia/textbooks for orientation only, never as the final cited authority.

- [ ] **Step 3: Assess mechanism accuracy and currency**

For each edge, judge whether the `why` text's causal claim is correct per standard energy-sector/housing-market mechanics, independent of whether a dataset backs it (Mechanism accuracy). Judge whether any cited stat is presented as current when it's actually dated in a misleading way, versus a fixed historical fact that doesn't go stale (Currency).

- [ ] **Step 4: Write the batch findings table**

Write `docs/superpowers/reports/.staging/batch-9.md` with the 8-column table from Global Constraints, one row per edge, in the same order as the table above.

- [ ] **Step 5: Verify completeness**

Count the rows in `docs/superpowers/reports/.staging/batch-9.md`. Confirm it is exactly 6, confirm each of the 6 `Edge` values above appears exactly once, and confirm no extra rows exist.

---

### Task 10: Aggregate all batches into the final report

**Files:**
- Create: `docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md`
- Read: `docs/superpowers/reports/.staging/batch-1.md` through `batch-9.md`
- Delete: `docs/superpowers/reports/.staging/` (all 9 files, after the final report is written and verified)

**Interfaces:**
- Consumes: the 9 staging files from Tasks 1-9, each with the 8-column verdict schema.
- Produces: the final aggregated report — the deliverable of this entire plan.

- [ ] **Step 1: Read all 9 staging files**

Read `docs/superpowers/reports/.staging/batch-1.md` through `batch-9.md`.

- [ ] **Step 2: Regroup rows by the 16 original sections, not by batch**

Batches don't align 1:1 with sections (e.g. "Breadth links (Mk15)" is split across batches 8 and 9; several plumbing sections share a batch with unrelated `LINKS` sections). Reorganize all 93 rows into 16 section tables, in this exact order, with these exact expected row counts:

1. Monetary policy spine — 5
2. Sovereign / fiscal — 2
3. Commercial banking — 4
4. Deposit flight (plumbing) — 3
5. Funding markets (plumbing) — 4
6. Backstops (plumbing) — 2
7. Dealer capacity (plumbing) — 1
8. Shadow / non-bank — 3
9. Mortgage/agency channel (plumbing) — 4
10. Who stands behind the backstops (plumbing) — 2
11. Regulators — 3
12. Capital markets — 4
13. Equity sectors — 4
14. Sentiment — 2
15. Economic data → policy — 2
16. FX / dollar — 6
17. Commodities — 4
18. Geopolitics — 10
19. Money & deposits (Mk13) — 8
20. Mortgage rates (Mk13) — 4
21. Private credit (Mk13) — 4
22. Breadth links (Mk15) — 12

(22 groups, not 16, because the 6 plumbing-only sections are broken out separately from their `LINKS`-array counterparts for clarity — this matches how the source file itself comments them as distinct blocks.)

- [ ] **Step 3: Add the merge-note appendix**

Prepend a short section titled "Note on the LINKS/PLUMBING_LINKS merge" explaining that `PLUMBING_LINKS` supersedes 9 `LINKS` entries at runtime (cite `bullion_mkultra.html:1509-1524`), and list the 9 dead, no-longer-live entries so a future reader doesn't mistake their absence from the audit for an oversight:

| Superseded pair | Dead LINKS line | Live version now at |
|---|---|---|
| ffr→banks | 1405 | PLUMBING_LINKS:1333 |
| dealers→yield | 1406 | PLUMBING_LINKS:1385 |
| fed→repo | 1411 | PLUMBING_LINKS:1356 |
| repo→hf | 1413 | PLUMBING_LINKS:1344 |
| mmf→repo | 1414 | PLUMBING_LINKS:1338 |
| ffr→mmf | 1416 | PLUMBING_LINKS:1327 |
| gse→mbs | 1418 | PLUMBING_LINKS:1361 |
| fdic→banks | 1421 | PLUMBING_LINKS:1353 |
| yield→mbs | 1430 | PLUMBING_LINKS:1364 |

- [ ] **Step 4: Write the final report**

Write `docs/superpowers/reports/2026-08-07-bullion-mkultra-link-sourcing-audit.md` with the merge-note appendix first, then the 22 section tables in the order from Step 2, each row using the 8-column verdict schema.

- [ ] **Step 5: Verify completeness**

Count total data rows across all 22 section tables in the final report. Confirm the total is exactly 93. Confirm each section's row count matches the list in Step 2 exactly.

- [ ] **Step 6: Clean up staging files**

Delete `docs/superpowers/reports/.staging/batch-1.md` through `batch-9.md` now that the final report exists and is verified — mirroring this project's convention of deleting an SDD plan's scratch workspace once the final review is clean.

No git commit — per Global Constraints, this entire report tree stays untracked.
