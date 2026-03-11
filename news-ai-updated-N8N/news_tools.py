import html
import re
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup

try:
    import trafilatura
except Exception:
    trafilatura = None


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_article_from_url(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        return {
            "title": "",
            "text": "",
            "source": "",
            "url": url,
            "error": f"Failed to fetch URL: {e}",
        }

    title = ""
    text = ""
    source = ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        if soup.title and soup.title.string:
            title = clean_text(soup.title.string)
        source = requests.utils.urlparse(url).netloc
    except Exception:
        pass

    if trafilatura:
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                extracted = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                )
                if extracted:
                    text = clean_text(extracted)
        except Exception:
            pass

    if not text:
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
            text = clean_text(" ".join(paragraphs))
        except Exception:
            text = ""

    return {
        "title": title,
        "text": text,
        "source": source,
        "url": url,
        "error": None,
    }


def build_article_from_text(title: str, text: str) -> dict:
    return {
        "title": clean_text(title),
        "text": clean_text(text),
        "source": "Manual Input",
        "url": "",
        "error": None,
    }


def search_related_articles(query: str, max_results: int = 6) -> list:
    rss_url = (
        f"https://news.google.com/rss/search?q={quote_plus(query)}"
        f"&hl=en-US&gl=US&ceid=US:en"
    )
    feed = feedparser.parse(rss_url)

    results = []
    for entry in feed.entries[:max_results]:
        source_name = ""
        if hasattr(entry, "source") and isinstance(entry.source, dict):
            source_name = entry.source.get("title", "")

        results.append(
            {
                "title": getattr(entry, "title", ""),
                "url": getattr(entry, "link", ""),
                "source": source_name,
                "published": getattr(entry, "published", ""),
                "summary": clean_text(getattr(entry, "summary", "")),
            }
        )
    return results


def fetch_related_articles(query: str, original_url: str = "", max_results: int = 4) -> list:
    items = search_related_articles(query, max_results=max_results + 2)
    enriched = []

    for item in items:
        link = item.get("url", "")
        if not link:
            continue
        if original_url and link == original_url:
            continue

        article = fetch_article_from_url(link)
        if article.get("error"):
            continue

        enriched.append(
            {
                "title": article.get("title", item.get("title", "")),
                "url": link,
                "source": item.get("source", article.get("source", "")),
                "text": article.get("text", ""),
                "published": item.get("published", ""),
            }
        )

        if len(enriched) >= max_results:
            break

    return enriched
