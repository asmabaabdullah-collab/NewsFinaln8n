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
    "4) The Related Sources tab shows the news website, publication date, and a visit button\n"
    "5) The Telegram tab prepares one editable post box containing Arabic title + Arabic summary + Arabic hashtags, followed by English title + English summary + English hashtags, with download and post controls"
)

if "result" not in st.session_state:
    st.session_state.result = None
if "related_view" not in st.session_state:
    st.session_state.related_view = []
if "telegram_posts" not in st.session_state:
    st.session_state.telegram_posts = {}
if "telegram_combined_text" not in st.session_state:
    st.session_state.telegram_combined_text = ""
if "telegram_post_generated" not in st.session_state:
    st.session_state.telegram_post_generated = False


def get_n8n_webhook() -> str:
    try:
        if "N8N_TELEGRAM_WEBHOOK" in st.secrets:
            return st.secrets["N8N_TELEGRAM_WEBHOOK"]
    except Exception:
        pass
    return os.getenv("N8N_TELEGRAM_WEBHOOK", "")


def post_to_n8n_telegram(message: str, language: str = "multi") -> dict:
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


def normalize_hashtags(text: str) -> str:
    if not text:
        return ""
    parts = []
    for item in text.replace("\n", " ").split():
        token = item.strip()
        if not token:
            continue
        if not token.startswith("#"):
            token = f"#{token}"
        parts.append(token)
    return " ".join(parts)


def build_combined_telegram_text(posts: dict) -> str:
    title_ar = (posts.get("telegram_title_ar") or "").strip()
    summary_ar = (posts.get("telegram_post_ar") or "").strip()
    hashtags_ar = normalize_hashtags(posts.get("telegram_hashtags_ar", ""))

    title_en = (posts.get("telegram_title_en") or "").strip()
    summary_en = (posts.get("telegram_post_en") or "").strip()
    hashtags_en = normalize_hashtags(posts.get("telegram_hashtags_en", ""))

    sections = []

    arabic_block = "\n".join(
        [part for part in [title_ar, "", summary_ar, "", hashtags_ar] if part != ""]
    ).strip()

    english_block = "\n".join(
        [part for part in [title_en, "", summary_en, "", hashtags_en] if part != ""]
    ).strip()

    if arabic_block:
        sections.append(arabic_block)

    if english_block:
        sections.append(english_block)

    return "\n\n" + "\n\n".join(sections).strip()


def hydrate_missing_hashtags(posts: dict) -> dict:
    if not isinstance(posts, dict):
        posts = {}

    posts.setdefault("telegram_title_ar", "")
    posts.setdefault("telegram_post_ar", "")
    posts.setdefault("telegram_title_en", "")
    posts.setdefault("telegram_post_en", "")
    posts.setdefault("telegram_hashtags_ar", "#ملخص_إخباري #أخبار")
    posts.setdefault("telegram_hashtags_en", "#NewsSummary #News")
    return posts


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
              result.get("related_sources", [])
           )
           

            raw_posts = build_export_posts(
                result.get("analysis", {}),
                result.get("related_articles", []),
            )
            posts = hydrate_missing_hashtags(raw_posts)

            st.session_state.telegram_posts = posts
            st.session_state.telegram_combined_text = build_combined_telegram_text(posts)
            st.session_state.telegram_post_generated = True


if st.session_state.result:
    result = st.session_state.result
    analysis = result.get("analysis", {})
    article = result.get("article", {})

    tabs = st.tabs(["Summary", "Related Sources", "Telegram"])

    with tabs[0]:
        st.subheader("Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### English Title")
            st.write(analysis.get("title_en", article.get("title", "")))

            st.markdown("### English Summary")
            st.write(analysis.get("summary_en", ""))

            st.markdown("### Key Points")
            key_points_en = analysis.get("key_points_en", [])
            if key_points_en:
                for point in key_points_en:
                    st.markdown(f"- {point}")
            else:
                st.info("No English key points available.")

        with col2:
            st.markdown("### العنوان بالعربية")
            st.write(analysis.get("title_ar", article.get("title", "")))

            st.markdown("### الملخص العربي")
            st.write(analysis.get("summary_ar", ""))

            st.markdown("### أبرز النقاط")
            key_points_ar = analysis.get("key_points_ar", [])
            if key_points_ar:
                for point in key_points_ar:
                    st.markdown(f"- {point}")
            else:
                st.info("لا توجد نقاط رئيسية بالعربية.")

    with tabs[1]:
        st.subheader("Related Sources")

        related_items = st.session_state.related_view
        if related_items:
            for idx, item in enumerate(related_items, start=1):
                with st.container(border=True):
                    st.markdown(f"### {idx}. {item.get('source', 'Unknown')}")
                    st.write(f"**Published:** {item.get('published', 'Not available')}")

                    if item.get("url"):
                        st.link_button("Visit Page", item.get("url"))
        else:
            st.info("No related sources found.")

    with tabs[2]:
        st.subheader("Telegram")

        combined_text = st.text_area(
            "Telegram post preview and editor",
            value=st.session_state.telegram_combined_text,
            height=360,
            key="telegram_combined_editor",
        )

        st.session_state.telegram_combined_text = combined_text

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            st.download_button(
                "Download Post",
                data=st.session_state.telegram_combined_text.encode("utf-8"),
                file_name="telegram_post.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with action_col2:
            if st.button("Post", use_container_width=True):
                if not st.session_state.telegram_combined_text.strip():
                    st.error("Telegram post is empty.")
                else:
                    result_post = post_to_n8n_telegram(
                        st.session_state.telegram_combined_text,
                        language="multi",
                    )
                    if result_post["success"]:
                        st.success("Telegram post sent successfully.")
                    else:
                        st.error(result_post["response_text"])

result_post = post_to_n8n_telegram("اختبار مباشر من التطبيق", language="multi")
