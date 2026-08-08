"""Independent structural check for the chain-reaction traversal feature.

findChains() (bullion_mkultra.html, JS) does undirected BFS over the merged
LINKS array to find paths <=3 hops between two nodes. There is no browser-based
JS test runner in this repo, so this file re-implements the same algorithm in
Python against the same source data (parsed via regex, not a full JS parser --
only the s/t/w/sign fields are needed for topology, not why/stat/conf) and
asserts it against known pairs. This is the only automated regression guard
for the traversal logic: if a future edit renames, removes, or re-signs a
link such that these known chains break, this test catches it the same way
test_freshness_parity.py catches Python<->JS table drift.

Mirrors the project's existing supersede-or-append merge rule (see
bullion_mkultra.html's "MERGE PLUMBING INTO THE GRAPH" comment block): a
PLUMBING_LINKS entry with the same (s, t) pair as an existing LINKS entry
replaces it; otherwise it's appended.
"""
import os
import re
import unittest

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "bullion_mkultra.html")

_EDGE_RE = re.compile(r"\{s:'(\w+)', t:'(\w+)', w:(\d+), sign:(-?\d+)")


def _extract_block(html, array_name):
    start = html.index("const " + array_name + " = [")
    end = html.index("\n];", start)
    return html[start:end]


def _parse_edges(block):
    return [(s, t, int(w), int(sign)) for s, t, w, sign in _EDGE_RE.findall(block)]


def load_merged_edges():
    with open(MAP_PATH, encoding="utf-8") as f:
        html = f.read()
    links = _parse_edges(_extract_block(html, "LINKS"))
    plumbing = _parse_edges(_extract_block(html, "PLUMBING_LINKS"))
    by_pair = {}
    order = []
    for s, t, w, sign in links:
        by_pair[(s, t)] = (s, t, w, sign)
        order.append((s, t))
    for s, t, w, sign in plumbing:
        if (s, t) not in by_pair:
            order.append((s, t))
        by_pair[(s, t)] = (s, t, w, sign)
    return [by_pair[k] for k in order]


def build_graph(edges):
    from collections import defaultdict
    neighbors = defaultdict(set)
    edge_of = {}
    for s, t, w, sign in edges:
        neighbors[s].add(t)
        neighbors[t].add(s)
        edge_of[(s, t)] = (s, t, w, sign)
    return neighbors, edge_of


def find_link(edge_of, a, b):
    if (a, b) in edge_of:
        e = edge_of[(a, b)]
        return {"sign": e[3], "forward": True}
    if (b, a) in edge_of:
        e = edge_of[(b, a)]
        return {"sign": e[3], "forward": False}
    return None


def find_chains(neighbors, edge_of, start, end, max_hops=3):
    paths = []

    def dfs(current, visited, path):
        if len(path) > max_hops:
            return
        if current == end and path:
            paths.append(list(path))
            return
        for nxt in sorted(neighbors[current]):
            if nxt in visited:
                continue
            hop = find_link(edge_of, current, nxt)
            visited.add(nxt)
            path.append((current, nxt, hop))
            dfs(nxt, visited, path)
            path.pop()
            visited.discard(nxt)

    if start != end:
        dfs(start, {start}, [])
    return paths


def net_sign(path):
    if not path:
        return None
    all_forward = all(hop[2]["forward"] for hop in path)
    all_backward = all(not hop[2]["forward"] for hop in path)
    if not all_forward and not all_backward:
        return None
    net = 1
    for hop in path:
        net *= hop[2]["sign"]
    return {"sign": net, "reversed": all_backward}


