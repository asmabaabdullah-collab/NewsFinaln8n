import json
import os
import re

import streamlit as st
from openai import OpenAI


def get_openai_api_key() -> str:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "")


def get_model_name() -> str:
    try:
        if "OPENAI_MODEL" in st.secrets:
            return st.secrets["OPENAI_MODEL"]
    except Exception:
        pass
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_client() -> OpenAI:
    return OpenAI(api_key=get_openai_api_key())


def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
    client = get_client()
    model = get_model_name()

    response = client.responses.create(
        model=model,
        temperature=temperature,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.output_text.strip()
    raw = re.sub(r"^```json", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    try:
        return json.loads(raw)
    except Exception:
        return {}
