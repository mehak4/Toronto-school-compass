# LangGraph validation — September 23, 2026 (Toronto)

- Combined test suite: **67 passed** (55 school-app and 12 document-agent cases).
- Live native-tool smoke test: synthetic Word document with Alice submitting a report by Friday and Bob reviewing it by Monday.
- Five tool calls: read, record, read, record, finish.
- Both quotes, owners and dates matched the synthetic source.
- Final graph status: `awaiting_review`; draft and SQLite checkpoint exist; no approved JSON or Markdown export exists.
- Separate automated subprocess tests resume durable checkpoints for both approve and reject without model calls, check output gating, and reject repeated review decisions.

No independent completeness score, broad success rate or latency target achievement is claimed. The live draft remains pending; synthetic approval/rejection behavior was verified by tests, not by approving a user's document. Generated documents and checkpoints are local ignored artifacts.

Reproduce automated checks:

```sh
python -m pytest -q tests document_agent/tests
```
