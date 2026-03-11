import html
import re
from urllib.parse import quote_plus, urlparse

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


def extract_domain_name(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        netloc = netloc.replace("www.", "")
        return netloc
    except Exception:
        return ""


def resolve_final_url(url: str) -> str:
    if not url:
        return ""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        return response.url or url
    except Exception:
        return url


def fetch_article_from_url(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        )
    }

    final_url = resolve_final_url(url)

    try:
        response = requests.get(final_url, headers=headers, timeout=20)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        return {
            "title": "",
            "text": "",
            "source": "",
            "url": final_url or url,
            "error": f"Failed to fetch URL: {e}",
        }

    title = ""
    text = ""
    source = extract_domain_name(final_url)

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        if soup.title and soup.title.string:
            title = clean_text(soup.title.string)

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            og_title_text = clean_text(og_title.get("content"))
            if og_title_text:
                title = og_title_text

        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            source = clean_text(og_site.get("content")) or source

    except Exception:
        pass

    if trafilatura:
        try:
            downloaded = trafilatura.fetch_url(final_url)
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

    if title.strip().lower() in ["google news", "news.google.com", "untitled", ""]:
        title = source or extract_domain_name(final_url) or "Related source"

    if source.strip().lower() in ["google news", "news.google.com", ""]:
        source = extract_domain_name(final_url) or "Unknown"

    return {
        "title": title,
        "text": text,
        "source": source,
        "url": final_url or url,
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
            source_name = clean_text(entry.source.get("title", ""))

        raw_link = getattr(entry, "link", "")
        resolved_link = resolve_final_url(raw_link)

        entry_title = clean_text(getattr(entry, "title", ""))
        if entry_title.strip().lower() in ["google news", "news.google.com", "untitled", ""]:
            entry_title = source_name or extract_domain_name(resolved_link or raw_link) or "Related source"

        if not source_name:
            source_name = extract_domain_name(resolved_link or raw_link) or "Unknown"

        if source_name.lower() in ["google news", "news.google.com", ""]:
            source_name = extract_domain_name(resolved_link or raw_link) or "Unknown"

        results.append(
            {
                "title": entry_title,
                "url": resolved_link or raw_link,
                "source": source_name,
                "published": getattr(entry, "published", "Not available"),
                "summary": clean_text(getattr(entry, "summary", "")),
            }
        )
    return results


def fetch_related_articles(query: str, original_url: str = "", max_results: int = 4) -> list:
    items = search_related_articles(query, max_results=max_results + 6)
    enriched = []

    normalized_original = resolve_final_url(original_url) if original_url else ""

    for item in items:
        link = (item.get("url") or "").strip()
        if not link:
            continue

        final_link = resolve_final_url(link)

        if normalized_original and final_link == normalized_original:
            continue

        source_name = (item.get("source") or "").strip()
        title = (item.get("title") or "").strip()
        published = item.get("published", "Not available")

        if source_name.lower() in ["google news", "news.google.com", "unknown", ""]:
            source_name = extract_domain_name(final_link) or "Unknown"

        if title.lower() in ["google news", "news.google.com", "untitled", ""]:
            title = source_name or extract_domain_name(final_link) or "Related source"

        article_text = ""
        try:
            article = fetch_article_from_url(final_link)
            if not article.get("error"):
                article_text = article.get("text", "")
                source_name = article.get("source", "") or source_name
                title = article.get("title", "") or title
        except Exception:
            pass

        if source_name.lower() in ["google news", "news.google.com", ""]:
            source_name = extract_domain_name(final_link) or "Unknown"

        enriched.append(
            {
                "title": title,
                "url": final_link,
                "source": source_name,
                "text": article_text,
                "published": published,
            }
        )

        if len(enriched) >= max_results:
            break

    return enriched
