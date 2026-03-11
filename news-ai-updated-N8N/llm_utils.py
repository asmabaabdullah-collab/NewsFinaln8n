import os
import json
import re
from openai import OpenAI

DEFAULT_CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_client():
    """Create and return an OpenAI client using the API key from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing.")
    return OpenAI(api_key=api_key)


def extract_json_from_text(text: str):
    """Extract a valid JSON object or array from raw model output, even if wrapped in markdown fences."""
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    fenced = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", text, re.S)
    if fenced:
        return json.loads(fenced.group(1))

    raw = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if raw:
        return json.loads(raw.group(1))

    raise ValueError("Could not parse JSON from model response.")


def call_llm_text(system_prompt: str, user_prompt: str, model: str = None, temperature: float = 0.2):
    """Send a text generation request to the language model and return the plain text response."""
    client = get_client()
    model = model or DEFAULT_CHAT_MODEL

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response.choices[0].message.content.strip()


def call_llm_json(system_prompt: str, user_prompt: str, model: str = None, temperature: float = 0.1):
    """Send a prompt to the language model and parse the response into structured JSON."""
    text = call_llm_text(system_prompt, user_prompt, model=model, temperature=temperature)
    return extract_json_from_text(text)
