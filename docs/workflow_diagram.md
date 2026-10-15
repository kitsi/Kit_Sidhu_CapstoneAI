# Technical Workflow Diagram

The diagram follows the real code: each box names the module that does the work. `pipeline.py` runs the steps in order and returns one report to `app.py`.

![Workflow diagram](workflow_diagram.png)

The PNG above is exported from the Mermaid code below, which GitHub also renders directly.

```mermaid
flowchart TD
    A["app.py: user pastes subject, body, optional link, or loads an example"] --> B{"validate_input: validation.py"}
    B -- "empty, over 10,000 chars, or not a link" --> B1["app.py: friendly error message"]
    B -- valid --> C["Strip HTML; collect body links as text, never opened"]

    subgraph P["pipeline.analyze: pipeline.py"]
        D1["Classifier: DistilBERT on subject + body, classifier.py"]
        D2["Rule indicators: 5 categories, rules.py"]
        D3["URL text checks: 6 checks, no network, url_checks.py"]
        X["AnalysisError: clear message, no risk level"]
        E["Risk score: 0.6 classifier + 0.4 indicators, Low / Medium / High + reasons, scoring.py"]
        F["Prompt: risk level, reasons, phrases; email excerpt in email tags as untrusted data, prompts.py"]
        G[["LangChain chain: ChatOllama, llama3.2:3b on this computer, explainer.py"]]
        H{"Structured output valid and passes safety post-check?"}
        I["AI explanation: summary, evidence, actions, limitations"]
        I2["Template explanation built from the same evidence"]
    end

    C --> D1
    C --> D2
    C --> D3
    D1 -- "model fails" --> X
    D1 --> E
    D2 --> E
    D3 --> E
    E --> F --> G --> H
    H -- yes --> I
    H -- "no, or Ollama down" --> I2
    I --> J["app.py: report with risk level as text + icon, reasons, phrases by category, link warnings, explanation, actions, disclaimer"]
    I2 --> J
```

## What happens at each step

| Step | Module | Notes |
|---|---|---|
| Input | `app.py` | Streamlit form; a sidebar loads 3 example emails. All email and AI text is displayed with `st.text` (no HTML or Markdown). |
| Validate | `validation.py` | Rejects bad input with a user-readable message; strips HTML; extracts links as text. |
| Classify | `classifier.py` | Pre-trained model loaded once; phishing probability = `LABEL_1` score; flags input over 512 tokens. If it fails, the run stops with a clear message. |
| Rules | `rules.py` | Case-insensitive patterns with word boundaries; returns category, phrase, and position. |
| URL checks | `url_checks.py` | `urlsplit` only: no HTTPS, raw IP, punycode, `@` trick, shorteners, more than 1 subdomain. |
| Score | `scoring.py` | Pure function; the only place a risk level is created. Credential request + any link warning ⇒ at least Medium. |
| Prompt | `prompts.py` | System rules + evidence; email excerpt (max 1,500 characters) fenced in `<email>` tags. |
| Explain | `explainer.py` | `ChatPromptTemplate` → `ChatOllama` → Pydantic structured output → safety post-check; any failure → template fallback. Never raises. |
| Display | `app.py` | Shows `report.assessment.level` from scoring, never anything the LLM wrote about the level. |

**Data storage:** none. There's no database or vector store; the email exists only in memory for the current browser session, and logs contain only stage timings and error types.
