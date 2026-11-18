"""Graph keterhubungan website (pyvis) bertema gelap dengan gradasi warna berdasarkan PageRank."""
import math

from pyvis.network import Network

SEED_COLOR = "#fb7185"  # koral
STOPS = [(0.0, "#22d3ee"), (0.35, "#2dd4bf"), (0.7, "#a3e635"), (1.0, "#fbbf24")]


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def score_color(t):
    """t di [0,1] -> warna hex pada gradasi."""
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            a, b = _rgb(c0), _rgb(c1)
            return "#%02x%02x%02x" % tuple(round(x + (y - x) * f) for x, y in zip(a, b))
    return STOPS[-1][1]


def build_graph_html(edges, scores, seed=None, top_n=40, height="680px"):
    ranked = sorted(scores, key=scores.get, reverse=True)
    visible = set(ranked[:top_n])
    if seed in scores:
        visible.add(seed)
    sub = {e: w for e, w in edges.items() if e[0] in visible and e[1] in visible}

    vals = [scores[n] for n in visible]
    lo, hi = min(vals), max(vals)

    net = Network(height=height, width="100%", directed=True, bgcolor="#0b1020",
                  font_color="#e2e8f0", notebook=False, cdn_resources="in_line")

    for node in visible:
        t = ((scores[node] - lo) / (hi - lo)) if hi > lo else 0.5
        t = t ** 0.6  # perhalus agar variasi warna terlihat
        size = 12 + 38 * t
        color = score_color(t)
        if node == seed:
            color, size = SEED_COLOR, max(size, 26)
        label = node if len(node) <= 28 else node[:25] + "..."
        net.add_node(node, label=label, size=size, color=color, borderWidth=0,
                     title=f"{node}<br>PageRank: {scores[node]:.5f}")

    for (s, d), w in sub.items():
        net.add_edge(s, d, arrows="to", width=min(1 + math.log(w), 5),
                     color={"color": "rgba(148,163,184,0.35)", "highlight": "#f472b6"},
                     title=f"{s} → {d}<br>{w} tautan")

    net.set_options("""
    {
      "nodes": {"font": {"size": 13, "color": "#e2e8f0"}},
      "edges": {"smooth": {"type": "continuous"}, "arrows": {"to": {"scaleFactor": 0.5}}},
      "physics": {"barnesHut": {"gravitationalConstant": -9000, "springLength": 170,
                                "springConstant": 0.03, "damping": 0.4},
                  "stabilization": {"iterations": 150}},
      "interaction": {"hover": true, "navigationButtons": true, "tooltipDelay": 100}
    }
    """)
    return net.generate_html()