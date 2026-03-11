import os
import requests
import streamlit as st

from agent_utils import (
    analyze_news_article,
    compare_news_coverage,
    build_export_posts,
    build_related_sources_view
)

st.set_page_config(page_title="Digital Media Assistant", layout="wide")

st.title("Digital Media Assistant")
st.caption(
    "Paste one news article URL. The agent will summarize it, find related coverage, "
    "and generate Telegram-ready summaries in Arabic and English."
)

if "main_analysis" not in st.session_state:
    st.session_state.main_analysis = None
if "related_analyses" not in st.session_state:
    st.session_state.related_analyses = []
if "comparison_summary" not in st.session_state:
    st.session_state.comparison_summary = None
if "export_posts" not in st.session_state:
    st.session_state.export_posts = None
if "related_view" not in st.session_state:
    st.session_state.related_view = None


def get_n8n_webhook():
    try:
        if "N8N_TELEGRAM_WEBHOOK" in st.secrets:
            return st.secrets["N8N_TELEGRAM_WEBHOOK"]
    except Exception:
        pass
    return os.getenv("N8N_TELEGRAM_WEBHOOK", "")


def post_to_n8n_telegram(message: str, language: str = "ar"):
    webhook_url = get_n8n_webhook()

    if not webhook_url:
        return {
            "success": False,
            "response_text": "N8N_TELEGRAM_WEBHOOK is missing."
        }

    payload = {
        "message": message,
        "language": language,
        "source": "digital_media_assistant"
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=25)
        return {
            "success": response.ok,
            "response_text": response.text
        }
    except Exception as e:
        return {
            "success": False,
            "response_text": str(e)
        }


with st.sidebar:
    st.header("Inputs")
    article_url = st.text_input("News article URL")
    output_language = st.selectbox("Summary language", ["Arabic", "English"], index=0)
    related_limit = st.slider("Number of related sources", min_value=2, max_value=8, value=4)

    run_btn = st.button("Analyze News", type="primary", use_container_width=True)


if run_btn:
    if not article_url.strip():
        st.error("Please enter a valid news article URL.")
    else:
        with st.spinner("Analyzing main article..."):
            main_result = analyze_news_article(article_url.strip(), output_language=output_language)

        if main_result.get("error"):
            st.error(main_result["error"])
        else:
            main_article = main_result.get("article", {})
            main_analysis = main_result.get("analysis", {})
            related_articles = main_result.get("related_articles", [])[:related_limit]

            related_analyses = []
            if related_articles:
                with st.spinner("Analyzing related coverage..."):
                    for item in related_articles:
                        url = item.get("url")
                        if not url:
                            continue
                        rel_result = analyze_news_article(url, output_language=output_language, fetch_related=False)
                        if not rel_result.get("error"):
                            related_analyses.append({
                                "article": rel_result.get("article", {}),
                                "analysis": rel_result.get("analysis", {})
                            })

            with st.spinner("Comparing news coverage..."):
                comparison_summary = compare_news_coverage(main_analysis, related_analyses, output_language=output_language)

            with st.spinner("Preparing Telegram summaries..."):
                export_posts = build_export_posts(main_analysis, comparison_summary, output_language=output_language)

            related_view = build_related_sources_view(related_articles)

            st.session_state.main_analysis = {
                "article": main_article,
                "analysis": main_analysis
            }
            st.session_state.related_analyses = related_analyses
            st.session_state.comparison_summary = comparison_summary
            st.session_state.export_posts = export_posts
            st.session_state.related_view = related_view


