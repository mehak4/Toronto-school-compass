# Week 2 assignment audit

Audited September 12, 2026 against the supplied `Week 2 Project Handout (Aug 2026)-2.docx`. The handout defines deliverables; its email, upload and submission instructions have not been executed.

This is a **bring-your-own use case on Track 2**, closest to the policy Q&A example. The example's 15-question evaluation is used as a useful benchmark. The financial track's two chunking strategies/reranking, GraphRAG's 20 nodes, and support track's hybrid search/20 queries are not requirements for this custom project.

| Requirement | Status | Evidence or remaining action |
| --- | --- | --- |
| Primer: user, question, specific corpus, surface, faithfulness target | Ready | `PROJECT_REPORT.md` |
| Latency ceiling | Defined | 90% of answers under 10 seconds; report current run separately from targets |
| Framework fields, 1–2 sentences each | Ready | Report framework table |
| Ingest, chunk, embed, store, retrieve, cited generation | Implemented | `ingest.py`, `provider.py`, `graph.py`, Chroma, LangChain and LangGraph |
| Unknown-information path | Implemented, imperfect | Deterministic guidance, excerpt validation and answerability fallback; independent review remains pending |
| Working Q&A interface | Implemented | Streamlit app; 55 automated tests pass |
| Evaluation with edge cases and failure analysis | Current run documented | `EVALUATION.md` and `evaluation/ANSWERABILITY_FINDINGS.md`; independent claim-level review pending |
| Project documentation: overview, data, prompts, iterations, learnings | Local draft ready | `PROJECT_REPORT.md`; copy final reviewed text into a Google Doc |
| Video at most 5 minutes: live result and use of AI coding tools | Pending | Follow `DEMO.md`; record and obtain shareable link |
| Project assets on GitHub | Pending | Source files ready locally; repository URL still needed |
| Submit documentation, video and assets links | Pending | User reviews and submits final links using the assignment form |

The general deliverables explicitly ask for GitHub assets and a Google Doc. Some example sections mention a zip alternative; a local zip would be a handoff/backup, not evidence that the general GitHub requirement has been satisfied. No recording, Google Doc, repository publication or submission is claimed here.

Optional expansion to 10–15 reviewed profiles, a larger curriculum corpus, hybrid retrieval and reranking can improve the project but need not block an honestly scoped submission. Full Fraser report import expands rating coverage; it does not expand the eleven-document RAG corpus or verify every school profile.

## Final handoff

1. Walk through the app using a public address, a comparison, Fraser scores, a supported learning question and the unsupported daily-coding question. This manual walkthrough remains pending.
2. Review the [project report](PROJECT_REPORT.md) and [evaluation overview](EVALUATION.md), then copy the final approved content into the required Google Doc.
3. Record the [demo](DEMO.md), five minutes or less.
4. Publish reviewed code and non-sensitive assets to GitHub; exclude `.env`, virtual environments, caches and private inputs.
5. Check access to the document, video and repository links, then submit them through the assignment form.

Documentation consolidation does not constitute source refresh, independent human scoring, a new live-address check or external publication.
