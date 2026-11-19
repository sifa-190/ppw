"""Cari website awal (seed) dari judul paper. Mencoba beberapa sumber berurutan."""
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from crawler import HEADERS, get_domain, normalize_url

SKIP_DOMAINS = {"duckduckgo.com", "google.com", "bing.com", "youtube.com", "facebook.com",
                "twitter.com", "x.com", "instagram.com"}


def _clean(urls, limit):
    out, seen = [], set()
    for u in urls:
        n = normalize_url(u or "")
        if not n:
            continue
        dom = get_domain(n)
        if dom in SKIP_DOMAINS or n in seen:
            continue
        seen.add(n)
        out.append(n)
        if len(out) >= limit:
            break
    return out


def parse_ddg(html, limit=5):
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select("a.result__a, a.result-link"):
        href = a.get("href", "")
        if "uddg=" in href:  # tautan redirect DuckDuckGo
            qs = parse_qs(urlparse(href if "://" in href else "https:" + href).query)
            href = unquote(qs.get("uddg", [""])[0])
        urls.append(href)
    return _clean(urls, limit)


def parse_openalex(data, limit=5):
    urls = []
    for w in data.get("results", []):
        loc = w.get("primary_location") or {}
        urls += [loc.get("landing_page_url"), w.get("doi")]
    return _clean(urls, limit)


def parse_crossref(data, limit=5):
    urls = []
    for it in data.get("message", {}).get("items", []):
        urls.append(((it.get("resource") or {}).get("primary") or {}).get("URL"))
        urls.append(it.get("URL"))
    return _clean(urls, limit)


def find_seeds(title, limit=3, timeout=10):
    """Kembalikan (daftar URL, nama sumber yang berhasil). Kosong jika semua sumber gagal."""
    title = title.strip()
    sources = [
        ("DuckDuckGo", "https://html.duckduckgo.com/html/", {"q": title}, "html", parse_ddg),
        ("OpenAlex", "https://api.openalex.org/works", {"search": title, "per-page": 5}, "json", parse_openalex),
        ("Crossref", "https://api.crossref.org/works",
         {"query.bibliographic": title, "rows": 5}, "json", parse_crossref),
    ]
    for name, url, params, kind, parser in sources:
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if r.status_code != 200:
                continue
            urls = parser(r.text if kind == "html" else r.json(), limit)
            if urls:
                return urls, name
        except (requests.RequestException, ValueError):
            continue
    return [], ""