if st.session_state.main_analysis:
    tabs = st.tabs(["Summary", "Related Sources Found", "Telegram"])

    with tabs[0]:
        article = st.session_state.main_analysis["article"]
        analysis = st.session_state.main_analysis["analysis"]

        st.subheader(article.get("title", "Untitled"))
        if article.get("source"):
            st.caption(f"Source: {article.get('source')}")

        st.markdown("### Detailed Summary")
        st.write(analysis.get("summary", ""))

        st.markdown("### Key Points")
        for point in analysis.get("key_points", []):
            st.markdown(f"- {point}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Main Events")
            for item in analysis.get("main_events", []):
                st.markdown(f"- {item}")

            st.markdown("### Prominent People")
            for item in analysis.get("people", []):
                st.markdown(f"- {item}")

        with col2:
            st.markdown("### Organizations")
            for item in analysis.get("organizations", []):
                st.markdown(f"- {item}")

            st.markdown("### Locations")
            for item in analysis.get("locations", []):
                st.markdown(f"- {item}")

    with tabs[1]:
        st.subheader("Related Sources Found")

        if st.session_state.related_view:
            for item in st.session_state.related_view:
                with st.expander(item.get("title", "Related source")):
                    st.write(f"**Source:** {item.get('source', 'Unknown')}")
                    st.write(f"**URL:** {item.get('url', '')}")
                    st.write(item.get("summary", ""))
        else:
            st.info("No related sources were found.")

with tabs[2]:
    st.subheader("Telegram Summaries")
    posts = st.session_state.export_posts or {}

    telegram_title_ar = st.text_input(
        "عنوان الخبر بالعربية",
        value=posts.get("telegram_title_ar", ""),
        key="telegram_title_ar"
    )

    telegram_post_ar = st.text_area(
        "ملخص الخبر بالعربية (جاهز لتيليجرام)",
        posts.get("telegram_post_ar", ""),
        height=220,
        key="telegram_post_ar"
    )

    telegram_title_en = st.text_input(
        "News Title in English",
        value=posts.get("telegram_title_en", ""),
        key="telegram_title_en"
    )

    telegram_post_en = st.text_area(
        "News Summary in English (Telegram-ready)",
        posts.get("telegram_post_en", ""),
        height=220,
        key="telegram_post_en"
    )

    ar_message = f"{telegram_title_ar}\n\n{telegram_post_ar}".strip()
    en_message = f"{telegram_title_en}\n\n{telegram_post_en}".strip()

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "تحميل العربي",
            data=ar_message.encode("utf-8"),
            file_name="telegram_ar.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "Download English",
            data=en_message.encode("utf-8"),
            file_name="telegram_en.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("Publish to Telegram")

    post_col1, post_col2 = st.columns(2)

    with post_col1:
        if st.button("Post Arabic", use_container_width=True):
            if not telegram_title_ar.strip() and not telegram_post_ar.strip():
                st.error("Arabic title and summary are empty.")
            else:
                result = post_to_n8n_telegram(ar_message, language="ar")
                if result["success"]:
                    st.success("Arabic title and summary posted successfully.")
                else:
                    st.error(result["response_text"])

    with post_col2:
        if st.button("Post English", use_container_width=True):
            if not telegram_title_en.strip() and not telegram_post_en.strip():
                st.error("English title and summary are empty.")
            else:
                result = post_to_n8n_telegram(en_message, language="en")
                if result["success"]:
                    st.success("English title and summary posted successfully.")
                else:
                    st.error(result["response_text"])

        with post_col1:
            if st.button("Post Arabic Summary", use_container_width=True):
                if not telegram_post_ar.strip():
                    st.error("Arabic Telegram summary is empty.")
                else:
                    result = post_to_n8n_telegram(telegram_post_ar, language="ar")
                    if result["success"]:
                        st.success("Arabic summary posted successfully.")
                    else:
                        st.error(result["response_text"])

        with post_col2:
            if st.button("Post English Summary", use_container_width=True):
                if not telegram_post_en.strip():
                    st.error("English Telegram summary is empty.")
                else:
                    result = post_to_n8n_telegram(telegram_post_en, language="en")
                    if result["success"]:
                        st.success("English summary posted successfully.")
                    else:
                        st.error(result["response_text"])
