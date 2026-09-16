# Specific-question answerability check

The daily-coding question exposed a difference between faithful quotation and answering a question: a general Kindergarten learning excerpt is accurate but does not establish a daily coding guarantee.

## Implementation

After evidence selection passes structural validation, a separate model call reviews only the selected passages against the question. It must return a subset of the supplied source IDs. For specific yes/no claims, the passage must address the requested activity, property, frequency or guarantee; a shared topic is insufficient and silence is not evidence of absence. Broad descriptive questions may use semantic paraphrases without exact keyword matching.

The app rejects malformed responses and newly introduced source IDs. Empty reviews and reviewer request failures produce the existing insufficient-evidence fallback. Only validated source excerpts reach the user. This preserves the extractive grounding guarantee while adding a model-based answerability check; it is not a deterministic proof of semantic relevance.

## Automated validation

All 55 tests pass. Added regressions force the selector to choose general Kindergarten evidence for the coding question, then verify that rejection, malformed review, out-of-scope IDs and provider failure cannot display it. A supported learning paraphrase remains answerable. Existing comparison, source attribution and citation validation tests still pass.

## Live regression

`answerability-paraphrase-raw-01.json` preserves the five additional questions. The daily-coding question now returns an insufficient-evidence fallback, as do robotics and the pool-invention instruction. Broad JK learning still returns the supported learning excerpt. The leading comparison about pending updates selects Joyce's profile without attributing that limitation to Glen Park; it does not fully resolve the missing Glen Park detail. All five requests completed without errors and below ten seconds.

`answerability-raw-01.json` records the separate 15-question regression run. These are sequential development-time runs, not an independent benchmark. See the paired summary JSON files for timing and routing metrics; human claim-level scores remain unmeasured.

The repair adds one model request when the initial selection is nonempty. It can increase latency and cost, or reject useful passages. It does not refresh source content or eliminate every possible selection error. Independent review remains appropriate.

The main run had 15/15 correct routes, zero request errors and all responses below ten seconds. Its four supported RAG questions retained excerpts; its three unsupported/injection questions abstained. Model-backed timings ranged from 1.317 to 5.385 seconds. This one run is not a latency guarantee.
