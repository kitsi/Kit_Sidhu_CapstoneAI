# Technical Workflow Diagram

The diagram follows the real code: each box names the module that does the work. `pipeline.py` runs the steps in order and returns one report to `app.py`.

![Workflow diagram](workflow_diagram.png)

TODO (Kit): export the diagram below at [mermaid.live](https://mermaid.live) (paste the code, then Actions → PNG) and save it as `docs/workflow_diagram.png`. GitHub also renders the Mermaid code below directly.

```mermaid
flowchart TD
    subgraph UI["Streamlit UI: app.py"]
        A["User pastes subject, body, optional link, or loads an example"]
        J["Report: risk level as text + icon, reasons, phrases by category, link warnings, explanation, actions, disclaimer"]
    end

    A --> B{"validate_input: validation.py"}
    B -- "empty, over 10,000 chars, or not a link" --> B1["Friendly error message"]
    B -- valid --> C["Strip HTML; collect body links as text, never opened"]

    subgraph P["pipeline.analyze: pipeline.py"]
        C --> D1["Classifier: DistilBERT on subject + body, classifier.py"]
        C --> D2["Rule indicators: 5 categories, rules.py"]
        C --> D3["URL text checks: 6 checks, no network, url_checks.py"]
        D1 -- "model fails" --> X["Clear error: no risk level"]
        D1 --> E["Risk score: 0.6 classifier + 0.4 indicators, Low / Medium / High + reasons, scoring.py"]
        D2 --> E
        D3 --> E
        E --> F["Prompt: risk level, reasons, phrases; email excerpt in email tags as untrusted data, prompts.py"]
        F --> G[["LangChain chain: ChatOllama, llama3.2:3b on this computer, explainer.py"]]
        G --> H{"Structured output valid and passes safety post-check?"}
        H -- yes --> I["AI explanation: summary, evidence, actions, limitations"]
        H -- "no, or Ollama down" --> I2["Template explanation built from the same evidence"]
    end

    I --> J
    I2 --> J
    B1 --> A
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
