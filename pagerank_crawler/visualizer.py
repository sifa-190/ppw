"""Graph keterhubungan website (pyvis) bertema gelap dengan gradasi warna berdasarkan PageRank.

Interaksi: klik sebuah node -> hanya node itu dan SEMUA website yang merujuk ke node itu
(punya tautan menuju node itu) yang ditampilkan, node lain disembunyikan.
Kembali ke graf penuh: klik area kosong, tekan Esc, atau klik tombol "Kembali".
"""
import json
import math

from pyvis.network import Network

SEED_COLOR = "#fb7185"  # koral
# gradasi PageRank rendah -> tinggi: cyan -> teal -> lime -> emas
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


# JavaScript interaksi klik-untuk-fokus. __DATA__ diganti JSON dari Python.
_FOCUS_JS = r"""
<script>
(function () {
  var DATA = __DATA__;
  var focused = null, saved = null, extraNodes = [], extraEdges = [];

  var bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;left:12px;top:10px;z-index:10;max-width:70%;padding:8px 12px;' +
    'border-radius:10px;background:rgba(15,31,29,.92);border:1px solid #1c3330;color:#e2e8f0;' +
    'font:13px/1.45 system-ui,sans-serif;';
  document.body.appendChild(bar);

  function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }
  function hint() { bar.innerHTML = 'Klik sebuah node untuk melihat website yang merujuk ke sana'; }
  hint();

  function addNode(id) {
    var s = DATA.nodes[id];
    nodes.add({id: id, label: s.label, size: s.size, color: s.color, borderWidth: 0, shape: 'dot',
               title: id + '\nPageRank: ' + s.pr.toFixed(5)});
  }

  function restore(silent) {
    if (focused === null) return;
    edges.remove(extraEdges); nodes.remove(extraNodes);
    extraEdges = []; extraNodes = [];
    nodes.update(nodes.get().map(function (n) { return {id: n.id, hidden: false}; }));
    edges.update(edges.get().map(function (e) { return {id: e.id, hidden: false}; }));
    Object.keys(saved).forEach(function (i) {
      if (nodes.get(i)) network.moveNode(i, saved[i].x, saved[i].y);
    });
    focused = null; saved = null;
    if (!silent) {
      network.setOptions({physics: {enabled: true}});
      network.fit({animation: {duration: 500}});
      hint();
    }
  }

  function focusNode(id) {
    if (focused !== null) restore(true);          // balik ke graf penuh dulu
    var refs = DATA.edges.filter(function (e) { return e[1] === id && e[0] !== id; })
      .map(function (e) { return {id: e[0], w: e[2]}; });
    refs.sort(function (a, b) { return DATA.nodes[b.id].pr - DATA.nodes[a.id].pr; });

    focused = id;
    saved = network.getPositions();
    network.setOptions({physics: {enabled: false}});

    var keep = {}; keep[id] = true;
    refs.forEach(function (r) { keep[r.id] = true; });
    Object.keys(keep).forEach(function (i) {
      if (!nodes.get(i)) { addNode(i); extraNodes.push(i); }   // perujuk di luar daftar yang digambar
    });

    nodes.update(nodes.get().map(function (n) { return {id: n.id, hidden: !keep[n.id]}; }));
    edges.update(edges.get().map(function (e) { return {id: e.id, hidden: true}; }));

    refs.forEach(function (r) {
      var ex = edges.get({filter: function (e) { return e.from === r.id && e.to === id; }});
      if (ex.length) {
        edges.update({id: ex[0].id, hidden: false});
      } else {
        var eid = 'x_' + r.id + '>' + id;
        edges.add({id: eid, from: r.id, to: id, arrows: 'to', width: Math.min(1 + Math.log(r.w), 5),
                   color: {color: 'rgba(148,163,184,0.55)', highlight: '#fbbf24'},
                   title: r.id + ' → ' + id + '\n' + r.w + ' tautan'});
        extraEdges.push(eid);
      }
    });

    // tata letak: node fokus di tengah, perujuk melingkar (PageRank tertinggi di lingkaran dalam)
    var c = saved[id] || {x: 0, y: 0};
    network.moveNode(id, c.x, c.y);
    var idx = 0, ring = 0;
    while (idx < refs.length) {
      var r = 170 + ring * 120;
      var cap = Math.max(6, Math.floor(2 * Math.PI * r / 75));
      var n = Math.min(cap, refs.length - idx);
      for (var k = 0; k < n; k++) {
        var a = 2 * Math.PI * k / n + ring * 0.35;
        network.moveNode(refs[idx].id, c.x + r * Math.cos(a), c.y + r * Math.sin(a));
        idx++;
      }
      ring++;
    }
    network.fit({nodes: Object.keys(keep), animation: {duration: 600}});

    var s = DATA.nodes[id];
    bar.innerHTML = 'Fokus: <b>' + esc(id) + '</b> (PageRank ' + s.pr.toFixed(5) + ')<br>' +
      (refs.length ? '<b>' + refs.length + '</b> website merujuk ke sini' : 'Belum ada website yang merujuk ke sini') +
      ' · klik area kosong / Esc, atau <a href="#" id="pr-reset" style="color:#2dd4bf">Kembali</a>';
    var btn = document.getElementById('pr-reset');
    if (btn) btn.onclick = function (ev) { ev.preventDefault(); restore(false); };
  }

  network.on('click', function (p) {
    if (p.nodes.length) {
      if (p.nodes[0] !== focused) focusNode(p.nodes[0]);
    } else if (!p.edges.length) {
      restore(false);
    }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') restore(false); });
  if (DATA.leave) document.documentElement.addEventListener('mouseleave', function () { restore(false); });
})();
</script>
"""


