# Data or Input Sources

The application has two kinds of input: **emails pasted by the user at run time**, and a **small evaluation set** used to test it. No dataset was used for training, because no model is trained or fine-tuned in this project.

## 1. User input (at run time)

- **What:** an email's subject, body, and an optional link, pasted into the Streamlit form.
- **Handling:** validated and cleaned in `src/phish_assistant/validation.py`: whitespace trimmed; empty, oversized (over 10,000 characters), or non-link input rejected with a friendly message; HTML tags stripped with Python's built-in parser (script and style contents dropped, link targets kept as text).
- **Privacy:** processed in memory on the user's computer only. It's never stored, never logged, and never sent to an external service. Links are analyzed as text and never opened.

## 2. Evaluation set: `eval/eval_set.jsonl`

| Property | Details |
|---|---|
| Size | 10 emails: 5 phishing-style, 5 legitimate |
| Source | Synthetic. Written for this project with AI assistance (Claude Code), then reviewed. Not taken from real mailboxes or public datasets. |
| Personal data | None. People's names are invented; companies are fictional (Northwind, Contoso, Fabrikam, Tailspin, Wingtip); link domains use the reserved `.example` top-level domain or private IP addresses, so no link points to a real site. |
| Format | One JSON object per line: `id`, `subject`, `body`, `url` (or `null`), `expected` (`"phishing"` or `"legitimate"`) |
| Labels | Assigned by design: each email was written to be phishing-style or legitimate, so the label is the intended class. |
| Preprocessing | None needed; the emails are plain text. At run time they go through the same validation as user input. |

**What the samples cover**

| Phishing-style | Legitimate |
|---|---|
| Credential harvest with urgency and a raw-IP link (`http://192.168.40.12/…`) | Library newsletter |
| Account-suspension threat with a many-subdomain link | Team meeting reminder |
| Overdue invoice asking for payment to a "new bank account," link with an `@` trick | Password reset the user requested |
| Gift-card request from a "boss," no link | Online order confirmation |
| Fake delivery fee with a URL-shortener link | Colleague asking for a spreadsheet |

The legitimate samples were chosen to include hard cases. The password reset and order confirmation use account and order vocabulary that phishing imitates; they're the two samples the classifier misreads (see `docs/evaluation_results.md`).

**Limitations.** Ten samples is small, and the rule patterns were written from the same phishing samples they're tested on, so results are a sanity check rather than a measure of real-world accuracy.

## 3. Pre-trained models (not data collected for this project)

- **Classifier:** [`cybersectony/phishing-email-detection-distilbert_v2.4.1`](https://huggingface.co/cybersectony/phishing-email-detection-distilbert_v2.4.1), fine-tuned by its author from `distilbert-base-uncased` on the `cybersectony/PhishingEmailDetectionv2.0` dataset (Apache-2.0). That dataset was **not** used here; the evaluation uses only the synthetic samples above, so results aren't inflated by testing on the model's own training data.
- **LLM:** `llama3.2:3b` by Meta, run locally through Ollama (Llama 3.2 Community License). Used through prompting only.
