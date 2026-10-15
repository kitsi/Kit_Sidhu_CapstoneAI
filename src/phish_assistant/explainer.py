"""LLM explanation via a LangChain chain on local Ollama, with a safe fallback.

The chain is prompt -> ChatOllama -> Pydantic structured output. The LLM only
explains the evidence; the risk level always comes from scoring.py.
"""

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from phish_assistant.config import (
    CATEGORY_WEIGHTS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    OLLAMA_MODEL,
)
from phish_assistant.models import EmailInput, Indicator, RiskAssessment
from phish_assistant.prompts import SYSTEM_PROMPT, USER_TEMPLATE, prompt_inputs

log = logging.getLogger(__name__)


class Evidence(BaseModel):
    """One piece of evidence and why it matters to the user."""

    indicator: str
    why_it_matters: str


class LLMExplanation(BaseModel):
    """The JSON contract the LLM must return (plan Section 12)."""

    summary: str = Field(description="2-3 sentence plain-language overview")
    evidence: list[Evidence]
    recommended_actions: list[str]
    limitations: str = Field(description="one sentence")


class Explanation(LLMExplanation):
    """An explanation shown to the user; is_fallback marks the template version."""

    is_fallback: bool = False


# Claims the app must never make (plan Section 14).
_FORBIDDEN = re.compile(
    # "to be safe, verify..." is fine advice, so "be safe" isn't listed.
    r"\b(?:is|looks|seems|appears|it's)\s+(?:completely\s+|totally\s+|probably\s+)?safe\b"
    r"|\bsafe\s+to\s+(?:open|click|trust|use|reply)\b"
    r"|\bdefinitely\s+(?:legitimate|malicious)\b"
    # Vouching for the email ("appears to be a legitimate newsletter"). General
    # statements like "legitimate companies don't ask..." have no verb and pass.
    r"|\b(?:is|looks|seems|appears|it's)(?:\s+to\s+be)?\s+(?:an?\s+)?"
    r"(?:completely\s+|totally\s+|probably\s+|likely\s+)?"
    r"(?:legitimate|genuine|authentic|verified)\b"
    r"|\bguarantee[ds]?\b",
    re.IGNORECASE,
)

_CATEGORY_WHY = {
    "urgency": "Pressure to act fast is meant to stop you from checking whether "
    "the message is real.",
    "threat": "Threats of losing access, money, or legal trouble are used to "
    "scare people into acting without thinking.",
    "credential_request": "Real organizations don't ask you to send or confirm "
    "your password or login details through an email link.",
    "payment_request": "Unexpected requests for payment, gift cards, or new bank "
    "details are a common way attackers steal money.",
    "suspicious_language": "Generic greetings, secrecy, or odd wording often "
    "appear in mass or impersonation scams.",
}
_URL_WHY = (
    "The link's address has a pattern often used to disguise where it really goes."
)
_ACTIONS = [
    "Don't click links, open attachments, or reply until you've checked the message.",
    (
        "Verify the request by contacting the sender through a channel you already "
        "know, such as their official website or phone number."
    ),
    "Report the message to your IT or security team if you're unsure.",
]
_LIMITATIONS = (
    "This is an automated risk assessment: it can miss well-written phishing and "
    "can flag legitimate mail, so use your own judgment."
)

# URL findings from url_checks.py all start with one of these words.
_URL_REASON_PREFIXES = ("Link", "Domain")
_URL_WORD = re.compile(r"\b(?:url|link|domain|https?)\b", re.IGNORECASE)

_chain: Any = None  # built on first use, then reused


def _label(category: str) -> str:
    """Return the readable label for a category, e.g. "credential request"."""
    return category.replace("_", " ")