def build_graph_html(edges, scores, seed=None, top_n=40, height="680px", restore_on_leave=False):
    """seed: satu nama website atau kumpulan nama website (titik awal crawling).

    restore_on_leave=True: graf otomatis kembali penuh saat kursor keluar dari area graf.
    """
    seeds = {seed} if isinstance(seed, str) else set(seed or [])
    ranked = sorted(scores, key=scores.get, reverse=True)
    visible = set(ranked[:top_n])
    visible |= {s for s in seeds if s in scores}
    sub = {e: w for e, w in edges.items() if e[0] in visible and e[1] in visible}

    vals = [scores[n] for n in visible]
    lo, hi = min(vals), max(vals)

    def style(node):
        t = ((scores[node] - lo) / (hi - lo)) if hi > lo else 0.5
        t = max(0.0, min(1.0, t)) ** 0.6  # perhalus agar variasi warna terlihat
        size = 12 + 38 * t
        color = score_color(t)
        if node in seeds:
            color, size = SEED_COLOR, max(size, 26)
        label = node if len(node) <= 28 else node[:25] + "..."
        return label, color, size

    net = Network(height=height, width="100%", directed=True, bgcolor="#07110f",
                  font_color="#e2e8f0", notebook=False, cdn_resources="in_line")

    for node in visible:
        label, color, size = style(node)
        net.add_node(node, label=label, size=size, color=color, borderWidth=0,
                     title=f"{node}\nPageRank: {scores[node]:.5f}")

    for (s, d), w in sub.items():
        net.add_edge(s, d, arrows="to", width=min(1 + math.log(w), 5),
                     color={"color": "rgba(148,163,184,0.35)", "highlight": "#fbbf24"},
                     title=f"{s} → {d}\n{w} tautan")

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
    html = net.generate_html()

    # Data untuk mode fokus: seluruh tautan graf (bukan hanya yang digambar),
    # supaya SEMUA website perujuk bisa ditampilkan saat sebuah node diklik.
    data = {
        "nodes": {n: dict(zip(("label", "color", "size"), style(n)), pr=scores[n]) for n in scores},
        "edges": [[s, d, w] for (s, d), w in edges.items()],
        "leave": bool(restore_on_leave),
    }
    payload = json.dumps(data).replace("</", "<\\/")
    return html.replace("</body>", _FOCUS_JS.replace("__DATA__", payload) + "</body>")