# Validation — September 23, 2026

## Automated

The combined suite passes **82 tests**, including fifteen GTM tests. Coverage includes real ephemeral Chroma retrieval, full short-brief source coverage, review feedback reaching the next writer call, bounded revisions, citation checks overriding a reviewer pass, tool failure, approve/reject gating and the Streamlit generate/approve/new-run flow. Model responses in automated tests are scripted; they do not measure writing quality.

The 82-test development run includes twelve tests from a separate local document-agent prototype that is not part of this publication. The published school and GTM suites contain 70 tests; run `python -m pytest -q tests gtm_agent/tests` from the repository root, or run the fifteen GTM tests alone as documented in the README.

## Current reviewer validation

The current local campaign override is `GTM_CHAT_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507`. A live run with the revised writer/reviewer instructions reached `awaiting_approval`. Source inspection then softened the email phrase “so nothing falls through the cracks” to “in a shared workspace”; this AI-assisted editorial revision was logged, and the edited campaign passed another model review. The user subsequently reviewed this saved sample and explicitly approved it in project chat.

The approved sample is in `examples/approved_campaign.md` and `examples/approved_campaign.json`. All recorded hashes were verified before restoring the saved state at the LangGraph human-review step, pausing at its interrupt, and resuming with the user's actual approval. No new model calls were made; campaign text and evidence were verified identical to the reviewed JSON. This records a saved-state approval rather than a continuous browser session. The original `sample_campaign_draft.*` files remain unchanged as the pre-approval snapshots.

Two additional synthetic reviewer-only checks used fixed campaign text: a fitness brief without a price, launch date or URL was accepted; the same campaign with an unsupported weight-loss guarantee was blocked. Their complete inputs and results are in `examples/reviewer_checks.json`. These are narrow regression checks, not a success-rate benchmark or independent human evaluation.

The smaller 30B model still produced contradictory and unverifiable findings during calibration. Exact draft-quote validation stopped that run rather than accepting the review. The larger model also initially confused an unapproved free-trial claim with proof that no trial existed; explicit source-interpretation guidance was added before the current sample. Model review remains fallible, so human review is still required. Automated tests additionally cover quote repair, repeated invalid review failure, retained drafts on failure, valid-citation unsupported claims and the optional campaign-only model override.

The current `examples/validation_manifest.json` identifies model IDs, code/input/output hashes, approval provenance and approved export hashes. Earlier examples below document the development history and have been superseded by the current sample.

## Earlier live fictional samples

Two live runs used `examples/atlas_launch.docx` with the configured Nebius-compatible model and embedding endpoints. Both generated all four requested asset formats and executed the reviewer-to-writer loop up to the two-revision limit. Both ended `needs_changes`; neither was approved or exported through the approval gate.

The first run retrieved five of six source passages. A coverage safeguard was then added so the second retained all six passages, including explicit restrictions. The reviewer still raised inaccurate or overly broad objections: it demanded a URL even though the brief supplies none, and inconsistently interpreted pricing permissions. Some draft shortcomings also persisted, including omitted pricing. Planner strategy text introduced unsupported product ideas; this text is labelled as a proposal and is not passed to the writer as factual evidence.

Those earlier runs verified execution and failure containment, not an accepted final campaign, and motivated the later calibration and model change. No success rate, factual accuracy percentage or latency target is claimed from them.

The current review copy is provided in [sample_campaign_draft.md](examples/sample_campaign_draft.md) and [sample_campaign_draft.json](examples/sample_campaign_draft.json). All source content is fictional. Earlier raw runs remain ignored in `outputs/`.

The local Streamlit health endpoint returned `ok` on port 8502. VS Code and browser open commands completed successfully during development.

## Fitness source and empty-output regression

The combined suite now passes 78 tests. New checks cover pasted fitness details replacing the Atlas demo, visible provider errors, redacted credentials, fenced JSON responses and rejection of whitespace-only fields. A live diagnostic run used the reported goal with a fictional Move Journal fitness brief: all four assets were nonempty. Its review flagged an ads citation mismatch and exports remained blocked; the diagnostic run disabled rewrites to isolate initial generation. This demonstrates visible drafts, not an approved or independently verified campaign. The original browser-session failure was not captured, so its exact cause is not claimed known.
