"""PageRank berbobot (power iteration), tabel ranking, website terkait, relevansi judul paper."""
import re
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from crawler import get_domain

STOPWORDS = {
    "the", "of", "and", "a", "an", "in", "on", "for", "to", "with", "by", "using", "based",
    "yang", "dan", "di", "ke", "dari", "untuk", "pada", "dengan", "atau", "sebuah", "analisis",
}


def aggregate_to_domain(page_edges):
    """Graph level-URL -> level-website. Bobot = jumlah tautan antarhalaman. Self-loop dibuang."""
    agg = Counter()
    for src, dst in page_edges:
        s, d = get_domain(src), get_domain(dst)
        if s != d:
            agg[(s, d)] += 1
    return agg


def pagerank(edges, damping=0.85, weighted=True, max_iter=200, tol=1e-10):
    """
    PageRank dengan power iteration.
    PR(i) = (1-d)/N + d * ( sum_{j->i} PR(j) * w(j,i)/W(j) + PR_dangling/N )
    Mengembalikan (dict node->skor, jumlah iterasi).
    """
    nodes = sorted({n for e in edges for n in e})
    n = len(nodes)
    if n == 0:
        return {}, 0
    idx = {node: i for i, node in enumerate(nodes)}

    src = np.array([idx[s] for s, _ in edges])
    dst = np.array([idx[d] for _, d in edges])
    w = np.array([edges[e] if weighted else 1.0 for e in edges], dtype=float)
    out_sum = np.bincount(src, weights=w, minlength=n)
    wn = w / out_sum[src]
    dangling = out_sum == 0

    pr = np.full(n, 1.0 / n)
    iters = 0
    for iters in range(1, max_iter + 1):
        inflow = np.bincount(dst, weights=pr[src] * wn, minlength=n)
        new = damping * (inflow + pr[dangling].sum() / n) + (1.0 - damping) / n
        done = np.abs(new - pr).sum() < tol
        pr = new
        if done:
            break
    return {nodes[i]: float(pr[i]) for i in range(n)}, iters


def domain_texts(pages):
    """Gabungkan judul + teks semua halaman yang di-crawl per website."""
    texts = defaultdict(str)
    for url, info in pages.items():
        texts[get_domain(url)] += f" {info.get('title', '')} {info.get('text', '')}"
    return texts


def _tokens(text):
    return [t for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 2]


def relevance(title_query, text):
    """Proporsi kata kunci judul paper yang muncul di teks website (0..1)."""
    q = set(_tokens(title_query))
    if not q or not text:
        return 0.0
    return round(len(q & set(_tokens(text))) / len(q), 3)


def build_ranking_table(scores, edges, crawled_count, texts=None, title_query=""):
    in_n, out_n = Counter(), Counter()
    for (s, d) in edges:
        out_n[s] += 1
        in_n[d] += 1
    rows = []
    for node, score in scores.items():
        row = {
            "Website": node,
            "PageRank": score,
            "Tautan masuk": in_n[node],
            "Tautan keluar": out_n[node],
            "Halaman di-crawl": crawled_count.get(node, 0),
        }
        if title_query:
            row["Relevansi Judul"] = relevance(title_query, texts[node]) if node in texts else None
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("PageRank", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "Peringkat"
    return df


def related_websites(seed, edges, scores):
    """Website yang terhubung langsung dengan seed (dua arah)."""
    rel = {}
    for (s, d), w in edges.items():
        if s == seed:
            rel.setdefault(d, {"out": 0, "in": 0})["out"] = w
        elif d == seed:
            rel.setdefault(s, {"out": 0, "in": 0})["in"] = w
    rows = []
    for node, v in rel.items():
        if v["out"] and v["in"]:
            arah = "↔ Dua arah"
        elif v["out"]:
            arah = "Seed → Website"
        else:
            arah = "Website → Seed"
        rows.append({"Website": node, "Hubungan": arah, "Tautan dari seed": v["out"],
                     "Tautan ke seed": v["in"], "PageRank": scores.get(node, 0.0)})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values("PageRank", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "No"
    return df