import requests
import feedparser
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import quote_plus

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def clean_text(text: str) -> str:
    """Normalize whitespace in extracted article text so the model receives cleaner, shorter context."""
    return " ".join((text or "").split())



def fetch_article_text(url: str):
    """Download a news webpage, extract the main readable content, and return title plus cleaned article text."""
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()

    html = response.text
    doc = Document(html)
    title = clean_text(doc.short_title())
    summary_html = doc.summary()

    soup = BeautifulSoup(summary_html, "html.parser")
    text = clean_text(soup.get_text(separator=" ", strip=True))

    if not text:
        full_soup = BeautifulSoup(html, "html.parser")
        text = clean_text(full_soup.get_text(separator=" ", strip=True))

    return {
        "url": url,
        "title": title,
        "text": text
    }



def build_google_news_rss_url(query: str, language_code: str = "en", country_code: str = "US"):
    """Build a Google News RSS search URL that can be used as a lightweight search tool for related coverage."""
    encoded = quote_plus(query)
    return (
        f"https://news.google.com/rss/search?q={encoded}"
        f"&hl={language_code}-{country_code}&gl={country_code}&ceid={country_code}:{language_code}"
    )



def search_related_news(query: str, max_results: int = 5, language_code: str = "en", country_code: str = "US"):
    """Search Google News RSS for articles related to the same topic and return candidate sources for comparison."""
    rss_url = build_google_news_rss_url(query, language_code=language_code, country_code=country_code)
    feed = feedparser.parse(rss_url)

    results = []
    for entry in feed.entries[: max_results * 3]:
        link = entry.get("link", "")
        title = clean_text(entry.get("title", ""))
        source = clean_text(entry.get("source", {}).get("title", "")) if entry.get("source") else ""
        published = entry.get("published", "")

        if link:
            results.append({
                "title": title,
                "url": link,
                "source": source,
                "published": published
            })

    unique = []
    seen = set()
    for item in results:
        key = item["url"]
        if key not in seen:
            seen.add(key)
            unique.append(item)
        if len(unique) >= max_results:
            break

    return unique



def fetch_related_articles(query: str, original_url: str, max_results: int = 3, language_code: str = "en", country_code: str = "US"):
    """Search for related news, exclude the original article, fetch readable text, and return usable articles for comparison."""
    search_results = search_related_news(
        query=query,
        max_results=max_results + 2,
        language_code=language_code,
        country_code=country_code
    )

    articles = []
    for item in search_results:
        if item["url"] == original_url:
            continue
        try:
            article = fetch_article_text(item["url"])
            article["source"] = item.get("source", "")
            article["published"] = item.get("published", "")
            articles.append(article)
        except Exception:
            continue

        if len(articles) >= max_results:
            break

    return articles
