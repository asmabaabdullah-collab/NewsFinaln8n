import json

from llm_utils import call_llm_json
from news_tools import (
    fetch_article_text,
    fetch_related_articles,
)


def analyze_news_article(url, output_language="Arabic", fetch_related=True):
    """
    Extract a news article, analyze it, and optionally fetch related coverage.
    Returns:
    {
        "error": None or str,
        "article": {...},
        "analysis": {...},
        "related_articles": [...]
    }
    """
    try:
        article = fetch_article_text(url)
    except Exception as e:
        return {"error": str(e)}

    system_prompt = """
You are a professional digital media analyst.
Analyze the provided news article and return valid JSON only.
"""

    user_prompt = f"""
Output language: {output_language}

Article:
{json.dumps(article, ensure_ascii=False, indent=2)}

Return JSON with exactly this structure:
{{
  "summary": "Detailed but concise summary of the article",
  "key_points": ["point 1", "point 2", "point 3"],
  "main_events": ["event 1", "event 2"],
  "people": ["person 1", "person 2"],
  "organizations": ["org 1", "org 2"],
  "locations": ["location 1", "location 2"],
  "search_query": "short search query to find related coverage"
}}
"""

    analysis = call_llm_json(system_prompt, user_prompt, temperature=0.2)

    if not isinstance(analysis, dict):
        analysis = {}

    analysis.setdefault("summary", "")
    analysis.setdefault("key_points", [])
    analysis.setdefault("main_events", [])
    analysis.setdefault("people", [])
    analysis.setdefault("organizations", [])
    analysis.setdefault("locations", [])
    analysis.setdefault("search_query", article.get("title", ""))

    related_articles = []
    if fetch_related:
        query = analysis.get("search_query") or article.get("title", "")
        try:
            related_articles = fetch_related_articles(
                query=query,
                original_url=url,
                max_results=6,
                language_code="en",
                country_code="US",
            )
        except Exception:
            related_articles = []

    return {
        "error": None,
        "article": article,
        "analysis": analysis,
        "related_articles": related_articles,
    }


def compare_news_coverage(main_analysis, related_analyses, output_language="Arabic"):
    """
    Compare the main article analysis against related coverage.
    This is used internally to improve Telegram export quality.
    """
    if not related_analyses:
        return {
            "similarities": [],
            "differences": [],
            "coverage_gaps": [],
            "comparison_summary": "",
        }

    related_only_analyses = []
    for item in related_analyses:
        if isinstance(item, dict):
            related_only_analyses.append(item.get("analysis", item))
        else:
            related_only_analyses.append(item)

    system_prompt = """
You are a news comparison analyst.
Compare the main article analysis with the related coverage analyses.
Return valid JSON only.
"""

    user_prompt = f"""
Output language: {output_language}

Main analysis:
{json.dumps(main_analysis, ensure_ascii=False, indent=2)}

Related analyses:
{json.dumps(related_only_analyses, ensure_ascii=False, indent=2)}

Return JSON with exactly this structure:
{{
  "similarities": ["similarity 1", "similarity 2"],
  "differences": ["difference 1", "difference 2"],
  "coverage_gaps": ["gap 1", "gap 2"],
  "comparison_summary": "overall comparison summary"
}}
"""

    result = call_llm_json(system_prompt, user_prompt, temperature=0.2)

    if not isinstance(result, dict):
        result = {}

    result.setdefault("similarities", [])
    result.setdefault("differences", [])
    result.setdefault("coverage_gaps", [])
    result.setdefault("comparison_summary", "")

    return result


def build_export_posts(analysis, comparison_summary, output_language="Arabic"):
    """
    Generate Telegram-ready summaries in Arabic and English only.
    """
    system_prompt = """
You are a professional media content editor.
Create Telegram-ready summaries only.
Return valid JSON only.
"""

    user_prompt = f"""
Output language: {output_language}

Main analysis:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

Comparison summary:
{json.dumps(comparison_summary, ensure_ascii=False, indent=2)}

Create:
1. An Arabic Telegram summary in formal, accurate, natural Arabic
2. An English Telegram summary in professional, accurate English

Rules:
- concise but informative
- suitable for Telegram
- professional and clear
- no exaggeration
- based only on supplied content
- do not invent facts

Return JSON with exactly these keys:
{{
  "telegram_post_ar": "",
  "telegram_post_en": ""
}}
"""

    result = call_llm_json(system_prompt, user_prompt, temperature=0.3)

    if not isinstance(result, dict):
        result = {}

    result.setdefault("telegram_post_ar", "")
    result.setdefault("telegram_post_en", "")

    return result


def build_related_sources_view(related_articles):
    """
    Prepare related sources for display in the Related Sources Found tab.
    """
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
