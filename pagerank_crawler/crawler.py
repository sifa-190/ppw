"""Modul web crawling: BFS dari seed URL, mengekstrak tautan antarhalaman/website."""
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urldefrag, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "PPW-LabCrawler/1.0 (tugas kuliah Pencarian & Penambangan Web)"}
SKIP_EXT = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".zip", ".rar",
    ".gz", ".mp3", ".mp4", ".avi", ".mov", ".doc", ".docx", ".xls", ".xlsx", ".ppt",
    ".pptx", ".css", ".js", ".xml", ".json",
)


@dataclass
class CrawlResult:
    edges: set = field(default_factory=set)     # {(url_sumber, url_tujuan)}
    pages: dict = field(default_factory=dict)   # url -> {title, text, depth}
    errors: dict = field(default_factory=dict)  # url -> pesan error
    elapsed: float = 0.0
    stopped_reason: str = "selesai"


def normalize_url(url: str):
    """Hapus fragment, rapikan trailing slash, hanya http/https."""
    if not url:
        return None
    url, _ = urldefrag(url.strip())
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        return None
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if path.lower().endswith(SKIP_EXT):
        return None
    return p._replace(netloc=p.netloc.lower(), path=path, fragment="").geturl()


def get_domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


class Crawler:
    def __init__(self, max_depth=2, max_pages=50, max_pages_per_domain=5, delay=0.5,
                 time_limit=90, respect_robots=True, timeout=10, max_links_per_page=150):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.max_pages_per_domain = max_pages_per_domain
        self.delay = delay
        self.time_limit = time_limit
        self.respect_robots = respect_robots
        self.timeout = timeout
        self.max_links_per_page = max_links_per_page
        self._robots = {}

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp = RobotFileParser()
            try:
                resp = requests.get(base + "/robots.txt", headers=HEADERS, timeout=self.timeout)
                rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
            except requests.RequestException:
                rp.parse([])
            self._robots[base] = rp
        return self._robots[base].can_fetch(HEADERS["User-Agent"], url)

    def crawl(self, seed_url: str, progress_cb=None) -> CrawlResult:
        seed = normalize_url(seed_url)
        if seed is None:
            raise ValueError("URL tidak valid (harus diawali http:// atau https://)")

        result = CrawlResult()
        start = time.time()
        queue = deque([(seed, 0)])
        queued = {seed}
        per_domain = Counter()

        while queue:
            if len(result.pages) >= self.max_pages:
                result.stopped_reason = "mencapai batas total halaman"
                break
            if time.time() - start > self.time_limit:
                result.stopped_reason = "mencapai batas waktu"
                break

            url, depth = queue.popleft()
            domain = get_domain(url)
            if per_domain[domain] >= self.max_pages_per_domain:
                continue  # kuota halaman untuk website ini habis
            per_domain[domain] += 1

            if not self._allowed(url):
                result.errors[url] = "Diblokir robots.txt"
                continue
            try:
                resp = requests.get(url, headers=HEADERS, timeout=self.timeout)
                ctype = resp.headers.get("Content-Type", "")
                if resp.status_code != 200 or "text/html" not in ctype:
                    result.errors[url] = f"Status {resp.status_code} / {ctype or 'tanpa content-type'}"
                    continue
            except requests.RequestException as e:
                result.errors[url] = str(e)[:120]
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.get_text(strip=True) if soup.title else url
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ", strip=True).split())[:5000]
            result.pages[url] = {"title": title, "text": text, "depth": depth}

            if progress_cb:
                progress_cb(len(result.pages), self.max_pages, url)

            links = []
            for a in soup.find_all("a", href=True):
                target = normalize_url(urljoin(url, a["href"]))
                if target and target != url and target not in links:
                    links.append(target)
                if len(links) >= self.max_links_per_page:
                    break

            for target in links:
                result.edges.add((url, target))
                if depth < self.max_depth and target not in queued:
                    queued.add(target)
                    queue.append((target, depth + 1))

            time.sleep(self.delay)

        result.elapsed = time.time() - start
        return result