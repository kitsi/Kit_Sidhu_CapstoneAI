"""Print Python, torch, and transformers versions, mps availability, and Ollama status."""

import platform

import ollama
import torch
import transformers

from phish_assistant.config import OLLAMA_MODEL


def ollama_status(model: str) -> str:
    """Describe whether the local Ollama server is reachable and has `model` pulled."""
    try:
        names = [m.model for m in ollama.list().models]
    except (ConnectionError, ollama.ResponseError) as e:
        return f"not reachable ({type(e).__name__}): start the Ollama app"
    if model in names:
        return f"reachable, {model} pulled"
    return f"reachable, but {model} missing: run `ollama pull {model}`"


def main() -> None:
    """Print one line per environment check."""
    print(f"Python:        {platform.python_version()}")
    print(f"torch:         {torch.__version__}")
    print(f"transformers:  {transformers.__version__}")
    print(f"mps available: {torch.backends.mps.is_available()}")
    print(f"Ollama:        {ollama_status(OLLAMA_MODEL)}")


if __name__ == "__main__":
    main()
