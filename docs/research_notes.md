# Phase 1 Research Notes

## How LLMs work (high level)

- A **large language model** is a neural network trained on large amounts of text to predict the next **token** (a word or part of a word). Generating text is repeated next-token prediction.
- The **prompt** is everything the model reads: a **system prompt** sets its role and rules, and the **user prompt** carries the request. The model has no other knowledge of the task, so what goes in the prompt shapes what comes out.
- **Temperature** controls randomness. Low values (0.1–0.3) give more consistent wording, which suits explanations that must follow rules.
- LLMs can **hallucinate**, stating things that aren't supported, and can be manipulated by **prompt injection**, where text inside the data tries to give new instructions.
- **Generative models vs classifiers:** an LLM like Llama writes text; a classifier like DistilBERT only assigns probabilities to fixed labels. This project uses each for what it's good at: the classifier scores, the LLM explains.
- **Running locally:** smaller open models (here 3 billion parameters, quantized to about 2 GB) can run on a laptop without a GPU. They're slower and less capable than large hosted models, but nothing leaves the machine and nothing costs money.

## Tool comparison

| Tool | What it is | Used here? | Why |
|---|---|---|---|
| **Ollama** | App that downloads and runs open LLMs locally and exposes them to code through a local server | **Yes**: runs `llama3.2:3b` for explanations | Simple install, one command to pull a model, free, local-only. Works directly with LangChain. |
| **GPT4All** | Desktop app and Python library for running open LLMs locally | No (considered as an alternative runner) | Similar purpose to Ollama. Ollama's model library and LangChain integration made it the simpler choice for this project. |
| **Hugging Face Transformers** | Python library for running pre-trained models from the Hugging Face Hub, including classifiers | **Yes**: runs the DistilBERT phishing classifier | The phishing classifier is published on Hugging Face, and Transformers loads and runs it in a few lines on CPU. |
| **LangChain** | Framework for connecting prompts, models, and output parsers into chains | **Yes**, for the explanation step only | The explanation is a real chain (prompt template → model → structured output), and LangChain validates the output against a Pydantic schema. The classifier, rules, and scoring are deterministic Python and gain nothing from a framework. |

## Running a model locally

- **LLM:** installed the Ollama app on macOS, ran `ollama pull llama3.2:3b` (about 2 GB), and tested it with `ollama run llama3.2:3b "Say hello in five words."`. `scripts/check_env.py` confirms the local Ollama server is reachable and has the model.
- **Classifier:** `scripts/download_models.py` caches the Hugging Face model, and `scripts/explore_classifier.py` ran it on 10 sample emails to learn its labels before writing any app code. Findings: scores sum to 1; `LABEL_1` tracks phishing on email text; every URL scored the same label, so links are checked with string rules instead.
- **Observed performance on the development Mac (Intel, CPU only):** the classifier answers in well under a second; each LLM explanation takes about 15–55 seconds.

## Resources reviewed

- Ollama documentation and the model library page for Llama 3.2
- Hugging Face Transformers pipeline documentation
- LangChain documentation on `ChatOllama` and structured output
- The classifier's model card on Hugging Face
- Course lectures and readings on LLMs and prompt engineering

## How instructor feedback changed the plan

- **No fine-tuning:** the original idea of training a DistilBERT model was replaced with a pre-trained classifier used as-is, as the course requires.
- **Text-only MVP:** the scope was narrowed to pasted subject, body, and link; mailbox connections and attachment analysis are out of scope.
- **Renamed project:** "Zero-Trust Phishing Detector" became "Explainable AI Phishing Analysis Assistant," since *Zero Trust* refers to a broader security architecture.
- **SHAP and header analysis moved to optional:** both are listed as next steps rather than part of the MVP.