class TestChainReactionTraversal(unittest.TestCase):
    def setUp(self):
        self.edges = load_merged_edges()
        self.neighbors, self.edge_of = build_graph(self.edges)

    def test_total_live_edge_count(self):
        # Cross-check against the 2026-08-07 link-sourcing audit's own count
        # (93 live edges after the supersede-or-append merge) -- if this
        # drifts, the graph structure changed in a way this test should see.
        self.assertEqual(len(self.edges), 93)

    def test_mortgage_to_repo_finds_seven_paths(self):
        paths = find_chains(self.neighbors, self.edge_of, "mortgage", "repo", 3)
        sequences = {
            tuple([p[0][0]] + [hop[1] for hop in p]) for p in paths
        }
        expected = {
            ("mortgage", "credit", "banks", "repo"),
            ("mortgage", "ffr", "banks", "repo"),
            ("mortgage", "ffr", "mmf", "repo"),
            ("mortgage", "mbs", "banks", "repo"),
            ("mortgage", "mbs", "fed", "repo"),
            ("mortgage", "yield", "dealers", "repo"),
            ("mortgage", "yield", "hf", "repo"),
        }
        self.assertEqual(sequences, expected)
        # 5 of these 7 are genuinely mixed-direction (no honest net sign).
        # The other 2 (yield->dealers->repo, yield->hf->repo) are all-backward
        # -- a real chain, just read start-to-end in reverse -- and now get a
        # reversed net sign rather than being lumped in with the mixed ones.
        by_seq = {tuple([p[0][0]] + [hop[1] for hop in p]): p for p in paths}
        mixed_sequences = expected - {
            ("mortgage", "yield", "dealers", "repo"),
            ("mortgage", "yield", "hf", "repo"),
        }
        for seq in mixed_sequences:
            self.assertIsNone(net_sign(by_seq[seq]), f"{seq} should have no net sign (mixed direction)")
        self.assertEqual(
            net_sign(by_seq[("mortgage", "yield", "dealers", "repo")]),
            {"sign": -1, "reversed": True},
        )
        self.assertEqual(
            net_sign(by_seq[("mortgage", "yield", "hf", "repo")]),
            {"sign": 0, "reversed": True},
        )

    def test_unconnected_pair_within_three_hops(self):
        paths = find_chains(self.neighbors, self.edge_of, "banks", "cftc", 3)
        self.assertEqual(paths, [])

    def test_same_node_returns_no_paths(self):
        paths = find_chains(self.neighbors, self.edge_of, "mortgage", "mortgage", 3)
        self.assertEqual(paths, [])

    def test_every_stored_edge_resolves_to_its_own_direction(self):
        # A pair with a link stored a->b must resolve forward=True for (a,b)
        # -- even when the reverse pair b->a is ALSO separately stored (e.g.
        # banks/fdic, equit/etf both exist as distinct, separately-cited
        # edges in this graph). find_link must never let one direction's
        # citation/sign shadow the other's.
        for (s, t, w, sign) in self.edges:
            result = find_link(self.edge_of, s, t)
            self.assertTrue(
                result["forward"],
                f"{s}->{t} should resolve forward=True (its own stored edge), got {result}",
            )
            self.assertEqual(result["sign"], sign)

    def test_all_forward_path_computes_net_sign(self):
        paths = find_chains(self.neighbors, self.edge_of, "ffr", "tech", 3)
        direct = next(
            p for p in paths if [p[0][0]] + [hop[1] for hop in p] == ["ffr", "tech"]
        )
        self.assertEqual(net_sign(direct), {"sign": -1, "reversed": False})
        three_hop = next(
            p for p in paths
            if [p[0][0]] + [hop[1] for hop in p] == ["ffr", "credit", "equit", "tech"]
        )
        self.assertEqual(net_sign(three_hop), {"sign": 1, "reversed": False})

    def test_reverse_label_present_in_render_source(self):
        # The parity test (test_chain_reaction_js_parity.py) guards the
        # COMPUTATION of {sign, reversed} -- it never renders anything, so it
        # would stay green even if the "(reverse)" label were silently
        # deleted from renderChainCard. That label is the one thing standing
        # between an honest reversed-direction net sign and one that reads
        # as if it answered the forward question the user actually asked.
        # This is a cheap static guard on the presentation layer, not a
        # replacement for the parity test's computation guard.
        with open(MAP_PATH, encoding="utf-8") as f:
            html = f.read()
        start = html.index("function renderChainCard(path) {")
        end = html.index("\n}\n", start)
        render_source = html[start:end]
        self.assertIn(
            "net.reversed",
            render_source,
            "renderChainCard should branch on net.reversed to label a reversed net sign",
        )
        self.assertIn(
            "(reverse)",
            render_source,
            "renderChainCard should render the literal '(reverse)' qualifier "
            "for an all-backward path's net-sign badge",
        )


if __name__ == "__main__":
    unittest.main()
