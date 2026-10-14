"""Smoke test: every module in the package imports cleanly."""

import importlib

import pytest

MODULES = [
    "phish_assistant",
    "phish_assistant.config",
    "phish_assistant.models",
    "phish_assistant.validation",
    "phish_assistant.classifier",
    "phish_assistant.rules",
    "phish_assistant.url_checks",
    "phish_assistant.scoring",
    "phish_assistant.prompts",
    "phish_assistant.explainer",
    "phish_assistant.pipeline",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name: str) -> None:
    """Importing the module raises no errors."""
    importlib.import_module(name)
