import os
import requests
import streamlit as st

from agent_utils import (
    analyze_news_input,
    build_export_posts,
    build_related_sources_view,
)

st.set_page_config(
    page_title="Digital Media Assistant",
    page_icon="📰",
    layout="wide",
)

st.title("📰 Digital Media Assistant")
st.caption(
    "How this agent works:\n"
    "1) Paste a news article URL from any news website\n"
    "2) Or paste a news title and article text\n"
    "3) The AI translates and summarizes the news in Arabic and English in the Summary tab\n"
    "4) The Related Sources tab shows where else the story appeared\n"
    "5) The Telegram tab prepares editable Arabic and English Telegram-ready content and lets you post through n8n"
)

if "result" not in st.session_state:
    st.session_state.result = None
if "related_view" not in st.session_state:
    st.session_state.related_view = []
if "telegram_posts" not in st.session_state:
    st.session_state.telegram_posts = {}


def get_n8n_webhook() -> str:
    try:
        if "N8N_TELEGRAM_WEBHOOK" in st.secrets:
            return st.secrets["N8N_TELEGRAM_WEBHOOK"]
    except Exception:
        pass
    return os.getenv("N8N_TELEGRAM_WEBHOOK", "")


def post_to_n8n_telegram(message: str, language: str = "ar") -> dict:
    webhook_url = get_n8n_webhook()
    if not webhook_url:
        return {
            "success": False,
            "response_text": "N8N_TELEGRAM_WEBHOOK is missing.",
        }

    payload = {
        "message": message,
        "language": language,
        "source": "digital_media_assistant",
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=25)
        return {
            "success": response.ok,
            "response_text": response.text,
        }
    except Exception as e:
        return {
            "success": False,
            "response_text": str(e),
        }


with st.sidebar:
    st.header("Input")

    input_mode = st.radio(
        "Choose input type",
        ["News URL", "News Title + Text"],
        horizontal=False,
    )

    article_url = ""
    article_title = ""
    article_text = ""

    if input_mode == "News URL":
        article_url = st.text_input("Paste news URL")
    else:
        article_title = st.text_input("Paste news title")
        article_text = st.text_area("Paste news text", height=240)

    related_limit = st.slider("Number of related sources", 2, 8, 4)

    run_btn = st.button("Analyze News", type="primary", use_container_width=True)


if run_btn:
    if input_mode == "News URL" and not article_url.strip():
        st.error("Please enter a valid news URL.")
    elif input_mode == "News Title + Text" and (not article_title.strip() or not article_text.strip()):
        st.error("Please paste both the news title and the news text.")
    else:
        with st.spinner("Analyzing news..."):
            result = analyze_news_input(
                input_mode=input_mode,
                article_url=article_url.strip(),
                article_title=article_title.strip(),
                article_text=article_text.strip(),
                related_limit=related_limit,
            )

        if result.get("error"):
            st.error(result["error"])
        else:
            st.session_state.result = result
            st.session_state.related_view = build_related_sources_view(
                result.get("related_articles", [])
            )
            st.session_state.telegram_posts = build_export_posts(
                result.get("analysis", {}),
                result.get("related_articles", []),
            )

if st.session_state.result:
    result = st.session_state.result
    analysis = result.get("analysis", {})
    article = result.get("article", {})
    posts = st.session_state.telegram_posts or {}

    tabs = st.tabs(["Summary", "Related Sources", "Telegram"])

    with tabs[0]:
        st.subheader("Summary")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Original Title")
            st.write(article.get("title", ""))

            st.markdown("### English Summary")
            st.write(analysis.get("summary_en", ""))

        with col2:
            st.markdown("### العنوان الأصلي")
            st.write(article.get("title", ""))

            st.markdown("### الملخص العربي")
            st.write(analysis.get("summary_ar", ""))

        st.markdown("### Key Points")
        key_points = analysis.get("key_points", [])
        if key_points:
            for point in key_points:
                st.markdown(f"- {point}")
        else:
            st.info("No key points available.")

    with tabs[1]:
        st.subheader("Related Sources")

        related_items = st.session_state.related_view
        if related_items:
            for item in related_items:
                with st.expander(item.get("title", "Related source")):
                    st.write(f"**Source:** {item.get('source', 'Unknown')}")
                    st.write(f"**URL:** {item.get('url', '')}")
                    st.write(item.get("summary", ""))
        else:
            st.info("No related sources found.")

    with tabs[2]:
        st.subheader("Telegram")

        telegram_title_ar = st.text_input(
            "عنوان الخبر بالعربية",
            value=posts.get("telegram_title_ar", ""),
            key="telegram_title_ar",
        )
        telegram_post_ar = st.text_area(
            "الملخص العربي",
            value=posts.get("telegram_post_ar", ""),
            height=180,
            key="telegram_post_ar",
        )

        telegram_title_en = st.text_input(
            "News Title in English",
            value=posts.get("telegram_title_en", ""),
            key="telegram_title_en",
        )
        telegram_post_en = st.text_area(
            "English Summary",
            value=posts.get("telegram_post_en", ""),
            height=180,
            key="telegram_post_en",
        )

        ar_message = f"{telegram_title_ar}\n\n{telegram_post_ar}".strip()
        en_message = f"{telegram_title_en}\n\n{telegram_post_en}".strip()

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Download Arabic",
                data=ar_message.encode("utf-8"),
                file_name="telegram_ar.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "Download English",
                data=en_message.encode("utf-8"),
                file_name="telegram_en.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.markdown("---")
        st.subheader("Publish to Telegram")

        p1, p2 = st.columns(2)
        with p1:
            if st.button("Post Arabic", use_container_width=True):
                if not ar_message.strip():
                    st.error("Arabic message is empty.")
                else:
                    result_post = post_to_n8n_telegram(ar_message, language="ar")
                    if result_post["success"]:
                        st.success("Arabic post sent successfully.")
                    else:
                        st.error(result_post["response_text"])

        with p2:
            if st.button("Post English", use_container_width=True):
                if not en_message.strip():
                    st.error("English message is empty.")
                else:
                    result_post = post_to_n8n_telegram(en_message, language="en")
                    if result_post["success"]:
                        st.success("English post sent successfully.")
                    else:
                        st.error(result_post["response_text"])
