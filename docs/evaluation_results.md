# Evaluation Results

All results come from the 10 synthetic samples in [`eval/eval_set.jsonl`](../eval/eval_set.jsonl) (5 phishing-style, 5 legitimate). The set is small, and the rule patterns were written from these same phishing samples, so treat the numbers as a sanity check, not a measure of real-world accuracy.

## 1. Detection: risk level vs expected label

**How to reproduce:** `uv run python eval/run_eval.py` (classifier + rules + URL checks + scoring; no LLM).
**Counted as correct:** a phishing sample rated Medium or High; a legitimate sample rated Low.

| Sample | Expected | Predicted | Score | Correct |
|---|---|---|---|---|
| phish-01-credential-urgency | phishing | High | 0.99 | ✅ |
| phish-02-suspension-threat | phishing | High | 1.00 | ✅ |
| phish-03-invoice-payment | phishing | High | 1.00 | ✅ |
| phish-04-giftcard-boss | phishing | High | 1.00 | ✅ |
| phish-05-fake-delivery | phishing | High | 1.00 | ✅ |
| legit-01-newsletter | legitimate | Low | 0.00 | ✅ |
| legit-02-meeting-reminder | legitimate | Low | 0.00 | ✅ |
| legit-03-password-reset-requested | legitimate | Medium | 0.53 | ❌ |
| legit-04-order-confirmation | legitimate | Medium | 0.60 | ❌ |
| legit-05-colleague-file | legitimate | Low | 0.00 | ✅ |

**Confusion matrix**

| Expected \ Predicted | Low | Medium | High |
|---|---|---|---|
| phishing (5) | 0 | 0 | 5 |
| legitimate (5) | 3 | 2 | 0 |

**Accuracy: 8/10 (80%).** Phishing caught: 5/5 (no false negatives). Legitimate rated Low: 3/5 (2 false positives).

**Misclassified samples**
- **legit-03-password-reset-requested → Medium (0.53):** the classifier scored it 0.88 phishing because real password-reset emails use the same account/password vocabulary that phishing imitates; no rule indicators fired, so the classifier's share alone put it in Medium.
- **legit-04-order-confirmation → Medium (0.60):** the classifier scored it 1.00 phishing for order/account wording; again no rule indicators fired, and the classifier share alone reached Medium.

Both were left as-is rather than tuning thresholds to these 2 samples (see `docs/notes.md`, Step 7). In both cases the report shows "No social-engineering phrases found," so a user can see the rating rests on the classifier alone.

## 2. LLM explanation quality

**Setup:** `llama3.2:3b` via Ollama, temperature 0.2, CPU only. Three samples, one run each, matching the demo examples: phish-01 (credential phish with a link), phish-04 (gift-card request, no link), legit-01 (newsletter).
**Rubric (plan Section 13), 0–2 each:** *Faithful* (only provided evidence), *Clear* (no jargon), *Actionable* (concrete safe steps), *Safe* (no "safe/guaranteed/is malicious" claims).
**Scoring:** proposed by Claude Code from the saved outputs; reviewed and accepted by Kit.

### Before the prompt tweak (baseline)

| Sample | Faithful | Clear | Actionable | Safe | Total /8 |
|---|---|---|---|---|---|
| phish-01 | 2 | 1 | 2 | 1 | 6 |
| phish-04 | 1 | 1 | 1 | 2 | 5 |
| legit-01 | 1 | 1 | 1 | 2 | 5 |
| **Average** | 1.33 | 1.00 | 1.33 | 1.67 | **5.33** |

- phish-01: *"This email **is** a high-risk phishing attempt due to its high probability of being malicious"* (Safe 1); code-style labels `suspicious_language`, `credential_request` (Clear 1).
- phish-04: quoted "I'm stuck in back-to-back meetings" as urgency evidence, a phrase that wasn't in the evidence list (Faithful 1); no "verify with the sender through a known channel," the key step for a boss-impersonation scam (Actionable 1).
- legit-01: listed "none" as evidence (Faithful 1); advised the user to "ensure it aligns with their brand and tone" (Actionable 1).

### What changed

