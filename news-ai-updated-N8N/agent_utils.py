import json
from llm_utils import call_llm_json, call_llm_text
from credibility_tools import build_credibility_report


def analyze_news_article(article_text, article_title, article_url, output_language="Arabic"):
    """Analyze one news article and extract a structured representation that will drive summary, comparison, and export."""
    system_prompt = """
You are an expert news analysis assistant.
Use only the supplied article text.
Do not invent facts.
Return valid JSON only.
"""

    user_prompt = f"""
Output language: {output_language}

Article URL:
{article_url}

Article title:
{article_title}

Article text:
{article_text}

Return JSON with exactly these keys:
{{
  "title": "",
  "summary": "",
  "key_points": [],
  "main_events": [],
  "people": [],
  "organizations": [],
  "countries": [],
  "topic": "",
  "tone": "",
  "keywords": [],
  "suggested_search_query": ""
}}
"""

    return call_llm_json(system_prompt, user_prompt)



def compare_news_coverage(primary_analysis, related_analyses, output_language="Arabic"):
    """Compare the original article with searched related articles and return explicit similarities and differences as JSON."""
    system_prompt = """
You are a professional media comparison assistant.
Compare multiple reports covering the same news event.
Only use the supplied analyses.
Return valid JSON only.
"""

    payload = {
        "primary": primary_analysis,
        "related_sources": related_analyses
    }

    user_prompt = f"""
Output language: {output_language}

News analyses:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Return JSON with exactly these keys:
{{
  "similarities": [],
  "differences": [],
  "coverage_gaps": [],
  "comparison_summary": ""
}}
"""

    return call_llm_json(system_prompt, user_prompt, temperature=0.2)



def build_export_posts(analysis, comparison_summary, output_language="Arabic"):
    """Generate concise platform-ready drafts for Telegram and LinkedIn using the analyzed article plus comparison context."""
    system_prompt = """
You are a media content assistant.
Create platform-ready post drafts.
Return valid JSON only.
"""

    user_prompt = f"""
Output language: {output_language}

Main analysis:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

Comparison summary:
{json.dumps(comparison_summary, ensure_ascii=False, indent=2)}

Return JSON with exactly these keys:
{{
  "telegram_post": "",
  "linkedin_post": ""
}}
"""

    return call_llm_json(system_prompt, user_prompt, temperature=0.3)



def build_related_sources_view(related_articles, related_analyses):
    """Merge article metadata with analysis output to produce a simple list ready for display in the interface."""
    rows = []
    for article, analysis in zip(related_articles, related_analyses):
        rows.append({
            "source": article.get("source", "Unknown"),
            "title": analysis.get("title", article.get("title", "")),
            "url": article.get("url", ""),
            "summary": analysis.get("summary", "")
        })
    return rows



def evaluate_credibility(article_url, related_analyses, comparison_summary):
    """Create a credibility report that explains the method, references, and score derived from the cross-source comparison."""
    return build_credibility_report(article_url, len(related_analyses), comparison_summary)



def explain_search_strategy(primary_analysis, output_language="Arabic"):
    """Explain in natural language how the agent searched for related sources so the workflow remains transparent to the user."""
    system_prompt = """
You are an assistant that explains agent workflows clearly and briefly.
Write plain text only.
"""

    user_prompt = f"""
Output language: {output_language}

Primary analysis:
{json.dumps(primary_analysis, ensure_ascii=False, indent=2)}

Explain in 4 short bullet points:
1. How the search query was selected
2. How related sources were found
3. How similarities and differences were detected
4. Why this improves verification transparency
"""

    return call_llm_text(system_prompt, user_prompt, temperature=0.2)
