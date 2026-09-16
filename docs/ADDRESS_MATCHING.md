# Live official address matching

The app submits a street number and canonical street name to the same public TDSB form used by the [official address finder](https://www.tdsb.on.ca/Find-your/School/By-Home-Address). It displays the returned school records, contact details, attendance-area links and board notes. This uses the board's address lookup, rather than estimating attendance from distance or approximate map polygons.

## Scope and authority

The board labels this lookup for **regular programs**. It does not expose a school-year selector. Results are attributed to TDSB with the retrieval timestamp, the user's requested grade/year and `year_verified: false`. The app never claims a future school-year assignment is verified or that a lookup guarantees admission. French Immersion and specialized-program requests receive guidance to the board process without submitting a regular-program search.

Schools beyond the two pilot profiles are displayed directly from the official response. All returned schools are included and initially selected in Explore or compare schools. Known school codes reuse reviewed profiles; additional schools receive session-only lookup profiles. Grade mismatches are labelled rather than removing options. Records with other explicit grade ranges remain visible and are labelled accordingly. When the board supplies no numeric grade range, the app does not infer one from the school name or level. Multiple results and footnotes are retained.

## Address handling

- Fetch the current official street list and form tokens on each explicit search.
- Match street names exactly after normalizing common street-type/direction abbreviations. For example, Joyce Parkway and Joyce Pky map to the board's Joyce Pkwy.
- Treat Toronto as the city-wide designation; use more specific municipalities to disambiguate. Unsupported municipality text is rejected, not silently ignored.
- Present a choice if more than one official street matches; do not choose the first or a fuzzy nearest match.
- Submit the civic number and selected canonical street to TDSB. Clearly distinguish an unknown street, a board no-match response and a network/parser failure.
- Preserve civic-number letter suffixes. Omit apartment details; ambiguous bare unit-number/civic-number ranges are rejected with input guidance.

No entered home address or search response is written to disk, included in embeddings, sent to Nebius, or cached across sessions. The form explicitly discloses that the address is sent to TDSB. Requests use an ephemeral cookie jar, timeouts, response-size limits and sanitized errors. Result links are restricted to the official TDSB HTTPS host. Display state is cleared when a new lookup begins or grade/year/program changes.

## Operational limits

This is an adapter to a public HTML form, **not a documented/versioned TDSB API**. Layout or access-policy changes may break it; unexpected or empty markup fails closed to the official finder link. It fetches data on demand rather than keeping a dated local boundary dataset. No bulk crawling or private-address testing was performed. Exact address support should be evaluated across a broader set of authorized test addresses before deployment.

## Validation — September 12, 2026

Live tests use public school addresses, not the user's home:

| Query | Board outcome |
| --- | --- |
| 26 Joyce Parkway, Toronto | Joyce Public School; Lawrence Heights Middle School; John Polanyi Collegiate Institute |
| 101 Englemount Avenue, North York | Glen Park Public School; Lawrence Heights Middle School; Ledbury Park Elementary and Middle School; John Polanyi Collegiate Institute |
| 99999 Joyce Parkway, North York | No result |

These validate the transport and parsing, not residency or admission eligibility. In particular, additional returned schools should be interpreted together with board notes and confirmed grade ranges.

The public Joyce-result HTML section is stored as a parser fixture without the full page's cookies, hidden form tokens or personal addresses. Automated tests exercise canonicalization, ambiguity, unsupported programs, grade ranges, unknown years, no matches, unexpected markup, external-link rejection, municipal mismatches, UI persistence and invalidation. The complete suite passes 24 tests.

Comparison update: all returned schools can now be selected, rendered and used in source-backed chat. New profile evidence contains only public school details, not the searched residential address. Missing reviewed details remain unknown. Tests cover mixed selections, context changes, deduplication and dynamic-school retrieval.
