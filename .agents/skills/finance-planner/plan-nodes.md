# plan-nodes

Apply the 4-question framework to plan one or more new financial system nodes.

## When to invoke
When you need to add a new institution, market, or mechanism to the financial map and need to produce a structured spec before writing any code.

## Input
The user or agent provides: a list of institution/concept names + which layer they belong to.

## Process

For each item, work through the 4 questions in order. Do not skip any.

### Q1 — What layer does it belong to?
Choose from: `purple` (monetary policy), `blue` (fiscal/sovereign), `teal` (markets), `coral` (equity sectors), `amber` (sentiment), `green` (economic indicators), `slate` (fx/currency), `ochre` (commodities), `rose` (geopolitics), `silver` (regulators), `cobalt` (commercial banking), `violet` (shadow banking), `iron` (infrastructure), `dkblue` (gov institutional), `indigo` (cb institutional).

### Q2 — What controls it / what does it control?
List:
- Upstream: entities that govern, fund, or influence this node
- Downstream: entities this node governs, funds, or influences

### Q3 — What breaks if it disappears?
Be specific. Name the failure cascade:
- Immediate effect (hours/days)
- Short-term effect (weeks)
- Systemic risk (if applicable — mark `"systemic": true`)

### Q4 — Where do money/data flows go?
Trace both directions. Note whether the flow is:
- Physical money settlement
- Credit/lending
- Regulatory data reporting
- Market price signals

## Output

Produce a ready-to-paste JSON block for the NODES array and a second block for LINKS array. Format exactly as the finance-builder expects.

Example output:
```js
// === NEW NODE: DTCC ===
{ id:'dtcc', label:'DTCC', group:'iron',
  beginner:'The central clearinghouse that guarantees every stock and bond trade in America is completed — even if one party defaults.',
  expert:'Depository Trust & Clearing Corporation. Clears >$2.5 quadrillion in securities annually. Operates DTC (custody), NSCC (equity clearing), and FICC (fixed income clearing). Systemically important FMU under Dodd-Frank. ~40M transactions/day.',
  breaks:'Without DTCC: all equity and bond settlement freezes. The 2008 Lehman default would have caused mass fails; DTCC\'s guarantee function prevented it. Failure = immediate market closure. Systemic.' },

// === NEW LINKS FROM DTCC ===
{s:'dtcc', t:'equit',  w:3, sign:+1, why:'DTCC\'s NSCC guarantees all US equity trades settle, which is why investors trust the market — without it, counterparty risk would freeze trading.'},
{s:'dtcc', t:'credit', w:2, sign:+1, why:'DTCC\'s FICC arm clears Treasury and agency securities, providing the backbone for bond market liquidity.'},
```
