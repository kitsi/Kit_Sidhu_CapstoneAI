"""Dataclasses shared between components."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailInput:
    """A validated email ready for analysis.

    `url` is the optional link the user pasted separately; `body_urls` are links
    found in the body. Both are plain text and are never fetched.
    """

    subject: str
    body: str
    url: str | None = None
    body_urls: list[str] = field(default_factory=list)


@dataclass
class Indicator:
    """One social-engineering phrase found in the email text."""

    category: str  # e.g. "urgency"
    matched: str  # exact text that triggered it
    start: int  # character offsets into the analyzed text
    end: int


@dataclass
class ClassifierResult:
    """Output of the pre-trained classifier for one email."""

    label_scores: dict[str, float]
    phishing_probability: float
    truncated: bool  # True if the input exceeded the model's token limit


@dataclass
class RiskAssessment:
    """Deterministic risk level with the reasons that produced it."""

    level: str  # "Low", "Medium", or "High"
    score: float
    reasons: list[str]


@dataclass
class AnalysisReport:
    """Everything the UI needs to render one analysis."""

    email: EmailInput
    classifier: ClassifierResult
    indicators: list[Indicator]
    url_findings: list[str]
    assessment: RiskAssessment
    explanation: Any = None  # filled in by explainer.py (Milestone 6)
