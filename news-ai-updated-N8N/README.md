# Digital Media Assistant

A Streamlit-based AI news assistant that:
- reads a news article from a URL
- summarizes the article in Arabic or English
- extracts events, people, entities, and key points
- automatically searches for related coverage from other sources
- displays related sources found
- generates Telegram-ready summaries in Arabic and English
- can publish summaries to Telegram through n8n webhook integration

## Run

```bash
pip install -r requirements.txt
streamlit run app.py

## Secrets
Create `.streamlit/secrets.toml`:

## TOML
OPENAI_API_KEY="your_key_here"
OPENAI_MODEL="gpt-4o-mini"
N8N_TELEGRAM_WEBHOOK="https://asmastudent26.app.n8n.cloud/webhook/6b5c1116-2b0f-4822-b305-c760c4998f3e"
