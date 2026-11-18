# Web Crawling dan Analisis PageRank

Project mata kuliah Pencarian & Penambangan Web.

Alur: input link website + judul paper -> crawling (BFS) -> graph keterhubungan -> PageRank -> ranking website terpenting.

## Struktur file

```
pagerank_crawler/
├── app.py              # UI Streamlit (input, parameter, hasil)
├── crawler.py          # Web crawler BFS (requests + BeautifulSoup, robots.txt)
├── pagerank_utils.py   # PageRank power iteration, tabel ranking, relevansi judul
├── visualizer.py       # Graph interaktif (pyvis)
├── requirements.txt
└── README.md
```

## Menjalankan lokal

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy di server laboratorium

```bash
git clone <repo> && cd pagerank_crawler
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 > app.log 2>&1 &
```

Buka `http://<IP-server>:8501`. Untuk jalan permanen, gunakan systemd atau screen/tmux.

## Catatan

- Rumus: PR(i) = (1-d)/N + d * (sum PR(j)/out(j) + dangling/N), d = 0.85.
- Hasil dibandingkan dengan `networkx.pagerank` sebagai verifikasi.
- Level node: Website (domain) atau Halaman (URL).
- Jeda antar request dan robots.txt diaktifkan agar crawling sopan.
- Judul paper dipakai sebagai acuan skor relevansi (kata kunci judul vs teks halaman).
