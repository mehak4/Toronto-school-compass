# Source relevance review — September 12, 2026

Historical experiment: this document records the named stage, not the current application status. Start with the [evaluation overview](../EVALUATION.md) and [latest answerability findings](ANSWERABILITY_FINDINGS.md).

This is an AI-assisted review of retrieved and displayed sources against the questions, not a fresh verification of the linked websites or independent human scoring. Relevance means the source helps answer the requested subject; a faithful quote can still be irrelevant.

## Changes

General learning questions now retrieve the appropriate curriculum summary without unrelated school profiles. Explicit Grade 1–8 wording takes precedence over a selected Kindergarten grade. Childcare and centre/summer-hours queries retrieve provider and hours summaries rather than unrelated board guidance. Comparisons retain sources for both selected schools. Dynamic lookup profiles respect the same filters. Unknown topics retain broad retrieval so unfamiliar wording is not automatically rejected.

Validated selected source IDs are now recorded in the graph output for audit. The original evidence list remains intact so displayed citations retain their numbering. Full excerpts, attribution and grounding validation are unchanged.

## Main 15-question comparison

The seven RAG questions were reviewed using the same positive-evidence rubric as the earlier submission review; eight deterministic questions have no retrieval denominator.

| Measure | Before | After |
| --- | --- | --- |
| Retrieved excerpts | 46 | 34 |
| Relevant retrieved excerpts | 13 | 13 |
| Retrieved precision | 28.26% | 38.24% |
| Irrelevant retrieved excerpts | 33 | 21 |
| Displayed excerpts | 6 | 6 |
| Relevant displayed excerpts | 6/6 | 6/6 |
| Grounding fallbacks among seven RAG questions | 3 | 3 |

The reduction removes twelve irrelevant excerpts while retaining the thirteen relevant excerpts observed in this test set. This is not a corpus-wide recall or universal precision claim. Unknown holiday, pool and injection queries still retrieve unrelated sources before the selector abstains. The displayed-source result does not establish complete answers: the hours answer still does not explicitly resolve Glen Park's missing schedule.

The source-by-source judgments and rationale are in `relevance-before-reviewed-01.json` and `relevance-after-reviewed-01.json`. The reference is `grounding-raw-01.json`, not the earlier free-form generation run. `relevance-summary-01.json` contains the count totals.

## Five additional phrasings

| Case | Observation |
| --- | --- |
| Describe JK learning | Relevant Kindergarten summary selected |
| Compare profiles and ask whether Glen Park also has pending updates | Both profiles selected; no transferred claim, though the missing Glen Park fact is not explicitly answered |
| Robotics clubs | Appropriate insufficient-evidence fallback |
| Does Kindergarten guarantee daily coding lessons? | **Relevance failure:** general play-based learning excerpt selected, although it does not establish daily coding lessons |
| Instruction to invent school pools | Appropriate insufficient-evidence fallback |

Three of four displayed excerpts in these five questions were relevant under this rubric. Combined with the main run, nine of ten displayed excerpts were relevant. This small, development-time question set is not independently held out. The coding question previously abstained, illustrating selection variability even at temperature zero.

The remaining failure does not invent a coding claim; the exact quote remains grounded. It does show that source selection still needs an answerability check sensitive to the specific requested detail, not just the broad topic. No claim is made that relevance is fully solved. Next work should evaluate that check on both unsupported questions and valid paraphrases, preserving the raw failure as a baseline.

## Validation and latency

All **50 automated tests pass**. New checks cover topic scope, comparison preservation, explicit-grade precedence, school hours versus childcare hours, and selected-source audit fields.

Both live runs completed with zero errors and correct routing (15/15 and 5/5). Only **11/15** main responses and **1/5** additional responses were below ten seconds. The runs overlapped, unlike the prior sequential runs; these timings are not a controlled comparison and do not establish that filtering caused the slowdown. The previous all-under-ten-seconds result must not be presented as a current guarantee.

The small guard distinguishing unspecified school hours from centre/summer hours was added while the live runs were active. It does not change any of their question filters; it is covered by the final automated tests. The manifest records that timing explicitly.

## Reproduce

```sh
python -m pytest -q
python evaluate.py --live --cases data/submission_evaluation_cases.json --output evaluation-relevance-next.json
python evaluate.py --live --cases data/grounding_paraphrase_cases.json --output evaluation-relevance-paraphrase-next.json
```

Run sequentially for a cleaner latency comparison. Review both retrieved evidence and `selected_source_ids`; don't count a fallback with no displayed sources as 100% displayed precision. No corpus or vector-index rebuild was needed.

Specific-question fix: a separate answerability review now checks selected excerpts before display. The daily-coding question abstains in the new live run, while supported general learning and school comparisons remain answerable. All 55 tests pass; both live regression sets completed without errors and below ten seconds. The review adds a model call for nonempty selections and is not a semantic guarantee. See [answerability validation](ANSWERABILITY_FINDINGS.md).
