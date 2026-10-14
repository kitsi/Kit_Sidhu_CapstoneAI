# Project: Explainable AI Phishing Analysis Assistant (CAP 942 capstone)

Full plan: implementation_plan.md. Build one milestone at a time.

## Stack

- Python 3.12, managed with uv (use `uv add`, `uv run`; never pip)
- Streamlit UI in app.py; logic in src/phish_assistant/
- Classifier: cybersectony/phishing-email-detection-distilbert_v2.4.1 (pre-trained, no training)
- LLM: llama3.2:3b via the ollama Python client

## Hard rules

- Never fetch, open, or resolve URLs. URL analysis is string parsing only.
- The risk level comes from scoring.py. The LLM only explains; it never sets the risk level.
- Escape all email text before rendering HTML in Streamlit.
- Never log or store email content.
- No paid APIs, no model training or fine-tuning.
- Keep Streamlit code out of src/ so modules are testable without the UI.

## Workflow

- Before writing code, state your plan in 2–3 bullets, then proceed (unless I used /plan).
- Add pytest tests with each module; run `uv run pytest` before saying a step is done.
- Only commit when I ask, using the commit subject I give you.
- Keep functions small, with docstrings and type hints.
