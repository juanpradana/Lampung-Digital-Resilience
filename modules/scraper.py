"""
Scraper Module - Mengambil data REAL dari Google News RSS dan Google Search.

Sumber data:
1. Google News RSS - Feed berita terkait gangguan internet di Lampung
2. Google Search - Scraping hasil pencarian terkini

Semua sumber gratis, tanpa API key.
"""

import logging
import re
import html
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Query pencarian untuk berbagai aspek gangguan digital di Lampung
SEARCH_QUERIES = [
    "gangguan internet Lampung",
    "indihome down Lampung",
    "sinyal hilang Lampung",
    "mati lampu Bandar Lampung",
    "Telkomsel gangguan Lampung",
    "Biznet gangguan Lampung",
    "internet mati Lampung",
    "wifi gangguan Bandar Lampung",
    "PLN padam Lampung",
    "jaringan down Lampung",
]

GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"


def _clean_html(raw_html):
    """Bersihkan tag HTML dari teks."""
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", str(raw_html))
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _parse_rss_date(entry):
    """Parse tanggal dari entry RSS ke ISO format."""
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
    except Exception:
        pass
    try:
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
    except Exception:
        pass
    return datetime.now(timezone.utc).isoformat()


def fetch_google_news_rss(queries=None, max_per_query=15):
    """
    Ambil berita dari Google News RSS untuk setiap query.

    Args:
        queries: list of search query strings. Default: SEARCH_QUERIES.
        max_per_query: max entries per query.

    Returns:
        list[dict]: Daftar berita mentah.
    """
    if queries is None:
        queries = SEARCH_QUERIES

    all_entries = []
    seen_titles = set()

    for query in queries:
        try:
            url = GOOGLE_NEWS_RSS_BASE.format(query=quote_plus(query))
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                logger.warning("RSS feed error untuk query '%s': %s", query, feed.bozo_exception)
                continue

            for entry in feed.entries[:max_per_query]:
                title = _clean_html(entry.get("title", ""))

                # Deduplikasi berdasarkan judul
                title_key = title.lower().strip()
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                summary = _clean_html(entry.get("summary", ""))
                timestamp = _parse_rss_date(entry)
                source_name = ""
                if hasattr(entry, "source") and hasattr(entry.source, "title"):
                    source_name = entry.source.title

                all_entries.append({
                    "id": f"gnews_{hash(title_key) & 0xFFFFFFFF:08x}",
                    "timestamp": timestamp,
                    "text": f"{title}. {summary}".strip(),
                    "title": title,
                    "summary": summary,
                    "link": entry.get("link", ""),
                    "source": "google_news",
                    "source_name": source_name,
                    "query": query,
                })

        except Exception as e:
            logger.error("Gagal fetch RSS untuk query '%s': %s", query, e)

    logger.info("Google News RSS: %d entries dari %d queries", len(all_entries), len(queries))
    return all_entries


def fetch_google_search(queries=None, max_per_query=10):
    """
    Scrape hasil Google Search untuk setiap query.

    Args:
        queries: list of search query strings. Default: subset SEARCH_QUERIES.
        max_per_query: max results per query.

    Returns:
        list[dict]: Daftar hasil pencarian mentah.
    """
    if queries is None:
        queries = SEARCH_QUERIES[:5]  # Batasi agar tidak kena rate limit

    all_results = []
    seen_urls = set()

    for query in queries:
        try:
            search_url = (
                f"https://www.google.com/search?"
                f"q={quote_plus(query)}&hl=id&gl=id&num={max_per_query}"
                f"&tbs=qdr:d"  # Hasil 24 jam terakhir
            )

            resp = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                logger.warning("Google Search status %d untuk '%s'", resp.status_code, query)
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Parse hasil pencarian Google
            for g_div in soup.select("div.g, div[data-sokoban-container]"):
                try:
                    # Ambil judul
                    title_el = g_div.select_one("h3")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)

                    # Ambil URL
                    link_el = g_div.select_one("a[href]")
                    link = link_el["href"] if link_el else ""
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    # Ambil snippet
                    snippet_el = (
                        g_div.select_one("div[data-sncf], div.VwiC3b, span.aCOpRe")
                    )
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    all_results.append({
                        "id": f"gsearch_{hash(link) & 0xFFFFFFFF:08x}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "text": f"{title}. {snippet}".strip(),
                        "title": title,
                        "summary": snippet,
                        "link": link,
                        "source": "google_search",
                        "source_name": "",
                        "query": query,
                    })

                except Exception as e:
                    logger.debug("Gagal parse satu hasil Google: %s", e)
                    continue

        except Exception as e:
            logger.error("Gagal fetch Google Search untuk '%s': %s", query, e)

    logger.info("Google Search: %d results dari %d queries", len(all_results), len(queries))
    return all_results


def fetch_all_social_signals():
    """
    Gabungkan semua sumber data sosial (Google News RSS + Google Search).
    Deduplikasi berdasarkan judul/teks yang mirip.

    Returns:
        list[dict]: Semua sinyal sosial mentah, siap diproses NLP.
    """
    all_signals = []

    # Sumber 1: Google News RSS (paling reliable)
    rss_results = fetch_google_news_rss()
    all_signals.extend(rss_results)

    # Sumber 2: Google Search (supplementary)
    search_results = fetch_google_search()
    all_signals.extend(search_results)

    # Deduplikasi final berdasarkan similarity judul
    unique = []
    seen_texts = set()
    for signal in all_signals:
        # Gunakan 50 karakter pertama sebagai key deduplikasi
        text_key = signal["text"][:50].lower().strip()
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            unique.append(signal)

    # Sort by timestamp desc
    unique.sort(key=lambda x: x["timestamp"], reverse=True)

    logger.info("Total sinyal sosial unik: %d", len(unique))
    return unique
