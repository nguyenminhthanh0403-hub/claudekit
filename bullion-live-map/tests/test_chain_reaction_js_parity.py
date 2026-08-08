"""JS<->Python exhaustive parity guard for the chain-reaction traversal.

test_chain_reaction.py re-implements findChains()/netSignForPath() in Python
against the same source data, but never actually runs the real JS -- so a bug
introduced only in the JS (exactly the direction-shadowing bug fixed in
commit e98ffe6) could ship with that Python-only guard fully green. This file
closes that gap: it shells out to a real `node` process, extracts the live
NODES..PLUMBING_LINKS..findChains..netSignForPath block directly out of
bullion_mkultra.html, runs the ACTUAL shipped JS across every ordered node
pair, and diffs the result against this repo's Python mirror
(test_chain_reaction.find_chains/net_sign) exhaustively -- not just a few
fixture pairs.

Skipped (not failed) if `node` isn't on PATH, since JS execution is not
otherwise a hard dependency of this test suite.
"""
import json
import shutil
import subprocess
import unittest

from test_chain_reaction import (
    MAP_PATH,
    build_graph,
    find_chains,
    load_merged_edges,
    net_sign,
)


def _extract_js_snippet(html):
    start = html.index("const NODES = [")
    end = html.index("let expandedHubs = new Set();")
    return html[start:end]


def _run_js_all_pairs(html, node_ids):
    snippet = _extract_js_snippet(html)
    script = (
        snippet
        + """
const nodeIds = %s;
const result = {};
for (const a of nodeIds) {
  for (const b of nodeIds) {
    if (a === b) continue;
    const paths = findChains(a, b, 3);
    if (paths.length === 0) continue;
    result[a + '|' + b] = paths.map(p => {
      const seq = [p[0].from, ...p.map(h => h.to)];
      const forwards = p.map(h => h.forward);
      const signs = p.map(h => h.link.sign);
      const net = netSignForPath(p);
      return { seq, forwards, signs, net };
    });
  }
}
process.stdout.write(JSON.stringify(result));
"""
        % json.dumps(node_ids)
    )
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError("node script failed: " + proc.stderr[:2000])
    return json.loads(proc.stdout)


def _net_key(net):
    if net is None:
        return None
    return (net["sign"], net["reversed"])


def _path_key(entry):
    return (
        tuple(entry["seq"]),
        tuple(entry["forwards"]),
        tuple(entry["signs"]),
        _net_key(entry["net"]),
    )


@unittest.skipUnless(shutil.which("node"), "node not available on PATH")
class TestChainReactionJsParity(unittest.TestCase):
    def test_js_and_python_agree_on_every_ordered_pair(self):
        with open(MAP_PATH, encoding="utf-8") as f:
            html = f.read()
        edges = load_merged_edges()
        neighbors, edge_of = build_graph(edges)
        node_ids = sorted(set([e[0] for e in edges] + [e[1] for e in edges]))

        js_data = _run_js_all_pairs(html, node_ids)

        mismatches = []
        checked_pairs = 0
        for a in node_ids:
            for b in node_ids:
                if a == b:
                    continue
                py_paths = find_chains(neighbors, edge_of, a, b, 3)
                key = a + "|" + b
                if not py_paths:
                    self.assertNotIn(
                        key,
                        js_data,
                        f"Python found no path {a}->{b} but JS found "
                        f"{len(js_data.get(key, []))}",
                    )
                    continue
                checked_pairs += 1
                py_entries = []
                for p in py_paths:
                    seq = [p[0][0]] + [hop[1] for hop in p]
                    forwards = [hop[2]["forward"] for hop in p]
                    signs = [hop[2]["sign"] for hop in p]
                    py_entries.append(
                        {"seq": seq, "forwards": forwards, "signs": signs, "net": net_sign(p)}
                    )
                py_set = set(_path_key(e) for e in py_entries)
                js_set = set(_path_key(e) for e in js_data.get(key, []))
                if py_set != js_set:
                    mismatches.append((a, b, js_set - py_set, py_set - js_set))

        self.assertEqual(
            mismatches,
            [],
            f"JS/Python traversal disagree on {len(mismatches)} pair(s): {mismatches[:3]}",
        )
        self.assertGreater(checked_pairs, 0, "sanity check: expected at least one connected pair")


if __name__ == "__main__":
    unittest.main()