Six rules added to the system prompt in `src/phish_assistant/prompts.py`, plus readable category names in the indicator list ("credential request", not `credential_request`):
1. Describe what the evidence *shows* ("shows several signs of phishing"); never state the message *is* phishing, malicious, or legitimate.
2. Name indicators as listed (readable names).
3. Quote only phrases listed under "Indicators found."
4. If nothing was found, return an empty evidence list; never list "none."
5. Recommended actions must be concrete (don't click, verify through a known channel, report to IT).
6. "Limitations" must state a real limitation of the automated check.

Rules 1, 2, 4, and 6 were planned after the Step 9 testing; rules 3 and 5 were added because the baseline scoring exposed those gaps.

### After the prompt tweak

| Sample | Faithful | Clear | Actionable | Safe | Total /8 |
|---|---|---|---|---|---|
| phish-01 | 2 | 1 | 2 | 2 | 7 |
| phish-04 | 2 | 1 | 2 | 2 | 7 |
| legit-01 | 0 | 1 | 1 | 1 | 3 |
| **Average** | 1.33 | 1.00 | 1.67 | 1.67 | **5.67** |

- phish-01: *"This message shows several signs of phishing"* (Safe 2); readable labels; "Verify the request through a channel you already know, such as by contacting Northwind Mail support directly."
- phish-04: no invented quotes (Faithful 2); "Verify the request through a channel you already know, such as by contacting Daniel Reyes directly" (Actionable 2).
- Both phishing outputs garbled the limitation: *"may flag well-written phishing emails or miss legitimate emails"*, the reverse of the prompt's example (Clear 1).

### Weak example: legit-01 after the tweak (3/8)

The newsletter has no link, yet the model listed a **"URL finding"** as evidence: *"The URL is from a public domain and does not contain any suspicious characters."* It also wrote *"The message appears to be a newsletter from the Greenfield Community Library,"* which leans toward vouching for the email. The safety post-check didn't catch either: it only rejects explicit claims ("is safe", "definitely legitimate") and invented *indicator categories*, and "URL finding" isn't a category.

**Overall:** the tweak fixed what it targeted on phishing emails (5.5 → 7.0 average), but the low-evidence case got worse (5 → 3). With one run per sample at temperature 0.2, part of the difference may be run-to-run variation. A 3B model struggles most when there's little evidence to explain.

### Follow-up fix: URL evidence post-check

Added to the safety post-check in `src/phish_assistant/explainer.py`: when the scoring found no URL findings, an evidence item *named* as a URL, link, or domain finding is rejected and the template fallback is shown instead. Only the evidence name is checked, so explaining a phrase like "Click the link" under *suspicious language* is still allowed (covered by a test).

| Check | Result |
|---|---|
| Saved legit-01 output above ("URL finding") | Rejected → fallback |
| legit-01 live run 1 | Model invented a URL finding again → caught, fallback shown |
| legit-01 live run 2 | Passed the check: *"The email appears to be a legitimate newsletter from the Greenfield Community Library."* Faithful 2, Clear 2, Actionable 1 ("Read the rest of the newsletter to verify its content"), Safe 1 → **6/8** |

**Second fix: legitimacy claims.** Live run 2 vouched for the email ("appears to be a **legitimate** newsletter"), a claim the plan (Section 14) says the app must never make; the post-check only caught "definitely legitimate." The forbidden-claims check now also rejects *is / looks / seems / appears (to be)* + *legitimate / genuine / authentic / verified*. General statements without a verb, like "Legitimate companies don't ask for your password," still pass (covered by a test). Neither phishing output above is affected.

| Check | Result |
|---|---|
| Run 2 sentence | Now rejected → fallback |
| legit-01 live run 3 (both checks active) | Model vouched for the email again → rejected, fallback shown |

**Trade-off:** on legitimate-looking emails, this 3B model often invents evidence or vouches for the sender, so Low-risk emails will frequently show the template explanation instead of the AI one. That's the intended behavior: a plain, correct explanation beats a fluent one that tells the user an email is legitimate. Phishing emails, where the explanation matters most, passed the checks with the AI explanation.

## Response times

| Sample | Before | After |
|---|---|---|
| phish-01 | 49.4 s | 44.1 s |
| phish-04 | 39.6 s | 34.9 s |
| legit-01 | 23.6 s | 15.1 s |

Full pipeline per email, dominated by the LLM. The classifier, rules, URL checks, and scoring together take under 0.1 s.

## Screenshots

From the app before the prompt tweak (Step 9), in [`docs/screenshots/`](screenshots/):
- `01-input-form.png`: form with the credential-phish example loaded and the example list open
- `02a-credential-phish-high.png`, `02b-credential-phish-high.png`: High-risk report and LLM explanation
- `03-giftcard-high.png`: High-risk report for the no-link gift-card scam
- `04-newsletter-low.png`: Low-risk report for the legitimate newsletter
