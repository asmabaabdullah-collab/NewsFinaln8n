import json

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
You are a professional digital media analyst.
Analyze the provided news article and return valid JSON only.
"""

    user_prompt = f"""
Article:
{json.dumps(article, ensure_ascii=False, indent=2)}

Return JSON with exactly this structure:
{{
  "summary_ar": "Accurate Arabic summary in formal Arabic",
  "summary_en": "Accurate English summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "search_query": "short search query to find related coverage"
}}
"""

    result = call_llm_json(system_prompt, user_prompt, temperature=0.2)

    if not isinstance(result, dict):
        result = {}

    result.setdefault("summary_ar", "")
    result.setdefault("summary_en", "")
    result.setdefault("key_points", [])
    result.setdefault("search_query", article.get("title", ""))

    return result


def build_export_posts(analysis: dict, related_articles: list) -> dict:
    system_prompt = """
You are a professional media editor.
Create Telegram-ready titles and summaries in Arabic and English.
Return valid JSON only.
"""

    user_prompt = f"""
Main analysis:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

Related sources:
{json.dumps(related_articles[:4], ensure_ascii=False, indent=2)}

Create:
1. Arabic news title suitable for Telegram
2. Arabic summary suitable for Telegram
3. English news title suitable for Telegram
4. English summary suitable for Telegram

Rules:
- professional and accurate
- concise but informative
- no exaggeration
- based only on supplied content
- do not invent facts

Return JSON with exactly this structure:
{{
  "telegram_title_ar": "",
  "telegram_post_ar": "",
  "telegram_title_en": "",
  "telegram_post_en": ""
}}
"""

    result = call_llm_json(system_prompt, user_prompt, temperature=0.3)

    if not isinstance(result, dict):
        result = {}

    result.setdefault("telegram_title_ar", "")
    result.setdefault("telegram_post_ar", "")
    result.setdefault("telegram_title_en", "")
    result.setdefault("telegram_post_en", "")

    return result


def build_related_sources_view(related_articles: list) -> list:
    view = []
    for item in related_articles:
        text = item.get("text", "") or ""
        summary = text[:500] + ("..." if len(text) > 500 else "")
        view.append(
            {
                "title": item.get("title", "Untitled"),
                "source": item.get("source", "Unknown"),
                "url": item.get("url", ""),
                "summary": summary,
            }
        )
    return view
