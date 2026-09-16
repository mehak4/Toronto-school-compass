"""Import the fixed-layout 2025 Ontario Fraser reports; never guesses future layouts."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

SPECS = {'elementary': (38, 3052), 'secondary': (19, 747)}


def extract(path, level):
    import pymupdf  # Optional import dependency; not needed by the app.
    end, expected = SPECS[level]
    rows = []
    with pymupdf.open(path) as doc:
        if '2025' not in doc[0].get_text():
            raise ValueError('Expected the 2025 report')
        for page_index in range(11, end):
            words = doc[page_index].get_text('words')
            for offset in (0, 246):
                anchors = sorted((w for w in words if 79 < w[2]-offset < 82
                                  and w[1] > 100 and w[4].isdigit()), key=lambda w: w[1])
                for anchor in anchors:
                    aligned = sorted((w for w in words if abs(w[1]-anchor[1]) < 1), key=lambda w:w[0])
                    def field(left, right):
                        return ' '.join(w[4] for w in aligned if left <= w[0]-offset < right)
                    name, city, score = field(119, 216), field(216, 267), field(267, 284)
                    if not name or not city:
                        raise ValueError(f'Missing identity on page {page_index+1}')
                    # One published row has a shifted city and no current score.
                    if level == 'elementary' and page_index == 36 and name == 'Nouveau Regard - Pavillon St-Joseph':
                        city, score = field(250, 284), ''
                    score = float(score) if score else None
                    if score is not None and not 0 <= score <= 10:
                        raise ValueError('Score outside 0–10')
                    rows.append(dict(fraser_name=name, fraser_city=city, score=score, scale=10,
                                     rank=int(anchor[4]), school_level=level, assessment_year='2023–24',
                                     report_year=2025, pdf_page=page_index+1, printed_page=page_index-1,
                                     source_url=f'https://www.compareschoolrankings.org/pdf/ontario-{level}-school-rankings-2025.pdf',
                                     checked_at=date.today().isoformat()))
    if len(rows) != expected:
        raise ValueError(f'{level}: expected {expected} rows, found {len(rows)}')
    # Competition ranking verifies every score group, including ties and missing rows.
    previous_score = 11
    for i, row in enumerate(rows):
        if row['score'] is not None:
            if row['score'] > previous_score:
                raise ValueError('Scores are not in report order')
            previous_score = row['score']
        expected_rank = rows[i-1]['rank'] if i and row['rank'] == rows[i-1]['rank'] else i+1
        if row['rank'] != expected_rank:
            raise ValueError(f'Rank mismatch at row {i+1}')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for level in SPECS:
        parser.add_argument(f'--{level}-pdf', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1]/'data/fraser_catalog.json')
    args = parser.parse_args()
    rows, reports = [], []
    for level in SPECS:
        path = getattr(args, level+'_pdf')
        extracted = extract(path, level)
        rows.extend(extracted)
        reports.append(dict(level=level, count=len(extracted), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    overrides = json.loads((Path(__file__).resolve().parents[1]/'data/fraser_ratings.json').read_text())
    for known in overrides.values():
        matches = [r for r in rows if all(r[k] == known[k] for k in ('fraser_name','fraser_city','school_level','score','rank','pdf_page'))]
        if len(matches) != 1:
            raise ValueError(f"Reviewed mapping disagrees: {known['school_name']}")
    output = json.dumps(dict(reports=reports, ratings=rows), ensure_ascii=False, indent=2)+'\n'
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(output)
    temporary.replace(args.output)
    print('Imported '+', '.join(f"{r['count']} {r['level']}" for r in reports))


if __name__ == '__main__':
    main()
