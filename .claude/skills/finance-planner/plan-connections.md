# plan-connections

Map the transmission mechanisms between nodes — determining link direction, strength, and the plain-language "why."

## When to invoke
When adding new nodes and you need to determine how they connect to existing nodes, or when reviewing whether the current link set is complete.

## Link Design Rules

### Direction (sign)
The `sign` answers: "When the SOURCE rises, what happens to the TARGET?"
- `+1` = source rising pushes target up (e.g., Fed raises rates → yield curve rises)
- `-1` = source rising pushes target down (e.g., rates rise → equity prices fall)
- `0` = ambiguous / regime-dependent (e.g., gold vs. real rates can flip in crises)

### Strength (w)
- `3` = primary/direct mechanism (e.g., FOMC → FFR is the definition of the rate)
- `2` = significant but mediated (e.g., FFR → Yield Curve, with market forces in between)
- `1` = secondary/contextual (e.g., USD → Equity Markets via foreign revenue headwind)

### The "why" field
Must explain the MECHANISM, not just the correlation. Bad: "They are related." Good: "A 10% dollar appreciation shrinks S&P 500 foreign revenue by ~4% when converted back to USD."

## Connection Mapping Process

For each new node pair (source → target):

1. **Identify the channel**: Is this a regulation channel? A funding channel? A price signal? A settlement channel?
2. **Confirm direction**: Does source rising make target rise or fall? Think about the mechanism.
3. **Estimate strength**: Is this the primary driver (3) or a secondary effect (1)?
4. **Write the why**: One mechanism sentence with a concrete number if possible.

## Key Connection Patterns

### Regulatory connections (silver → other)
Regulators typically `+1` sign to their regulated entities (tighter regulation = fewer failures = stronger system), though this is contextual. Use sign=0 for regulators where the direction is ambiguous.

### Funding connections (banks → markets)
Commercial banks provide funding to markets. When banks are healthy (rising), market liquidity rises (positive).

### Infrastructure connections (iron → other)
Infrastructure nodes almost always sign=+1 (working infrastructure supports the nodes that use it). Failure = system freeze.

### Shadow banking connections (violet → markets)
Shadow banking amplifies market moves — when hedge funds or MMFs are stressed, they sell assets, worsening market conditions (sign=-1 in stress).

## Output Format

```js
// === CONNECTIONS: [Node Name] ===
{s:'source_id', t:'target_id', w:2, sign:+1, why:'Mechanism description here.'},
{s:'source_id', t:'target_id2', w:1, sign:-1, why:'Second mechanism here.'},
```

Always group by source node for readability.
