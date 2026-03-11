import os
import streamlit as st

from news_tools import fetch_article_text, clean_text, fetch_related_articles
from agent_utils import (
    analyze_news_article,
    compare_news_coverage,
    build_export_posts,
    build_related_sources_view,
    evaluate_credibility,
    explain_search_strategy
)

st.set_page_config(page_title="News AI Agent", layout="wide")

try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    if "OPENAI_MODEL" in st.secrets:
        os.environ["OPENAI_MODEL"] = st.secrets["OPENAI_MODEL"]
except Exception:
    pass

if "main_analysis" not in st.session_state:
    st.session_state.main_analysis = None
if "related_view" not in st.session_state:
    st.session_state.related_view = []
if "comparison_summary" not in st.session_state:
    st.session_state.comparison_summary = None
if "credibility" not in st.session_state:
    st.session_state.credibility = None
if "export_posts" not in st.session_state:
    st.session_state.export_posts = None
if "search_strategy_text" not in st.session_state:
    st.session_state.search_strategy_text = ""

st.sidebar.title("Agent Settings")

output_language = st.sidebar.selectbox("Output language", ["Arabic", "English"])
related_count = st.sidebar.slider("Number of related sources to search", min_value=1, max_value=5, value=3)

st.title("News AI Agent")
st.caption(
    "Paste one news article URL. The agent will summarize it, search for related coverage, "
    "show similarities and differences, assess credibility, and generate Telegram/LinkedIn drafts."
)

news_url = st.text_input("News URL", placeholder="Paste a news article URL here")
analyze_btn = st.button("Analyze News")

if analyze_btn:
    if not news_url.strip():
        st.error("Please enter a news URL.")
    else:
        try:
            with st.spinner("Fetching and reading the main article..."):
                main_article = fetch_article_text(news_url)
                main_article["text"] = clean_text(main_article["text"])

            with st.spinner("Analyzing the main article..."):
                main_analysis = analyze_news_article(
                    article_text=main_article["text"],
                    article_title=main_article["title"],
                    article_url=main_article["url"],
                    output_language=output_language
                )

            search_query = main_analysis.get("suggested_search_query") or main_analysis.get("title") or main_article["title"]
            search_lang = "ar" if output_language == "Arabic" else "en"
            search_country = "SA" if output_language == "Arabic" else "US"

            with st.spinner("Searching for related news sources automatically..."):
                related_articles = fetch_related_articles(
                    query=search_query,
                    original_url=main_article["url"],
                    max_results=related_count,
                    language_code=search_lang,
                    country_code=search_country
                )

            related_analyses = []
            for article in related_articles:
                try:
                    article["text"] = clean_text(article["text"])
                    related_analyses.append(
                        analyze_news_article(
                            article_text=article["text"],
                            article_title=article["title"],
                            article_url=article["url"],
                            output_language=output_language
                        )
                    )
                except Exception:
                    continue

            with st.spinner("Detecting similarities and differences across sources..."):
                comparison_summary = compare_news_coverage(
                    primary_analysis=main_analysis,
                    related_analyses=related_analyses,
                    output_language=output_language
                ) if related_analyses else {
                    "similarities": [],
                    "differences": [],
                    "coverage_gaps": [],
                    "comparison_summary": "No related sources were successfully analyzed."
                }

            with st.spinner("Preparing credibility report and export posts..."):
                credibility = evaluate_credibility(main_article["url"], related_analyses, comparison_summary)
                export_posts = build_export_posts(main_analysis, comparison_summary, output_language=output_language)
                search_strategy_text = explain_search_strategy(main_analysis, output_language=output_language)

            st.session_state.main_analysis = main_analysis
            st.session_state.related_view = build_related_sources_view(related_articles, related_analyses)
            st.session_state.comparison_summary = comparison_summary
            st.session_state.credibility = credibility
            st.session_state.export_posts = export_posts
            st.session_state.search_strategy_text = search_strategy_text

            st.success("News analyzed successfully.")

        except Exception as e:
            st.error(f"Error: {e}")

if st.session_state.main_analysis:
    tabs = st.tabs(["Summary", "Similarities & Differences", "Credibility", "Export"])

    with tabs[0]:
        st.subheader(st.session_state.main_analysis.get("title", "Article Title"))
        st.write(st.session_state.main_analysis.get("summary", ""))

        st.markdown("### Key Points")
        for point in st.session_state.main_analysis.get("key_points", []):
            st.markdown(f"- {point}")

        st.markdown("### Main Events")
        for item in st.session_state.main_analysis.get("main_events", []):
            st.markdown(f"- {item}")

        st.markdown("### People")
        people = st.session_state.main_analysis.get("people", [])
        st.write(", ".join(people) if people else "N/A")

        st.markdown("### Search Workflow")
        st.write(st.session_state.search_strategy_text)

    with tabs[1]:
        st.subheader("Similarities and Differences Found by the Agent")

        if st.session_state.related_view:
            st.markdown("### Related Sources Found")
            for item in st.session_state.related_view:
                with st.expander(item.get("title", "Related source")):
                    st.write(f"**Source:** {item.get('source', 'Unknown')}")
                    st.write(f"**URL:** {item.get('url', '')}")
                    st.write(item.get("summary", ""))

        summary = st.session_state.comparison_summary or {}

        st.markdown("### Similarities")
        similarities = summary.get("similarities", [])
        if similarities:
            for item in similarities:
                st.markdown(f"- {item}")
        else:
            st.info("No strong similarities were extracted.")

        st.markdown("### Differences")
        differences = summary.get("differences", [])
        if differences:
            for item in differences:
                st.markdown(f"- {item}")
        else:
            st.info("No major differences were extracted.")

        st.markdown("### Coverage Gaps")
        gaps = summary.get("coverage_gaps", [])
        if gaps:
            for item in gaps:
                st.markdown(f"- {item}")
        else:
            st.info("No coverage gaps were identified.")

        st.markdown("### Final Comparison Summary")
        st.write(summary.get("comparison_summary", ""))

    with tabs[2]:
        st.subheader("Credibility Check")
        credibility = st.session_state.credibility

        if credibility:
            st.metric("Credibility Score", f"{credibility['credibility_score']}/10")
            st.write(f"**Level:** {credibility['credibility_level']}")
            st.write(f"**Domain:** {credibility['domain']}")

            st.markdown("### Verification References")
            for item in credibility["references"]:
                st.markdown(f"- {item}")

            st.markdown("### Verification Method")
            for item in credibility["verification_method"]:
                st.markdown(f"- {item}")

            st.markdown("### Tools Used")
            for item in credibility["tools_used"]:
                st.markdown(f"- {item}")

            st.markdown("### Notes")
            for item in credibility["reasons"]:
                st.markdown(f"- {item}")

    with tabs[3]:
        st.subheader("Export-ready Posts")
        posts = st.session_state.export_posts

        if posts:
            st.markdown("### Telegram Post")
            st.text_area("telegram_post", posts.get("telegram_post", ""), height=180)

            st.markdown("### LinkedIn Post")
            st.text_area("linkedin_post", posts.get("linkedin_post", ""), height=250)
