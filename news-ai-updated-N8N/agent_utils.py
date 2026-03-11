import json
from urllib.parse import urlparse

from llm_utils import call_llm_json
from news_tools import (
    fetch_article_from_url,
    build_article_from_text,
    fetch_related_articles,
)


def analyze_news_input(
    input_mode: str,
    article_url: str = "",
    article_title: str = "",
    article_text: str = "",
    related_limit: int = 4,
):
    try:
        if input_mode == "News URL":
            article = fetch_article_from_url(article_url)
            original_url = article_url
        else:
            article = build_article_from_text(article_title, article_text)
            original_url = ""

        if article.get("error"):
            return {"error": article["error"]}

        analysis = analyze_article_content(article)

        search_query = analysis.get("search_query") or article.get("title", "")
        related_articles = fetch_related_articles(
            query=search_query,
            original_url=original_url,
            max_results=related_limit,
        )

        return {
            "error": None,
            "article": article,
            "analysis": analysis,
            "related_articles": related_articles,
        }
    except Exception as e:
        return {"error": str(e)}


def analyze_article_content(article: dict) -> dict:
    system_prompt = """
You are a senior bilingual news editor and professional translator.
Your task is to analyze and rewrite news content in high-quality Arabic and English.

Rules:
- Write fluent, professional, publication-quality Arabic.
- Use formal Modern Standard Arabic suitable for journalism.
- Do not translate literally when a more natural phrasing is better.
- Preserve the exact meaning, tone, and factual accuracy.
- Avoid awkward wording, repetition, and machine-like phrasing.
- Make Arabic titles concise, natural, and news-style.
- Make Arabic summaries smooth, readable, and coherent.
- Return valid JSON only.
"""

    user_prompt = f"""
Article:
{json.dumps(article, ensure_ascii=False, indent=2)}

Return JSON with exactly this structure:
{{
  "title_ar": "A fluent, natural Arabic news headline",
  "title_en": "An accurate English news headline",
  "summary_ar": "A polished Arabic summary written in professional journalistic Arabic",
  "summary_en": "A polished English summary",
  "key_points_ar": ["نقطة عربية واضحة 1", "نقطة عربية واضحة 2", "نقطة عربية واضحة 3"],
  "key_points_en": ["Clear English point 1", "Clear English point 2", "Clear English point 3"],
  "search_query": "short search query to find related coverage"
}}

Additional instructions:
- Arabic output must read as if written by a professional Arabic news editor.
- Prefer elegant Arabic phrasing over literal translation.
- Keep names and entities accurate.
- Keep the summary concise but complete.
- Do not add facts that are not present in the article.
"""

    result = call_llm_json(system_prompt, user_prompt, temperature=0.1)

    if not isinstance(result, dict):
        result = {}

    result.setdefault("title_ar", "")
    result.setdefault("title_en", article.get("title", ""))
    result.setdefault("summary_ar", "")
    result.setdefault("summary_en", "")
    result.setdefault("key_points_ar", [])
    result.setdefault("key_points_en", [])
    result.setdefault("search_query", article.get("title", ""))

    return result


def build_export_posts(analysis: dict, related_articles: list) -> dict:
    system_prompt = """
You are a senior media editor specialized in Arabic and English news publishing.
Create Telegram-ready titles and summaries in excellent Arabic and English.

Rules:
- Arabic must be elegant, clear, professional, and natural.
- Use refined Modern Standard Arabic suitable for digital news platforms.
- Avoid literal translation and awkward structures.
- English must also be concise and professional.
- Titles should be strong, short, and news-style.
- Summaries should be readable and polished.
- Hashtags should be relevant and not excessive.
- Return valid JSON only.
"""

    user_prompt = f"""
Main analysis:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

Related sources:
{json.dumps(related_articles[:4], ensure_ascii=False, indent=2)}

Create:
1. Arabic news title suitable for Telegram
2. Arabic summary suitable for Telegram
3. Arabic hashtags
4. English news title suitable for Telegram
5. English summary suitable for Telegram
6. English hashtags

Return JSON with exactly this structure:
{{
  "telegram_title_ar": "",
  "telegram_post_ar": "",
  "telegram_hashtags_ar": "",
  "telegram_title_en": "",
  "telegram_post_en": "",
  "telegram_hashtags_en": ""
}}
"""

    result = call_llm_json(system_prompt, user_prompt, temperature=0.2)

    if not isinstance(result, dict):
        result = {}

    result.setdefault("telegram_title_ar", analysis.get("title_ar", ""))
    result.setdefault("telegram_post_ar", analysis.get("summary_ar", ""))
    result.setdefault("telegram_hashtags_ar", "#ملخص_إخباري #أخبار")
    result.setdefault("telegram_title_en", analysis.get("title_en", ""))
    result.setdefault("telegram_post_en", analysis.get("summary_en", ""))
    result.setdefault("telegram_hashtags_en", "#NewsSummary #News")

    return result


def extract_site_name(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "").strip().lower()
    except Exception:
        return ""


def build_related_sources_view(related_articles: list) -> list:
    view = []

    for item in related_articles:
        url = (item.get("url") or "").strip()
        published = item.get("published", "Not available")
        source_name = (item.get("source") or "").strip()

        domain = extract_site_name(url)

        if not source_name or source_name.lower() in ["google news", "news.google.com", "unknown"]:
            source_name = domain or "Unknown"

        if source_name.lower() in ["google news", "news.google.com"]:
            continue

        view.append(
            {
                "source": source_name,
                "published": published,
                "url": url,
            }
        )

    return view
