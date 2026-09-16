# Evaluation overview and review rubric

Current implementation: extractive answers with topic-filtered retrieval, validated model source selection and a separate answerability review. Status recorded September 12, 2026. This page is the entry point for evaluation evidence; raw historical files remain unchanged.

## Latest validation

| Measure | Latest recorded result | Limit |
| --- | --- | --- |
| Automated tests | 55 passed | Includes mocked-model integration, not live semantic correctness |
| Main live cases | 15/15 correct routes, zero request errors | Routing is not faithfulness |
| Additional phrasings | 5/5 correct routes, zero request errors | Written during development, not independently held out |
| Latency | All 20 responses below ten seconds in two sequential runs | Previous runs were slower; no service guarantee |
| Specific coding-lessons question | Insufficient-evidence fallback | Model review may still make errors on other questions |
| Independent claim faithfulness and citation support | Unmeasured | Do not claim the 95% faithfulness target was met |

The main run contains eight deterministic questions and seven RAG questions. Four RAG questions returned excerpts and three abstained. The additional set retained broad learning, returned Joyce's profile for a leading update-pending comparison, and abstained on robotics, daily coding and pool invention. The leading comparison remains incomplete about Glen Park's missing detail. A fallback is not a substantive answer, and a correct quotation need not answer the entire question.

Use [answerability findings](evaluation/ANSWERABILITY_FINDINGS.md), [main raw results](evaluation/answerability-raw-01.json), [additional raw results](evaluation/answerability-paraphrase-raw-01.json), [main summary](evaluation/answerability-summary-01.json), [additional summary](evaluation/answerability-paraphrase-summary-01.json) and [manifest](evaluation/answerability-manifest-01.json). Observations are AI-assisted; independent review is pending. These runs did not recheck the live address form or refresh source pages.

## Experiment history

| Stage | What it establishes | Artifact |
| --- | --- | --- |
| Initial childcare prototype | Historical 92.65% supported claim units in provisional AI review; not current faithfulness | [Historical findings](evaluation/FINDINGS.md) |
| Expanded school corpus | Early school-generation failures and retrieval iterations | [Historical school notes](SCHOOL_UPDATE.md) |
| Submission baseline | Fifteen current-topic questions exposed unsupported generated details; 80% under ten seconds | [Baseline findings](evaluation/SUBMISSION_FINDINGS.md) |
| Extractive grounding | Original source excerpts prevented unsupported free-form prose in tested cases | [Grounding findings](evaluation/GROUNDING_FINDINGS.md) |
| Topic relevance filtering | Relevant retrieved excerpts retained (13); irrelevant excerpts reduced 33 → 21; daily-coding relevance failure found | [Relevance findings](evaluation/RELEVANCE_FINDINGS.md) |
| Answerability review — current | Specific daily-coding case abstains; supported general questions remain answerable | [Latest findings](evaluation/ANSWERABILITY_FINDINGS.md) |

`revised-reviewed.json`, `revised-raw.json` and `revised-schools.json` belong to the initial childcare experiment. `relevance-paraphrase-reviewed-01.json` documents the intermediate relevance failure before answerability review. They are preserved evidence, not files to rewrite with the latest results. The relevance experiment's 38.24% retrieval precision and nine-of-ten relevant displayed excerpts are stage-specific AI judgments, not fresh final-version quality scores.

## Reproduce or review

Run from the project root after configuring the local environment and index. New live runs use provider credits; run sequentially for cleaner timing comparisons and use a fresh output name to preserve prior results.

```sh
python -m pytest -q
python evaluate.py --live --cases data/submission_evaluation_cases.json --output evaluation-final-next.json
python evaluate.py --live --cases data/grounding_paraphrase_cases.json --output evaluation-final-paraphrase-next.json
python evaluate.py --summarize docs/evaluation/answerability-raw-01.json
```

To score quality, copy a raw run to a new reviewed file and assess every answer against its evidence (and stored source records for deterministic paths). Record judgments using the fields below, then summarize that reviewed copy. Preserve null for unmeasured metrics. Missing-index responses and API fallbacks are not successful grounded answers.

Review retrieved-source relevance separately from displayed-source relevance. The latter uses `result.selected_source_ids` to identify passages actually displayed. Record whether the answer addresses the specific requested detail, covers both schools when appropriate, preserves dates and caveats, or correctly abstains. A zero-source fallback has no precision denominator; do not label it 100% precision.

| Field | Scoring rule |
| --- | --- |
| `total_claims` | Count independently checkable factual claims in the answer. Use zero for an answer with no factual claims. |
| `supported_claims` | Count claims entailed by evidence; wrong dates, invented fees or conflated centre/session hours are unsupported. |
| `retrieved_chunks` | Automatically populated count of returned chunks; zero for deterministic answers. |
| `retrieval_relevant` | Count chunks useful to answering the particular question; an unrelated board chunk is not automatically relevant. |
| `total_citations` | Count citation occurrences, including directory source links where applicable. |
| `supporting_citations` | Count citations whose linked evidence supports the associated claim. Numeric validity alone is insufficient. |
| `fallback_correct` | Enter true/false based on whether the answer appropriately handles missing information or verification needs; leave null when not applicable. |
| `human_notes` | Explain failures, missing evidence and whether expected behavior was met. |

Faithfulness = supported claims / total claims. Retrieval precision = relevant chunks / retrieved chunks. Citation support = supporting citations / total citations. These are aggregate count-weighted metrics over reviewed cases; missing reviews and zero denominators remain unmeasured. Review all cases before comparing against the 95% faithfulness target.
