# News AI Agent

A Streamlit-based AI news agent that:
- reads a news article from a URL
- summarizes the article in Arabic or English
- extracts events, people, entities, and key points
- automatically searches for related coverage from other sources
- displays similarities and differences across the coverage
- produces a transparent credibility report
- generates Telegram and LinkedIn post drafts

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secrets

Create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY="your_key_here"
OPENAI_MODEL="gpt-4o-mini"
```
