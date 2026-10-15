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

## How classifier.py works

- Loads the pre-trained DistilBERT model once, on first use, and reuses it; a clear error explains how to fix a failed load.
- Scores subject + body together; "phishing probability" is the LABEL_1 score, the label that tracked phishing on email text in exploration.
- Flags when an email exceeds the model's 512-token limit so the UI can say only the beginning was analyzed. URLs are never sent to the model, since it scored every URL the same.

## How validation.py works

- Acts as the boundary for untrusted input: trims whitespace and rejects empty, oversized, or non-URL input with plain-English `ValueError` messages the UI can show directly.
- Strips HTML with Python's built-in parser, dropping script/style contents but keeping the targets of hidden `<a href>` links, where phishing links usually hide.
- Finds `http(s)://` and `www.` links in the body as plain text only; nothing is ever opened or resolved.
