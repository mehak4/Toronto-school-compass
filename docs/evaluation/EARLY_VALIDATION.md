Validation on September 12, 2026

Historical snapshot: implementation details and test counts below describe earlier iterations. For the current app, see [project report](../PROJECT_REPORT.md) and [current evaluation](../EVALUATION.md). Fraser scores now use the full report import and the app displays Fraser only.

- Thirteen automated tests passed, including real Chroma storage and LangGraph execution with mocked model calls, reviewed metric calculations, and evaluation output preservation.
- Streamlit AppTest passed initial render and full-address submission.
- Fifteen routing evaluation cases passed.
- Monthly estimates now require the same source URL and effective date as fee labels; regression checks cover missing provenance and a documented zero rate.
- Live Nebius indexing succeeded: four chunks from four sources using `Qwen/Qwen3-Embedding-8B`. The previously suggested `BAAI/bge-en-icl` returned HTTP 404 and was absent from the account model catalog.
- A live childcare-hours question returned a cited RAG answer using `Qwen/Qwen3-30B-A3B-Instruct-2507` and four evidence chunks. The answer distinguished centre hours from session times and acknowledged missing Dalemount hours, but omitted the undated-source caveat. This smoke check does not establish the full evaluation targets; two fifteen-case runs and AI-assisted scoring are now recorded in docs/evaluation/FINDINGS.md; independent human sign-off remains pending.
- Automatic school boundary matching is not implemented.
- Fees remain unknown where no published rate was found.

- Revised live run: 15/15 routes, zero API errors, 15/15 responses under 10 seconds; AI-assisted review accepted 11/15 answers. Claim-unit support was 92.65%, existing citation support 88.71%, retrieval precision 32.14%. Quality target remains unmet.
- Added explicit unknown-waitlist guidance, cited undated-hours source notes and prompt refinements. Refreshed the reviewed sources and index.

School-topic update: 18 automated tests passed; 11 summaries indexed. Two eight-case live runs completed with zero API errors and every response under 10 seconds. Generated curriculum answers still have documented grounding limitations; see docs/SCHOOL_UPDATE.md. Historical childcare metrics above do not measure this expanded scope.

Live address matching: 24 automated tests pass. Official-form checks succeeded for two public school addresses and one invalid civic number. See docs/ADDRESS_MATCHING.md. The app now displays board lookup results; no school-year-specific assignment or admission guarantee is inferred.
