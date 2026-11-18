"""Web Crawler & PageRank (Streamlit).
Jalankan: python -m streamlit run app.py
"""
import html
from collections import Counter

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from crawler import Crawler, get_domain, normalize_url
from pagerank_utils import (aggregate_to_domain, build_ranking_table, domain_texts,
                            pagerank, related_websites)
from visualizer import build_graph_html

st.set_page_config(page_title="Web Crawler & PageRank", page_icon="🕸️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 1200px;}
.hero h1 {
    font-size: 2.1rem; font-weight: 800; margin: 0 0 .2rem 0;
    background: linear-gradient(90deg, #2dd4bf, #a3e635, #fbbf24);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p {color: #94a3b8; margin: 0 0 1.2rem 0;}
div[data-testid="stForm"] {border: 0; padding: 0;}
div[data-testid="stFormSubmitButton"] button,
button[kind="primaryFormSubmit"], button[kind="secondaryFormSubmit"] {
    background: linear-gradient(90deg, #0d9488, #0ea5e9); border: 0; color: #fff;
    font-weight: 700; height: 2.6rem; border-radius: 10px;
}
div[data-testid="stFormSubmitButton"] button:hover {filter: brightness(1.12); color: #fff;}
.kpi {background: #0f1f1d; border: 1px solid #1c3330; border-radius: 14px; padding: 14px 18px;}
.kpi .label {font-size: 11px; letter-spacing: .12em; color: #94a3b8; text-transform: uppercase;}
.kpi .value {font-size: 26px; font-weight: 700; color: #f8fafc; margin-top: 4px;
             overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}
.kpi.top {border-color: #0f766e; background: linear-gradient(135deg, #052e2b, #0f1f1d);}
.kpi.top .value {font-size: 20px; color: #fde68a; padding-top: 4px;}
.legend {color: #94a3b8; font-size: 13px; margin-top: .4rem;}
.legend .dot {display: inline-block; width: 10px; height: 10px; border-radius: 50%;
              background: #fb7185; margin-right: 4px;}
.legend .bar {display: inline-block; width: 70px; height: 8px; border-radius: 4px; margin: 0 4px;
              background: linear-gradient(90deg, #22d3ee, #2dd4bf, #a3e635, #fbbf24);}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="hero"><h1>🕸️ Web Crawler &amp; PageRank</h1>'
    '<p>Pencarian &amp; Penambangan Web · temukan website paling berpengaruh dari jaringan tautan</p></div>',
    unsafe_allow_html=True,
)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### ⚙️ Pengaturan Crawl")
    max_depth = st.slider("Kedalaman (depth)", 1, 4, 2, help="Seberapa jauh tautan diikuti dari website awal.")
    max_pages = st.slider("Maks. total halaman", 10, 200, 50, step=5)
    per_domain = st.slider("Maks. halaman per website", 1, 20, 5)
    delay = st.slider("Jeda antar request (detik)", 0.0, 3.0, 0.5, 0.25)
    time_limit = st.slider("Batas waktu crawl (detik)", 30, 300, 90, 10)
    respect_robots = st.checkbox("Patuhi robots.txt", value=True)
    weighted = st.checkbox("Bobot edge = jumlah tautan", value=True)
    damping = st.slider("Damping factor PageRank", 0.5, 0.99, 0.85, 0.01)
    st.caption("Tips: mulai dengan pengaturan kecil agar cepat, lalu naikkan bertahap.")

# ---------------- Input ----------------
with st.form("input_form"):
    c1, c2, c3 = st.columns([3, 3, 1])
    seed_url = c1.text_input("Link website", placeholder="https://www.contoh.ac.id/",
                             label_visibility="collapsed")
    paper_title = c2.text_input("Judul paper", placeholder="Judul paper (untuk skor relevansi)",
                                label_visibility="collapsed")
    submitted = c3.form_submit_button("Analisis", use_container_width=True)
st.caption("Contoh: `https://www.wikipedia.org` · `https://news.ycombinator.com` · `https://github.com`")

if submitted:
    url = seed_url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not url or normalize_url(url) is None:
        st.error("Masukkan link website yang valid, misalnya https://www.contoh.ac.id/")
        st.stop()

    bar = st.progress(0.0, text="Memulai crawling...")

    def on_progress(done, total, current):
        bar.progress(min(done / total, 1.0), text=f"[{done}/{total}] {current}")

    crawler = Crawler(max_depth=max_depth, max_pages=max_pages, max_pages_per_domain=per_domain,
                      delay=delay, time_limit=time_limit, respect_robots=respect_robots)
    try:
        result = crawler.crawl(url, progress_cb=on_progress)
    except ValueError as e:
        bar.empty()
        st.error(str(e))
        st.stop()
    bar.empty()

    st.session_state["result"] = result
    st.session_state["seed"] = normalize_url(url)
    st.session_state["title"] = paper_title.strip()

if "result" not in st.session_state:
    st.info("Masukkan link website dan judul paper, lalu klik **Analisis**.")
    st.stop()

# ---------------- Analisis ----------------
result = st.session_state["result"]
seed_node = get_domain(st.session_state["seed"])
title = st.session_state["title"]

edges = aggregate_to_domain(result.edges)
if not edges:
    st.warning("Tidak ditemukan tautan ke website lain. Coba link lain atau naikkan kedalaman.")
    st.stop()

scores, iters = pagerank(edges, damping=damping, weighted=weighted)
texts = domain_texts(result.pages)
crawled_count = Counter(get_domain(u) for u in result.pages)
table = build_ranking_table(scores, edges, crawled_count, texts, title)
top_site = table.iloc[0]["Website"]


def kpi(label, value, cls=""):
    return f'<div class="kpi {cls}"><div class="label">{label}</div><div class="value">{html.escape(str(value))}</div></div>'


k1, k2, k3, k4 = st.columns(4)
k1.markdown(kpi("Website ditemukan", len(scores)), unsafe_allow_html=True)
k2.markdown(kpi("Halaman di-crawl", len(result.pages)), unsafe_allow_html=True)
k3.markdown(kpi("Tautan antarwebsite", len(edges)), unsafe_allow_html=True)
k4.markdown(kpi("🏆 Paling penting", top_site, "top"), unsafe_allow_html=True)

info = f"Crawl selesai dalam {result.elapsed:.0f} detik ({result.stopped_reason}) · PageRank konvergen dalam {iters} iterasi"
if title:
    info = f"📄 Paper acuan: *{title}* · " + info
st.caption(info)

tab_graph, tab_rank, tab_rel, tab_dl = st.tabs(
    ["🕸️ Graph", "🏆 Peringkat PageRank", "🔗 Website Terkait", "📥 Unduh"])

# ---- Graph
with tab_graph:
    n_nodes = len(scores)
    if n_nodes > 5:
        top_n = st.slider("Jumlah website ditampilkan (berdasarkan PageRank tertinggi)",
                          5, min(100, n_nodes), min(40, n_nodes))
    else:
        top_n = n_nodes
    graph_html = build_graph_html(edges, scores, seed=seed_node, top_n=top_n)
    components.html(graph_html, height=700, scrolling=False)
    st.markdown(
        '<div class="legend"><span class="dot"></span>website awal · warna '
        '<span class="bar"></span> PageRank rendah → tinggi · ukuran node = PageRank · '
        'anak panah = arah tautan · scroll untuk zoom, seret untuk menggeser</div>',
        unsafe_allow_html=True)

# ---- Peringkat
with tab_rank:
    cfg = {"PageRank": st.column_config.ProgressColumn(
        "PageRank", format="%.5f", min_value=0.0, max_value=float(table["PageRank"].max()))}
    if "Relevansi Judul" in table.columns:
        cfg["Relevansi Judul"] = st.column_config.NumberColumn("Relevansi Judul", format="%.2f")
    st.dataframe(table, use_container_width=True, column_config=cfg, height=420)
    st.bar_chart(table.head(15).set_index("Website")["PageRank"])
    try:
        import networkx as nx
        g = nx.DiGraph()
        for (s, d), w in edges.items():
            g.add_edge(s, d, weight=w if weighted else 1)
        nx_scores = nx.pagerank(g, alpha=damping, weight="weight")
        diff = max(abs(scores[n] - nx_scores[n]) for n in scores)
        st.caption(f"Verifikasi: selisih maksimum dengan networkx.pagerank = {diff:.1e}")
    except Exception:
        pass

# ---- Website terkait
with tab_rel:
    rel = related_websites(seed_node, edges, scores)
    st.markdown(f"**Website yang terhubung langsung dengan `{seed_node}`**")
    if rel.empty:
        st.info("Tidak ada website lain yang terhubung langsung dengan website awal.")
    else:
        st.dataframe(rel, use_container_width=True, height=360, column_config={
            "PageRank": st.column_config.NumberColumn("PageRank", format="%.5f")})
    if title and "Relevansi Judul" in table.columns:
        st.markdown(f"**Website paling relevan dengan judul paper** · *{title}*")
        rel_t = table[table["Relevansi Judul"].fillna(0) > 0].sort_values(
            ["Relevansi Judul", "PageRank"], ascending=False).head(10)
        if rel_t.empty:
            st.info("Belum ada website yang memuat kata kunci judul paper pada halaman yang di-crawl.")
        else:
            st.dataframe(rel_t[["Website", "Relevansi Judul", "PageRank"]], use_container_width=True,
                         column_config={"PageRank": st.column_config.NumberColumn("PageRank", format="%.5f")})

# ---- Unduh
with tab_dl:
    edge_df = pd.DataFrame([(s, d, w) for (s, d), w in edges.items()],
                           columns=["Sumber", "Tujuan", "Bobot"])
    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇️ Peringkat PageRank (CSV)", table.to_csv().encode("utf-8"),
                       "peringkat_pagerank.csv", "text/csv", use_container_width=True)
    d2.download_button("⬇️ Daftar tautan (CSV)", edge_df.to_csv(index=False).encode("utf-8"),
                       "tautan_antarwebsite.csv", "text/csv", use_container_width=True)
    d3.download_button("⬇️ Graph interaktif (HTML)", graph_html.encode("utf-8"),
                       "graph_pagerank.html", "text/html", use_container_width=True)
    if result.errors:
        with st.expander(f"Halaman gagal / dilewati ({len(result.errors)})"):
            st.json(result.errors)