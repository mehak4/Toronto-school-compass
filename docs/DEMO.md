# Demo and submission guide

## Demo script — target 4 minutes 30 seconds

- **0:00–0:30:** Explain Toronto School Compass, the parent audience, eleven curated official-source summaries and the custom Python/LangGraph track.
- **0:30–1:15:** Show curriculum and registration tabs. Change grade/year, distinguish the September 2027 French application window from unknown other-year dates, then show Fraser-only scores with assessment year and publisher page links.
- **1:15–1:55:** Demonstrate the TDSB address form using a public school address such as 26 Joyce Parkway, North York. Explain that these are current regular-program results, all returned schools appear in Explore, and the requested school year is not verified. Never use a private home address in the recording.
- **1:55–2:45:** Ask a curriculum question and expand its retrieved evidence. Compare the answer with the summary: explain that the app now renders original excerpts to prevent unsupported model paraphrases. Ask “Does the Kindergarten curriculum guarantee daily coding lessons?” to demonstrate the answerability fallback; exact model behavior can vary.
- **2:45–3:30:** Explain JSON → splitter → embeddings → Chroma → source selection → answerability check → cited excerpts. Distinguish the structured Fraser import and official address adapter from RAG.
- **3:30–4:00:** Show the latest results in [the evaluation overview](EVALUATION.md): 55 automated tests, 15 main questions plus five additional phrasings, no request errors and all below ten seconds in the latest sequential runs. Explain that independent faithfulness scoring is pending and latency varied in earlier runs.
- **4:00–4:30:** Describe how AI coding assistance helped implement, debug, test and document the project, along with your own design decisions and review. Explain the tradeoff: original excerpts preserve grounding, but model-based answerability can still omit information or choose poorly and adds a request.

## Before recording

Start Streamlit with the configured local environment and existing index. Keep `.env`, terminals with credentials and private browser tabs out of the recording. Test the chosen public address in advance; if TDSB is unavailable, disclose that and show the error path. A fabricated address should demonstrate an unknown-address path, not a successful match.

## Submission checklist

- [x] Working local app and model configuration.
- [x] Current 15-question live run, saved evidence and AI-assisted failure analysis.
- [x] Current project report and assignment audit prepared locally.
- [ ] Independently review claim support and disclose or fix remaining failures.
- [ ] Copy `PROJECT_REPORT.md` and current evaluation findings into the required Google Doc; check sharing access.
- [ ] Record a video of five minutes or less and obtain its shareable link.
- [ ] Publish reviewed project assets on GitHub; verify no `.env`, local caches or private inputs are included.
- [ ] Review and submit the Google Doc, video and repository links using the handout's submission form.

No external document, recording, repository publication or submission has been completed by preparing these local files.
