"""Streamlit entry point (UI only). All analysis happens in pipeline.analyze().

Email text and LLM output are shown with st.text, which does no Markdown or
HTML parsing, so nothing from the email can render as HTML or a clickable link.
"""

import json
import logging
from itertools import groupby
from pathlib import Path

import streamlit as st

from phish_assistant.classifier import load_model
from phish_assistant.models import AnalysisReport
from phish_assistant.pipeline import AnalysisError, analyze
from phish_assistant.validation import validate_input

logging.basicConfig(level=logging.INFO)  # stage timings only, never email content

EVAL_SET = Path(__file__).resolve().parent / "eval" / "eval_set.jsonl"
EXAMPLES = {
    "Credential phish with a raw IP link": "phish-01-credential-urgency",
    "Gift-card request from a 'boss' (no link)": "phish-04-giftcard-boss",
    "Library newsletter (legitimate)": "legit-01-newsletter",
}
NO_EXAMPLE = "Choose an example..."
LEVEL_DISPLAY = {
    "High": (st.error, "⛔", "High risk: strong signs of phishing."),
    "Medium": (
        st.warning,
        "⚠️",
        "Medium risk: some warning signs. Check carefully before acting.",
    ),
    "Low": (
        st.info,
        "ℹ️",
        "Low risk: few warning signs found. This doesn't mean the email is safe.",
    ),
}
DISCLAIMER = (
    "This is an educational risk-assessment tool. It can't guarantee that an email is "
    "safe or malicious. When in doubt, don't click, and report the message to your IT "
    "or security team."
)
SPINNER_TEXT = (
    "Analyzing... The AI explanation runs locally on your computer and can take up "
    "to a minute."
)


@st.cache_resource(show_spinner="Loading the phishing classifier (first run only)...")
def warm_up_models() -> bool:
    """Load the classifier once per server process."""
    load_model()
    return True


def load_example(example_id: str) -> dict:
    """Return one sample from the eval set by id."""
    for line in EVAL_SET.read_text(encoding="utf-8").splitlines():
        if line.strip() and (sample := json.loads(line))["id"] == example_id:
            return sample
    raise KeyError(example_id)


def on_example_selected() -> None:
    """Fill the form fields with the chosen example."""
    choice = st.session_state["example"]
    if choice == NO_EXAMPLE:
        return
    sample = load_example(EXAMPLES[choice])
    st.session_state["subject"] = sample["subject"]
    st.session_state["body"] = sample["body"]
    st.session_state["url"] = sample["url"] or ""


def render_sidebar() -> None:
    """Example selector."""
    with st.sidebar:
        st.header("Try an example")
        st.selectbox(
            "Load example",
            [NO_EXAMPLE, *EXAMPLES],
            key="example",
            on_change=on_example_selected,
        )
        st.caption("Examples are synthetic emails from the evaluation set.")


def render_risk(report: AnalysisReport) -> None:
    """Risk level as text plus icon (not color alone), with reasons."""
    box, icon, text = LEVEL_DISPLAY[report.assessment.level]
    box(text, icon=icon)
    st.caption(f"Risk score {report.assessment.score:.2f} (0 to 1)")
    if report.classifier.truncated:
        st.info("This email is long: the classifier only read the first part of it.")
    st.subheader("Why this rating")
    for reason in report.assessment.reasons:
        st.text(f"• {reason}")


def render_evidence(report: AnalysisReport) -> None:
    """Matched phrases grouped by category, then URL findings."""
    st.subheader("Warning signs in the text")
    if not report.indicators:
        st.text("No social-engineering phrases found.")
    by_category = sorted(report.indicators, key=lambda i: i.category)
    for category, group in groupby(by_category, key=lambda i: i.category):
        phrases = list(dict.fromkeys(i.matched for i in group))
        st.markdown(f"**{category.replace('_', ' ').capitalize()}**")
        for phrase in phrases:
            st.text(f'• "{phrase}"')
    if report.url_findings:
        st.subheader("Link warning signs")
        st.caption("Links are checked as text only. They are never opened.")
        for finding in dict.fromkeys(report.url_findings):
            st.text(f"• {finding}")


def render_explanation(report: AnalysisReport) -> None:
    """The LLM explanation, recommended actions, and limitations."""
    explanation = report.explanation
    st.subheader("Explanation")
    if explanation.is_fallback:
        st.info(
            "The AI explanation wasn't available, so this is a standard explanation "
            "built from the evidence above."
        )
    st.text(explanation.summary)
    for item in explanation.evidence:
        st.text(f"• {item.indicator}: {item.why_it_matters}")
    st.subheader("What to do")
    for action in explanation.recommended_actions:
        st.text(f"• {action}")
    st.caption("Limitations")
    st.text(explanation.limitations)


def run_analysis(subject: str, body: str, url: str) -> AnalysisReport | None:
    """Validate and analyze, showing friendly errors instead of stack traces."""
    try:
        email = validate_input(subject, body, url)
    except ValueError as exc:
        st.error(str(exc))
        return None
    try:
        warm_up_models()
        with st.spinner(SPINNER_TEXT):
            return analyze(email)
    except AnalysisError as exc:
        st.error(str(exc))
    except Exception as exc:  # noqa: BLE001 - never show a stack trace to the user
        # Log only the error type: a traceback message could contain email text.
        logging.getLogger(__name__).error("Analysis failed: %s", type(exc).__name__)
        st.error("Something went wrong during the analysis. Please try again.")
    return None


def main() -> None:
    """Page layout: form, then the report."""
    st.set_page_config(page_title="Phishing Analysis Assistant", page_icon="🎣")
    st.title("Explainable AI Phishing Analysis Assistant")
    st.caption(DISCLAIMER)
    render_sidebar()
    with st.form("email_form"):
        subject = st.text_input("Subject", key="subject")
        body = st.text_area("Email body (required)", key="body", height=220)
        url = st.text_input("Link from the email (optional, never opened)", key="url")
        submitted = st.form_submit_button("Analyze", type="primary")
    if submitted and (report := run_analysis(subject, body, url)):
        render_risk(report)
        render_evidence(report)
        render_explanation(report)
        st.divider()
        st.caption(DISCLAIMER)


main()
