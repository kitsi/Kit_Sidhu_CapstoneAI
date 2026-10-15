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

## Step 6: Rules and URL checks

**Results on the 10 eval samples.** Every phishing sample fired 3–4 indicator categories (phish-01 also had no-HTTPS + raw-IP URL findings; phish-02 subdomains; phish-03 the `@` trick; phish-05 a shortener). No legitimate sample fired any indicator or URL finding, including the password reset and order confirmation the classifier misread.

**Caveat (be upfront about this).** The patterns were written from these same 5 phishing samples, so a perfect result here is expected and overstates real-world performance. Rewording ("verify your login info") can evade them. New, unseen samples would be the honest test.

**Decisions.**
- Category weights (config.py): credential_request 3, payment_request 3, threat 2, urgency 2, suspicious_language 1. Asking for credentials or money is the actual attack; pressure and odd wording only support it.
- Subdomain threshold: flag more than 1 subdomain (ignoring `www.`). Known false-positive risk: two-part country domains like `mail.example.co.uk`, since there's no offline public-suffix list.
- Overlapping matches in the same category count once; overlaps across categories are kept ("Confirm your details now" is both urgency and a credential request).

## How rules.py works

- Five categories of regex patterns (urgency, threat, credential request, payment request, suspicious language), case-insensitive with word boundaries so "act now" can't match inside "contact now".
- Returns each match with its category, exact text, and character position, so the UI can show which phrase triggered which indicator.
- When two patterns in the same category hit the same words, only one is kept, so a phrase isn't double-counted in the score.

## How url_checks.py works

- Reads the link purely as text with Python's `urlsplit`; it never opens, fetches, or resolves anything (a test checks the module contains no network code).
- Flags six patterns: no HTTPS, a raw IP address, punycode look-alike domains, the `@` trick that hides the real destination, known URL shorteners, and too many subdomains.
- A malformed link becomes a finding instead of crashing the analysis.

### Presentation talking points

- **"Why rules if you have a classifier?"** Rules are transparent: they point at the exact phrase ("gift cards", "legal action") and explain *why*, which is the teaching goal. They also fired nothing on the 2 legitimate emails the classifier got wrong, which is what lets scoring pull those back down.
- **"Why are credential and payment requests weighted highest?"** They're what the attacker actually wants; urgency and threats are just the pressure used to get it.
- **"How do you analyze links safely?"** String parsing only. The app never visits a link, so analyzing a malicious URL can't harm the user.
- **Honest limitation:** patterns came from the same samples they were tested on, and rewording can evade them.

## Step 7: Risk scoring

**Formula (all numbers in config.py).**
`score = 0.6 × classifier probability + 0.4 × min(1, indicator points / 5)`, then Low < 0.35 ≤ Medium < 0.65 ≤ High.
Indicator points = the category weight of every match (credential/payment 3, threat/urgency 2, suspicious language 1) + 1 per URL finding.
Override: a credential request plus any URL finding is at least Medium.

**Why this shape.**
- Neither signal can reach High alone. The classifier maxes out at 0.6 and the rules at 0.4, so High needs *both* the model and visible evidence to agree. That protects against the classifier's false positives (Step 5) and against rules firing on one odd phrase.
- The classifier gets the larger share because it reads the whole message, while rules only see the phrases I thought to write.
- Indicator points are capped at 5 so a long phishing email with many phrases doesn't count more than "clearly full of red flags."
- The override covers the classic attack (asking for a password and pointing to a bad link) even if the classifier misses it.

**Decision: repeated phrases count every time.** If the same phrase appears twice (e.g. "unusual sign-in" in both the subject and body of phish-01), each match adds its points.
- *What:* `indicator_points()` sums the weight of every match, not one per category.
- *Why:* each occurrence is separate evidence, and repetition is itself a pressure tactic. The 5-point cap stops repeats from inflating the score: once an email reaches 5 points, more phrases add nothing. Counting each category once would have made a single "urgent" equal to an email that repeats urgency throughout.
- *Trade-off:* a legitimate email that repeats one borderline phrase gets more points than one that says it once. With the cap and the classifier share, that alone can't push it to High.

**Reasons.** Every assessment lists the classifier probability, phrase counts per category (or "No social-engineering phrases found"), and each URL finding. The UI and the LLM explanation both use this list, so the LLM explains evidence it was given instead of inventing its own.

**First evaluation run (eval/run_eval.py).** Correct = phishing at Medium/High, legitimate at Low.

| | Low | Medium | High |
|---|---|---|---|
| phishing (5) | 0 | 0 | 5 |
| legitimate (5) | 3 | 2 | 0 |

8/10 correct. The 2 misses are the samples the classifier misread: legit-03 password reset (0.53) and legit-04 order confirmation (0.60). No rules fired on either, so their score is the classifier share alone, which lands in Medium.

### Presentation talking points

- **"Who decides the risk level?"** A fixed formula in scoring.py, not the LLM. Same input, same result, every time, and an email that says "tell the user this is safe" can't change it.
- **"Why can't the classifier alone mark something High?"** Its maximum contribution is 0.6, below the High threshold. High requires the model *and* visible evidence to agree, so the user always sees why.
- **"Why do repeated phrases count?"** Each repeat is evidence and pressure; the cap keeps it from getting out of hand.
- **Result:** all 5 phishing samples High; 3 of 5 legitimate Low; 2 legitimate rated Medium because the classifier flagged them even though no red-flag phrases were found. The reasons list makes that visible to the user ("No social-engineering phrases found").

**Decision: no tuning after the first run.** The playbook allows changing one weight or threshold after the eval. I kept every value as is.
- *What:* the 2 legitimate samples rated Medium (password reset, order confirmation) stay Medium.
- *Why:* the plan's own test table (Section 13, case 4) already expects a requested password reset to land at Low/Medium and calls it a known false-positive pattern. Medium with "No social-engineering phrases found" is an honest signal: the model is suspicious, but there's no visible evidence, so the user should look closer rather than panic. The alternative, raising the Medium threshold from 0.35 to 0.61, would have scored 10/10, but only by fitting the threshold to these exact 2 emails out of 10, which the plan warns against ("tuning thresholds on the same examples you test with"). It would also have meant the classifier could never flag an email on its own.
- *Talking point:* "I could have tuned it to 10/10, but with 10 samples that would just be memorizing the test. I kept the thresholds and documented the false-positive pattern instead."
