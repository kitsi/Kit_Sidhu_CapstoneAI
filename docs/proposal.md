# Project Proposal: Explainable AI Phishing Analysis Assistant

**Course:** CAP 942 – Capstone Project: AI Application Development
**Author:** Kit Sidhu

## Problem statement

Phishing is still one of the most common ways attackers get into organizations. Spam filters and blocklists stop known bad senders and links, but well-written social-engineering emails still reach inboxes, and then the decision falls to a person. Most tools that help with that decision return a bare verdict ("suspicious" or "phishing") without saying why. Users either trust the verdict blindly or ignore it, and in both cases they learn nothing they can use on the next message.

## Why it matters

The tactics behind phishing repeat: false urgency, threats of losing access, requests for passwords, and pressure to pay. A person who learns to recognize those tactics is better protected against every future message, not just the one being checked. An explanation also lets people handle borderline cases, such as a real password-reset email they requested, using their own judgment instead of an unexplained score.

Intended users are non-technical employees and students who receive suspicious messages, security-awareness trainers who need concrete examples, and help-desk staff doing a quick first look before escalating. The tool is not meant to replace an email security gateway or a security team.

## How AI solves it

The application combines two kinds of AI with transparent rules, and gives each a job it's suited for:

1. **A pre-trained classifier scores the email.** A DistilBERT model trained specifically for phishing detection reads the subject and body and returns a phishing probability. It catches patterns that are hard to write as rules.
2. **Rules and URL checks find visible evidence.** Pattern checks flag phrases in five categories (urgency, threats, credential requests, payment requests, suspicious language), and URL text checks flag link tricks such as raw IP addresses or a hidden `@`. Links are analyzed as text and never opened.
3. **A fixed formula decides the risk level.** Scoring combines the classifier and the evidence into Low, Medium, or High, with every reason listed. The result is reproducible and can't be changed by text inside the email.
4. **An open-source generative LLM explains it.** Llama 3.2 (3B), running locally in Ollama, turns the risk level and evidence into a plain-language explanation with recommended next steps. It explains; it never decides. The email is passed to it as clearly marked untrusted data, and its answer is checked before display: if it calls an email safe or legitimate, or cites evidence that wasn't found, a template explanation is shown instead.

## Tools, frameworks, and model choices

| Choice | Reason |
|---|---|
| `cybersectony/phishing-email-detection-distilbert_v2.4.1` (Hugging Face) | Pre-trained for phishing email detection, small (about 67M parameters) and fast on a laptop CPU, Apache-2.0. No training or fine-tuning is needed, as the course requires. |
| `llama3.2:3b` via **Ollama** | Free, open-source, and runs locally on a 16 GB laptop, so no email content leaves the machine and no paid API is used. Good enough to explain evidence it's given. |
| **LangChain** (explanation step only) | Applies course material to the one part that is an LLM chain: prompt template → model → structured output validated with Pydantic. The deterministic steps stay plain Python. |
| **Streamlit** | A usable web interface with little UI code, leaving time for the analysis logic. |
| **uv, pytest, ruff** | Reproducible setup with a lockfile, automated tests, and consistent code style. |
| **No database** | There's no retrieval or memory feature, and storing nothing is a privacy goal. |

## Workflow plan and expected user interaction

1. The user opens the app in a browser on their own computer, pastes an email's subject, body, and (optionally) a link, and clicks **Analyze**. They can also load one of three example emails from the sidebar.
2. The app validates the input and gives a friendly message for problems such as an empty body or a "link" that isn't a web address.
3. The classifier, rule checks, and URL checks run, and scoring produces the risk level and reasons.
4. The local LLM writes the explanation while a spinner shows progress.
5. The report shows the risk level as text and an icon, the reasons, the exact phrases found (grouped by category), any link warnings, the explanation and recommended actions, and a disclaimer that the tool can't guarantee an email is safe.

The user leaves with a decision for this email and with the tactics named, so they can recognize them next time.
