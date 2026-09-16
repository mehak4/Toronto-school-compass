# Curriculum, registration and school results update

Historical snapshot: implementation details and test counts below describe earlier iterations. For the current app, see [project report](PROJECT_REPORT.md) and [evaluation overview](EVALUATION.md). Fraser scores now use the full report import and the app displays Fraser only.

The app now leads with three school tabs: Curriculum & programs, Registration dates, and Ratings & results. Childcare details are in an optional expander; fee labels and monthly estimates have been removed from the interface. Public-school tuition and optional childcare charges are different topics; the old missing-childcare-fee safeguard remains available for explicit questions.

## What is implemented

- Reviewed profiles for Joyce and Glen Park list JK–6 and school-office phone numbers. A Grade 7/8 selection displays a grade-range warning.
- Kindergarten selections show TDSB learning guidance; Grades 1–8 show a provincial curriculum overview. School-specific profile details are distinguished from shared curriculum.
- Grade and school year drive registration guidance. English Kindergarten has a published January start month, with exact dates confirmed locally. The November 2–27, 2026 Early French Immersion window is tied only to September 2027 JK entry. Unknown deadlines are stated explicitly.
- Rating questions use deterministic guidance linking EQAO results and the third-party Fraser report. School-specific numeric scores are not verified and are not displayed. School-level Fraser data could not be accessed through the research tool; secondary real-estate scores were not treated as verified ratings.
- Curriculum and school-program retrieval is restricted to school profiles and the relevant learning summary, preventing childcare hours and CWELCC information from dominating school answers. Explicit childcare queries retain the existing retrieval path.
- The address heuristic now recognizes one-digit street addresses and avoids treating every year followed by a word as an address.

## Reviewed sources — September 12, 2026

- [TDSB Kindergarten](https://www.tdsb.on.ca/EarlyYears/Kindergarten): learning approach, English registration start month and entry-year-specific French application dates. Some individual school pages still mention February; the app uses the central board page and tells families to confirm exact local dates.
- [Ontario assessment and curriculum guidance](https://www.ontario.ca/page/student-assessment-evaluations-and-report-cards): curriculum expectations and elementary subject examples.
- [Joyce board profile](https://www.tdsb.on.ca/DesktopModules/Tdsb.Webteam.Modules.SPC/schoolprofile.aspx?schno=3182): grade range, office number and profile limitations.
- [Glen Park board profile](https://www.tdsb.on.ca/DesktopModules/Tdsb.Webteam.Modules.SPC/schoolprofile.aspx?schno=3138): grade range, office number and French/English technology-supported programming.
- [EQAO school lookup](https://www.eqao.com/the-assessments/find-my-school/): official school results lookup.
- [Fraser 2025 elementary report](https://www.fraserinstitute.org/studies/report-card-ontarios-elementary-schools-2025): publisher's report description, published January 8, 2026; no school-specific numeric scores imported.

## Validation and limits

All 18 automated tests pass, including grade/year switching, two-school rendering, registration-year isolation, unknown ratings, address routing and curriculum retrieval scope. The expanded corpus contains eleven summaries indexed as eleven chunks. This remains a curated seed dataset.

The first eight-question live run completed without API errors but showed unsupported Kindergarten elaboration and a school-comparison answer importing childcare hours across schools. Retrieval was then restricted by subject and grade, and the prompt tightened. Both raw runs are preserved in `evaluation/school-baseline-raw.json` and `evaluation/school-revised-raw.json`.

The old 15-case childcare quality percentages are historical. No new faithfulness percentage is claimed for this expanded scope. Human review of the school answers and numeric school-level rating verification remain outstanding.

The revised eight-case run had zero API errors and all responses under 10 seconds (model-backed cases: 3.958 and 4.856 seconds). AI inspection confirmed that the comparison no longer imported childcare hours, but the Kindergarten answer still added developmental skills absent from the seed summary, and the comparison incorrectly generalized Joyce’s update-pending limitation to both profiles. These two generated answers need further grounding work; the deterministic cards, date guidance and rating fallbacks are not affected. No claim is made that all eight answers passed semantic review.
