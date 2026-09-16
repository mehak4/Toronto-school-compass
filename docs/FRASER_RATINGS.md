# Verified Fraser ratings

Verified September 12, 2026 by reading and visually inspecting the publisher's PDF tables. The earlier web-text search missed Joyce, but local PDF extraction and page inspection found its row. Secondary real-estate listings were not used.

| TDSB school code | School | Score / 10 | Assessment year | Report edition | PDF page / printed page |
| --- | --- | --- | --- | --- | --- |
| 3182 | Joyce Public School | 7.7 | 2023–24 | Elementary 2025 | 17 / 15 |
| 3138 | Glen Park Public School | 5.1 | 2023–24 | Elementary 2025 | 31 / 29 |
| 3189 | Ledbury Park Elementary and Middle School | 7.6 | 2023–24 | Elementary 2025 | 17 / 15 |
| 3437 | John Polanyi Collegiate Institute | 4.4 | 2023–24 | Secondary 2025 | 18 / 16 |
| 5257 | Ogden Junior Public School | 6.8 | 2023–24 | Elementary 2025 | 21 / 19 |
| 5273 | Ryerson Community School | 4.1 | 2023–24 | Elementary 2025 | 34 / 32 |
| 5510 | Harbord Collegiate Institute | 7.5 | 2023–24 | Secondary 2025 | 13 / 11 |

Sources: [elementary report](https://www.compareschoolrankings.org/pdf/ontario-elementary-school-rankings-2025.pdf), [secondary report](https://www.compareschoolrankings.org/pdf/ontario-secondary-school-rankings-2025.pdf).

These are the 2023/2024 **overall rating** values, not the separate five-year-average column or provincial rank. Report edition, assessment year, and the app's verification date are distinct. The elementary 2025 edition was published in January 2026.

Mappings use the report name and municipality plus the established TDSB school identifiers. Ledbury's identity is also supported by its [official board profile](https://www.tdsb.on.ca/MOSS/asp_apps/school_landing_page/pdfs/web/3189_4pageLayout.pdf). These seven reviewed overrides take precedence; a conflicting name on one of these codes receives no score. Other TDSB schools can use the automatic matching described below. Unknown schools, including Lawrence Heights in the current mapping, are not assigned zero or another school's score.

Cards and chat use the same rating resolver. Each score links to its report page. There is no live scraping on page load. Fraser ratings are third-party academic indicators, not official TDSB ratings or a complete assessment of school quality. Elementary and secondary reports measure different grade levels, so these scores should not be presented as a cross-level league table. The ratings tab and rating answers now show Fraser only. The Toronto Ryerson row was verified separately from schools with the same name in London and Burlington.

Validation: tests cover exact school identity, unknown schools, assessment-year provenance, dynamic matched schools, UI metrics and deterministic chat. The catalog tests also cover report counts, reviewed-score parity, cross-level names, missing municipalities and ambiguous matches.


## Full report import

`data/fraser_catalog.json` contains 3,052 elementary and 747 secondary report rows from the linked 2025 editions (assessment year 2023–24). These are Ontario-wide records, not 3,799 TDSB schools. Each row retains its municipality, level, rank, source URL and PDF page. Report SHA-256 hashes are included. The elementary Nouveau Regard - Pavillon St-Joseph row on PDF page 37 has a blank current score and shifted city in the published table; the importer explicitly preserves a null score rather than substituting its five-year value.

For schools without a reviewed override, the resolver requires a TDSB profile URL, a known elementary or secondary grade range, and a unique exact normalized name and municipality match. Only terminal institution labels and punctuation/accents are normalized. Toronto boroughs are not silently treated as interchangeable. Cards identify automatic matches separately from reviewed mappings. Missing rows, unrecognized names, missing grade/city information, duplicate candidates and null scores remain unavailable. Some cases still need reviewed mappings; absence is never treated as a zero.

To reproduce the import, download the two linked publisher PDFs, then run:

```sh
.venv/bin/python -m pip install -r requirements-import.txt
.venv/bin/python scripts/import_fraser.py --elementary-pdf /path/to/ontario-elementary-school-rankings-2025.pdf --secondary-pdf /path/to/ontario-secondary-school-rankings-2025.pdf
```

The importer checks row totals, score order/ranges, competition ranks and all seven reviewed mappings before atomically replacing the catalog. It supports this specific 2025 layout; a later edition requires updating and validating the parser, expected counts and assessment year. Refresh when a new report is adopted, not per address search. The app reads the committed catalog locally without API keys, PDF dependencies or a vector reindex.
