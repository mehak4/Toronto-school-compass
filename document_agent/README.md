# Document Action Agent

A separate Python project within Toronto School Compass. It reads a PDF or Word document and extracts action items or requirements into a source-backed JSON collection and Markdown report using a LangGraph **plan → act → observe → repeat** workflow with durable human review.

## Setup

From the repository root, use the existing Python 3.11/3.12 environment:

```sh
source .venv/bin/activate
python -m pip install -r document_agent/requirements.txt
```

The existing root `.env` supplies `MODEL_BASE_URL`, `MODEL_API_KEY` and `CHAT_MODEL`. For a new checkout, copy the root `.env.example` without overwriting an existing `.env`, then fill it locally. `config.json` selects environment-variable names, chunk size, maximum steps and native/JSON tool mode. No secrets belong in config or source files.

The client uses the configured HTTPS `/chat/completions` endpoint (including compatible Nebius endpoints). Native tool calling is the default. For providers lacking native tools, set `tool_mode` to `json` in a copied config file and pass `--config`; JSON mode still runs the same validated multi-step action loop. Endpoint and model compatibility must be tested with the account in use.

## Usage

```sh
# Local ingestion only: no credentials or network needed.
python -m document_agent.main --file /path/to/document.pdf --ingest-only

# Extract obligations, dates and named owners with exact source quotes.
python -m document_agent.main --file /path/to/document.docx --task extract_action_items
python -m document_agent.main --file /path/to/spec.pdf --task extract_requirements
```

For the requested direct entry-point style:

```sh
cd document_agent
../.venv/bin/python main.py --file /path/to/document.pdf --task extract_action_items
```

Optional flags: `--config config.json`, `--env-file /path/to/.env`, `--output /path/to/new-directory`. Existing output directories are never overwritten. Default outputs use a unique timestamp in `document_agent/outputs/`, which Git ignores. Store private inputs under the ignored `document_agent/inputs/` directory.

## Ingestion

`document_loader.py` uses [pdfplumber](https://github.com/jsvine/pdfplumber) for multi-page PDFs, with page references, repeated margin removal and best-effort tables. It uses [python-docx](https://python-docx.readthedocs.io/en/latest/api/document.html) to read Word paragraphs and tables in body order, excluding header/footer parts. Whitespace and Unicode are normalized before character-bounded chunking.

PDF margin removal is heuristic; review `document.json` for omissions. Tables may duplicate PDF text, scanned PDFs need external OCR, and DOCX text boxes or tracked changes may not be extracted. DOCX provenance uses body-block numbers because pagination depends on Word's renderer. Files over 25 MB, unsupported extensions, corrupt/encrypted files and documents with no readable text fail clearly. Long documents may require additional steps or smaller task scope; partial results are labelled rather than silently called complete.

## Human review

Extraction writes a local `draft.json` and `draft.md`, then pauses at a LangGraph interrupt. Read the draft and its quoted evidence, then explicitly approve or reject it:

```sh
python -m document_agent.main --resume document_agent/outputs/RUN_ID --decision approve --review-note "Checked against source"
python -m document_agent.main --resume document_agent/outputs/RUN_ID --decision reject --review-note "Missing obligations; revise input and rerun"
```

Choose one decision. Approval writes final `result.json` and `report.md`; rejection keeps only working artifacts and the decision record. Review resumes without model credentials or further model calls. A terminal decision cannot be replayed or changed; rerun extraction for a new draft. This CLI supports approve/reject, not in-place editing or correction loops.

Drafts, logs and checkpoints are local working writes authorized by starting a run. Approval gates the final export; no emails, external records or files outside the chosen run directory are modified by the agent.

## Decision loop and tools

1. **Plan:** the model sees the task, chunk count, extraction warnings, allowed actions and previous observations.
2. **Act:** it calls `document_action` with a brief operational purpose and one action: `read_chunk`, `search_document`, `record_actions`, or `finish`.
3. **Observe:** the app executes the allowlisted tool and returns content, a save confirmation, or an actionable validation error.
4. **Repeat:** conditional LangGraph edges return to planning, stop on an error/step limit, or enter human review after all chunks have been read.
5. **Review:** `interrupt()` persists state; `Command(resume=...)` supplies the human decision. Only approval enables final export.

`search_document` uses local keyword overlap and returns up to three complete chunks; it does not require embeddings. `record_actions` saves structured items with an exact source quote, source location, and owner/due-date strings (null if unknown). Quotes must occur in a previously read chunk and non-null fields must occur in that quote. Items are validated before storage and duplicates within a chunk are suppressed. These checks prevent invented evidence but do not prove semantic classification or complete extraction.

The model cannot run shell commands, send messages, browse or choose output file paths. Document instructions are treated as data. The CLI writes artifacts to the user-selected output directory. Document passages and accumulated tool observations are sent to the configured model during agent runs; `--ingest-only` stays local.

## Artifacts and errors

- `document.json`: cleaned text chunks, locations and warnings.
- `steps.jsonl`: each action, brief purpose, tool arguments and observation, flushed as work progresses. This is an execution trace, not hidden chain-of-thought.
- `draft.json` / `draft.md`: unapproved extraction and readable source quotes.
- `checkpoint.sqlite` / `run.json`: durable graph state and thread ID; treat checkpoints as trusted local files.
- `result.json`: approved task result, reviewed chunks, extracted records and steps.
- `review.json`: pending, approved or rejected status and human decision.
- `report.md`: approved readable quoted items with owners, dates and provenance.

Exit code 0 means ingestion succeeded, extraction is awaiting review, or a review decision completed; 1 means input/config/output error; 2 means model failure or step-limit exhaustion with saved partial results. A process interrupted externally may leave only the document and step trace. An approved run is not a guarantee that the model found every obligation. Output traces contain document content and should be reviewed before sharing.

## Modules and tests

- `document_loader.py`: extraction and cleaning.
- `tools.py`: tool schema, search/read actions, record validation and coverage gate.
- `agent.py`: model adapter, typed LangGraph state, nodes, conditional edges and review interrupt.
- `main.py`: CLI, configuration and output persistence.

```sh
python -m pytest -q tests document_agent/tests
```

Tests create real multi-page PDF and Word fixtures, check table/body order, corrupt files, retry observations in native and JSON modes, grounded field validation, step limits and output overwrite protection. Live smoke testing uses synthetic content only; no user document is sent automatically.

## Week 3 submission

See [the Week 3 report](WEEK3_REPORT.md) for the primer, framework, state and approval boundaries, validation and remaining submission assets. This implementation uses LangGraph from the LangChain ecosystem for orchestration and retains the existing compatible HTTP model adapter; it does not require a separate LangChain agent wrapper.
