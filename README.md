# Toronto School Compass

A Streamlit RAG application for Toronto parents exploring curriculum, school programs, registration guidance, Fraser ratings and optional childcare. It combines eleven curated official-source summaries, two reviewed school profiles, live TDSB regular-program address lookup and an Ontario-wide Fraser report catalog.

## Run locally

Use Python 3.11 or 3.12. On macOS with Homebrew, `brew install python@3.12` provides a compatible interpreter.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

School cards and deterministic guidance work without model credentials. Address lookup requires access to the official TDSB website. To enable document answers, create `.env` from `.env.example` **only if you do not already have `.env`**, then configure the provider URL, key and model IDs locally:

```sh
python ingest.py
streamlit run app.py
```

The provider must support HTTPS `/embeddings` and `/chat/completions` endpoints. Query and document embeddings must use the same model. Rebuild the index after corpus or embedding configuration changes; no rebuild is needed just for answerability code changes. Never commit `.env`.

## What the app does

- **Find schools:** submits a civic address to TDSB's official regular-program finder and displays all returned schools and attendance-area links. Ambiguous streets and service failures receive explicit handling. The finder has no school-year selector, so requested-year admission is not verified.
- **Explore and compare:** combines Joyce and Glen Park's reviewed profiles with schools returned by the current lookup. Additional profiles have public contact information and shared guidance; school-specific programs and childcare may remain unknown.
- **Curriculum and registration:** separates board-wide learning guidance from school offerings and ties known application windows to their specified entry years. Exact local deadlines and unverified years remain unknown.
- **Fraser ratings:** displays Fraser-only scores with assessment year and source-page links. The local catalog contains 3,052 elementary and 747 secondary Ontario report rows from the 2025 editions, covering 2023–24. Seven reviewed school-code mappings take precedence; other matches require a unique name, municipality and school level. Missing or ambiguous scores remain unavailable.
- **Document answers:** retrieves relevant summaries, asks the model to select sources, checks whether selected passages address the specific question, and renders original cited excerpts. It returns a fallback when evidence or validation is insufficient.

## How RAG works

LangChain splits reviewed JSON summaries into 1,800-character chunks with 200-character overlap. Chroma stores their embeddings. LangGraph routes registration, ratings, boundary, legacy fee and vacancy questions to deterministic handling; other questions use dense retrieval with topic filters and balanced school coverage.

The model returns source IDs rather than factual prose. A separate answerability call reviews nonempty selections, and the app validates the returned subset before showing whole excerpts with titles, dates and citations. This is extractive RAG: less conversational than paraphrasing, with source context preserved. The model-based review can still choose poorly or omit useful information, and adds latency and cost.

The tested configuration uses Nebius `Qwen/Qwen3-Embedding-8B` for embeddings and `Qwen/Qwen3-30B-A3B-Instruct-2507` for selection and answerability review. Availability depends on the configured provider account. Pinecone and Hugging Face keys are not required by this Chroma/Nebius implementation.

## Validation and submission

As of September 12, 2026, **55 automated tests pass**. The latest sequential live runs covered 15 main questions and five additional phrasings with correct routing, zero request errors and every response below ten seconds. The coding-lessons question now abstains while broad Kindergarten learning remains answerable. These are small development-time runs, not guarantees or independently measured faithfulness scores.

Start with the [evaluation overview](docs/EVALUATION.md), [project report](docs/PROJECT_REPORT.md) and [assignment checklist](docs/SUBMISSION_CHECKLIST.md). The report is ready for user review and copying into the required Google Doc. Recording, GitHub publication and submission remain pending.

```sh
python -m pytest -q
# Live runs use configured API credits. Use a fresh output filename each time.
python evaluate.py --live --cases data/submission_evaluation_cases.json --output evaluation-submission-next.json
python evaluate.py --live --cases data/grounding_paraphrase_cases.json --output evaluation-paraphrase-next.json
python evaluate.py --summarize docs/evaluation/answerability-raw-01.json
```

Targets are 95% factual-claim faithfulness and 90% of answers under ten seconds. Current independent claim-level review is pending. Historical evaluations and their failures are preserved and indexed in the evaluation overview; their percentages do not certify the final app.

## Data, privacy and limits

The eleven-source corpus is manually reviewed, not a full production crawl. Fraser report import is separate from the vector corpus; one published row has no current score. Ratings are third-party academic indicators, not a complete assessment of school quality. See [rating provenance](docs/FRASER_RATINGS.md) and [address lookup details](docs/ADDRESS_MATCHING.md).

Childcare is optional. Dated vacancy reports do not establish current availability; centre hours do not establish exact session schedules. Missing fees mean unknown, not free. Legacy fee safeguards remain in code even though fee controls are absent from the UI.

Addresses submitted in the lookup form go to TDSB and remain in the active app session; they are not stored in the vector index or sent to the model. Public returned school profiles may be used as evidence. Do not enter home addresses in chat: address detection there is heuristic. Model questions and evidence are processed by the configured provider. Keep credentials, private inputs and local caches out of published assets.

## Main files

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit interface |
| `address_lookup.py`, `profiles.py` | TDSB lookup and merged public school profiles |
| `core.py` | Structured directory and deterministic guidance |
| `provider.py`, `graph.py` | Model calls, retrieval, source selection and answerability validation |
| `ingest.py` | Chunking and vector indexing |
| `fraser.py`, `scripts/import_fraser.py` | Rating matching and reproducible PDF import |
| `evaluate.py`, `tests/` | Saved live evaluations and automated checks |
| `data/`, `docs/` | Source records, question sets and submission documentation |

## Document action agent

The separate [document-agent project](document_agent/README.md) accepts PDF/Word files and extracts structured action items or requirements through a LangGraph tool loop with persistent state and human approval before final export. Start with `python -m document_agent.main --file /path/to/document.docx --ingest-only`; its dependencies and usage are documented separately.
