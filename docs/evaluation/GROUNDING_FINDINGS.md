# Grounding repair — September 12, 2026

Historical experiment: this document records the named stage, not the current application status. Start with the [evaluation overview](../EVALUATION.md) and [latest answerability findings](ANSWERABILITY_FINDINGS.md).

The previous run showed that free-form answers added developmental skills absent from the Kindergarten summary and applied Joyce's update-pending limitation to Glen Park. Tightening prompts had not reliably prevented this.

## Change

The model now selects up to four numbered evidence sources in strict JSON. The app rejects malformed selections, extra fields, duplicates, non-integer IDs and IDs outside the retrieved evidence. It renders only the original source excerpts under their own titles and review dates. Whole excerpts retain dates, school attribution, centre/session distinctions and other caveats. Model-written factual prose is never displayed. Empty selections return an insufficient-evidence message.

This is an extractive RAG answer: retrieval and model-based evidence selection still run, while answer composition uses source text rather than a generated paraphrase. It is not a semantic entailment classifier or a guarantee of source accuracy/relevance. The tradeoff is less conversational wording and sometimes additional context in a full excerpt.

## Validation

- All **48 automated tests pass**, including rejection of fabricated prose with valid-looking citations, injected extra answer fields, bad source IDs and invalid schemas. Regression tests preserve school attribution and prevent adding unsupported developmental claims.
- The same **15 current-scope questions** had correct routing, no request errors, and all responses below ten seconds. The seven RAG requests ranged from **1.391 to 4.197 seconds**; four returned excerpts and three returned grounding fallbacks. Previously only 12/15 responses were below ten seconds.
- Five additional phrasings also completed without errors and below ten seconds. These were written during the repair and are not an independently held-out benchmark.

AI inspection of the saved outputs found:

| Question area | Result |
| --- | --- |
| Kindergarten learning | Only the supplied inquiry/play-based learning sentence is shown; no invented skills or future-year guarantee |
| School comparison | Joyce and Glen Park excerpts stay separate; Joyce's update-pending note is not attributed to Glen Park |
| Childcare hours | Source's undated-page caveat and centre/session distinction are retained |
| Childcare comparison | Both provider excerpts retain their original vacancy dates and CWELCC limitations |
| Holiday schedule, invented tuition and pool | Insufficient-evidence fallback, with no fabricated facts |
| Additional JK paraphrase | Same supported Kindergarten excerpt |
| Leading question about Glen Park updates | Separate source profiles, no claim that Glen Park has update-pending sections |
| Robotics, guaranteed daily coding, pool-invention instruction | Insufficient-evidence fallback |

No independent claim-faithfulness percentage is claimed. Source excerpts can contain stale or incorrect information, selection can omit a school or choose irrelevant material, and quoting is not proof of answering the whole question. For example, the hours answer supplies Rejoyce's available hours without explicitly resolving Glen Park's missing schedule. Retrieval itself is unchanged, so the earlier retrieval-precision problem is not claimed solved. Deterministic registration, address, rating and vacancy paths are unchanged.

## Artifacts and reproduction

- `grounding-raw-01.json`: original 15 questions, results, retrieved evidence and timing.
- `grounding-paraphrase-raw-01.json`: five additional phrasings.
- `grounding-summary-01.json` and `grounding-paraphrase-summary-01.json`: computed summaries; human-review metrics remain null.
- `grounding-manifest-01.json`: tested model IDs and code/data/output hashes, without credentials.

```sh
python -m pytest -q
python evaluate.py --live --cases data/submission_evaluation_cases.json --output evaluation-grounding-next.json
python evaluate.py --live --cases data/grounding_paraphrase_cases.json --output evaluation-grounding-paraphrase-next.json
```

Use new output filenames; live runs consume configured provider credits. No vector reindex is required for this code-only grounding change.