def _build_chain() -> Any:
    """Build prompt | ChatOllama.with_structured_output(LLMExplanation)."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_ollama import ChatOllama

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", USER_TEMPLATE)]
    )
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        temperature=LLM_TEMPERATURE,
        client_kwargs={"timeout": LLM_TIMEOUT_SECONDS},
    )
    return prompt | llm.with_structured_output(LLMExplanation)


def _get_chain() -> Any:
    """Return the chain, building it on first call."""
    global _chain
    if _chain is None:
        _chain = _build_chain()
    return _chain


def fallback_explanation(
    assessment: RiskAssessment, indicators: list[Indicator]
) -> Explanation:
    """Build a template explanation from the scoring results alone."""
    categories = list(dict.fromkeys(i.category for i in indicators))
    evidence = [
        Evidence(indicator=_label(c), why_it_matters=_CATEGORY_WHY[c])
        for c in categories
    ]
    evidence += [
        Evidence(indicator=r, why_it_matters=_URL_WHY) for r in _url_reasons(assessment)
    ]
    found = "the evidence listed below" if evidence else "the classifier score alone"
    summary = (
        f"This email was rated {assessment.level} risk based on {found}. "
        "A detailed AI explanation isn't available right now."
    )
    return Explanation(
        summary=summary,
        evidence=evidence,
        recommended_actions=_ACTIONS,
        limitations=_LIMITATIONS,
        is_fallback=True,
    )


def _url_reasons(assessment: RiskAssessment) -> list[str]:
    """Return the URL findings among the scoring reasons."""
    return [r for r in assessment.reasons if r.startswith(_URL_REASON_PREFIXES)]


def _all_text(output: LLMExplanation) -> str:
    """Join every text field of an explanation for checking."""
    parts = [output.summary, output.limitations, *output.recommended_actions]
    parts += [f"{e.indicator} {e.why_it_matters}" for e in output.evidence]
    return "\n".join(parts)


def _unsupported_categories(output: LLMExplanation, allowed: set[str]) -> set[str]:
    """Return indicator categories named in evidence that weren't in the input."""
    named = " ".join(e.indicator for e in output.evidence).lower()
    return {
        c
        for c in CATEGORY_WEIGHTS
        if c not in allowed and (c in named or _label(c) in named)
    }


def _names_url_evidence(output: LLMExplanation) -> bool:
    """Return True if any evidence item is named as a URL/link/domain finding.

    Only the evidence *name* is checked, so explaining a phrase like
    "Click the link" under another category is still allowed.
    """
    return any(_URL_WORD.search(e.indicator) for e in output.evidence)


def passes_safety_check(
    output: LLMExplanation,
    indicators: list[Indicator],
    has_url_findings: bool = False,
) -> bool:
    """Reject forbidden claims and evidence that wasn't actually found."""
    if _FORBIDDEN.search(_all_text(output)):
        log.warning("Explanation rejected: forbidden claim")
        return False
    if _unsupported_categories(output, {i.category for i in indicators}):
        log.warning("Explanation rejected: unsupported indicator category")
        return False
    if not has_url_findings and _names_url_evidence(output):
        log.warning("Explanation rejected: URL evidence without URL findings")
        return False
    return True


def explain(
    assessment: RiskAssessment,
    email_input: EmailInput,
    indicators: list[Indicator] | None = None,
    *,
    chain: Any = None,
) -> Explanation:
    """Explain the assessment in plain language. Never raises.

    `chain` can be swapped for a fake in tests. On any failure (Ollama down,
    model missing, invalid output, failed safety check) returns the fallback.
    """
    indicators = indicators or []
    try:
        runnable = chain if chain is not None else _get_chain()
        output = runnable.invoke(prompt_inputs(assessment, email_input, indicators))
        if not isinstance(output, LLMExplanation):
            output = LLMExplanation.model_validate(output)
    except Exception as exc:  # noqa: BLE001 - any LLM failure must degrade, not crash
        log.warning("Explanation unavailable: %s", type(exc).__name__)
        return fallback_explanation(assessment, indicators)
    has_urls = bool(_url_reasons(assessment))
    if not passes_safety_check(output, indicators, has_urls):
        return fallback_explanation(assessment, indicators)
    return Explanation(**output.model_dump())
