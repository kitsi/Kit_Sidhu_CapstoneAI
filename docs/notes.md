# Build Notes

Running notes for the final documentation and the "Challenges & Lessons Learned" section.

## Step 4–5: Classifier

**Label mapping decision.** Scores sum to 1 (softmax, single-label). On email text, LABEL_0 tracks legitimate and LABEL_1 tracks phishing, so `phishing_probability` = LABEL_1 score. Every URL scored LABEL_3 = 1.0 and LABEL_2 never appeared, so the model can't separate good from bad links; URLs are not sent to the classifier and `url_checks.py` handles them instead.

**Where the model is wrong.** Two of five legitimate samples score as phishing:

| Sample | phishing_probability |
|---|---|
| legit-03-password-reset-requested | 0.875 |
| legit-04-order-confirmation | 1.000 |

Both use account/order language that phishing emails imitate. This is why the risk level can't come from the classifier alone: rule-based indicators and scoring (Step 7) need to balance it.

**Model decision: kept the classifier.** The plan names `ealvaradob/bert-finetuned-phishing` (BERT-large, ~336M parameters) as the alternative if the first model behaved poorly. I kept `cybersectony/phishing-email-detection-distilbert_v2.4.1` because:

- It caught all 5 phishing samples (probability ≥ 0.985), so it isn't missing attacks.
- Its weakness, false positives on legitimate account/order emails, is something the design already compensates for: the classifier is only 60% of the risk score, and the other 40% comes from rule indicators (urgency, threats, credential and payment requests). A legitimate email with none of those phrases can still land at Low.
- It's ~5× smaller than the alternative, runs in well under a second on CPU, and matches the original DistilBERT idea for the project.
- Switching would have cost ~30–45 minutes on a one-day schedule (download, re-explore, new label mapping) with no guarantee of better results on these samples.

### Presentation talking points

- **"Why not just trust the classifier?"** In testing it flagged 2 of 5 legitimate emails (a password reset I requested and an order confirmation) as phishing. Legitimate account emails use the same vocabulary phishing imitates. That's why the verdict combines the classifier with transparent rules instead of relying on one model.
- **"Why didn't you switch models?"** It caught every phishing sample, and its false positives are offset by scoring. A bigger model is slower and wouldn't remove the need for evidence-based rules.
- **"How did you pick the label mapping?"** I didn't trust the model card's label names. I ran 10 samples, checked that scores sum to 1 (softmax), and saw LABEL_1 tracks phishing on email text.
- **"Why aren't URLs sent to the classifier?"** Every URL I tested scored the same label at 1.0, so the model couldn't separate good links from bad. URL risk comes from string checks instead (raw IP, punycode, `@` trick, shorteners), which never visit the link.
- **Lesson learned:** measure a pre-trained model on your own samples before building on it. The model card reports ~99.6% accuracy on its own test data; on my samples it misread 40% of legitimate emails.

## How classifier.py works

- Loads the pre-trained DistilBERT model once, on first use, and reuses it; a clear error explains how to fix a failed load.
- Scores subject + body together; "phishing probability" is the LABEL_1 score, the label that tracked phishing on email text in exploration.
- Flags when an email exceeds the model's 512-token limit so the UI can say only the beginning was analyzed. URLs are never sent to the model, since it scored every URL the same.

## How validation.py works

- Acts as the boundary for untrusted input: trims whitespace and rejects empty, oversized, or non-URL input with plain-English `ValueError` messages the UI can show directly.
- Strips HTML with Python's built-in parser, dropping script/style contents but keeping the targets of hidden `<a href>` links, where phishing links usually hide.
- Finds `http(s)://` and `www.` links in the body as plain text only; nothing is ever opened or resolved.
