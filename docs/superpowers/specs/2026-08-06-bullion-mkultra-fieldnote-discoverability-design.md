# Bullion Mk Ultra — field-note discoverability — design

**Date:** 2026-08-06
**Status:** approved, not yet implemented
**Origin:** `/impeccable critique` dual-agent audit of `bullion-live-map/bullion_mkultra.html`,
snapshot at `.impeccable/critique/2026-08-06T12-49-55Z__bullion-live-map-bullion-mkultra-html.md`
(Design Health Score 27/40). This is the second of that critique's two deferred P2 findings —
the first (WebGL-fallback/orb overlap) and the three P1s were fixed in an earlier pass
(`docs/superpowers/specs/2026-08-06-bullion-mkultra-identity-polish-design.md`).

## Problem

Only 2 of 250+ links (`credit→equit`, `usd→oil`) carry a `fieldNote` — first-person marginalia
tied to the fitted statistics, the most human content in the file. Nothing in the 3D graph, the
2D Overview board, or the relationship detail panel signals which links have one. The critique's
live testing needed an undirected scroll-and-hope path (Overview → Credit Markets card → scroll
to the Equity Markets sub-card) to find the one it eventually found.

**Explicitly out of scope for this pass** (confirmed with the user): whether the bar for writing
a field note should be lower, and writing any additional field notes. This pass only makes the
existing 2 discoverable — it does not change how many exist.

## Design

### Data layer

One new top-level constant, computed immediately after the existing `PLUMBING_LINKS` →
`LINKS` supersede-or-append merge block (`bullion_mkultra.html` ~line 1533), so it reads the
already-merged canonical `LINKS` array — not `LINKS`/`PLUMBING_LINKS` separately (this project's
standing two-link-array trap):

```js
const FIELDNOTE_NODE_IDS = new Set();
LINKS.forEach(l => { if (l.fieldNote) { FIELDNOTE_NODE_IDS.add(l.s); FIELDNOTE_NODE_IDS.add(l.t); } });
```

Today this evaluates to `{credit, equit, usd, oil}`. It stays correct automatically if the
(separately-scoped) content bar is ever lowered and more field notes are added later.

### The marker

One shared glyph and CSS class, reused at all three placement points below — a single visual
language rather than three different affordances:

- **Glyph:** ✎ (U+270E, pencil) — thematically consistent with field notes being the creator's
  own marginalia, distinct from existing iconography (🔊 narration button, ⚠ audit-unverified
  badge).
- **CSS class:** `.fieldnote-badge` — color `var(--gold-dim)`, sized to context (~10-11px),
  `title="Field note — the creator's own note on this link"` for the hover tooltip. This
  `title`-for-hint pattern matches existing usage in this file (`.audit-badge`, `.tier-badge`,
  `.rel-arrows` all already use `title` this way).
- **Not interactive.** The badge is a passive signal, not a new click target — avoids nesting an
  interactive element inside the board card's `<button>`, and avoids adding new behavior beyond
  what's needed to fix discoverability.

### Placement (three surfaces, one badge)

1. **Overview board card** (`buildBoard`, ~line 2921) — if `FIELDNOTE_NODE_IDS.has(n.id)`,
   append the badge after the card's label. **Implementation note:** `card.textContent = n.label`
   currently wipes any children, so this line changes to setting the label via a text node (or
   `textContent` on a child span) plus a conditionally-appended badge span, not a plain
   `textContent` assignment. This is the most reliable of the three surfaces — the board always
   renders every node card at once, regardless of hub/focus state.

2. **3D node label** (`labelEls` creation, ~line 1965) — same condition, badge appended into the
   label element's HTML. Visible exactly when that node's label is already showing today (hub
   node, or a focused node's neighbor) — no change to the existing label-visibility rules
   (`labelEligible`). Opportunistic: won't help a visitor who never focuses `usd` or `oil` if
   neither happens to be a hub, but it's free once the shared badge markup exists and doesn't
   regress anything.

3. **Relationship row** (`rowHtml`, ~line 2778) — if `r.l.fieldNote`, badge goes in
   `.rel-row-top` next to the link name. This is the only placement tied to the *specific link*
   rather than "this node has one somewhere" — once a visitor has opened a hub with many links,
   this lets them scan the compact row headers instead of reading every expanded `.rel-detail`
   paragraph looking for the italic marginalia block.

### Onboarding

One sentence appended to the existing COACH step 2 body (`'That card is the point'`, ~line
3013) — no new step, no new mechanism:

> "A <span style='color:var(--gold-dim)'>✎</span> next to a name means the creator left a
> first-person note on why that link changed."

Scoped to this step because it's already the step that introduces what a card shows; adding a
fourth step for one sentence would be disproportionate.

## Testing / verification approach

- **Headless-Chrome probe:** load the file, confirm the badge DOM node exists on exactly the
  `credit`, `equit`, `usd`, `oil` board cards and on exactly the `credit→equit` and `usd→oil`
  relationship rows; confirm it's absent on every other card/row (no false positives from a
  loose selector or an inverted condition).
- **Chrome-MCP visual check:** confirm the glyph renders legibly at board-card size (not just
  present in the DOM — legible), and that it doesn't crowd the card label at narrow widths.
- **3D label:** headless or Chrome-MCP check that the badge appears in the label overlay for at
  least one of the four affected nodes when it's a visible hub or focused-neighbor label.
- **Freeze-check:** `git diff --stat -- bullion-live-map/bullion_mk1[1-8].html` must stay empty
  — this pass only touches `bullion_mkultra.html`.
- No Python/unit-test suites are affected — this is CSS/JS-only inside one file.

## Out of scope (separate future decision, not rejected)

Whether the bar for "this link deserves a field note" should be lower, and writing any
additional field notes. The critique raised this as its own open question; the user chose to
keep this pass scoped to discoverability of the 2 that already exist.
