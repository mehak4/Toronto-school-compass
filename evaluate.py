"""Run cases and summarize human-reviewed grounding metrics."""
import argparse
import json
import time
from pathlib import Path
from core import ROOT, route_question


def summarize(rows):
    def ratio(numerator, denominator):
        pairs = [(r.get(numerator), r.get(denominator)) for r in rows]
        pairs = [(n, d) for n, d in pairs if n is not None and d is not None]
        for n, d in pairs:
            if not isinstance(n, int) or not isinstance(d, int) or not 0 <= n <= d:
                raise ValueError(f'Invalid counts for {numerator}/{denominator}')
        total = sum(d for _, d in pairs)
        return {'reviewed_cases': len(pairs), 'percent': round(100 * sum(n for n, _ in pairs) / total, 2) if total else None}

    timed = [r for r in rows if r.get('seconds') is not None]
    return {
        'cases': len(rows),
        'route_passes': sum(bool(r.get('route_pass')) for r in rows),
        'faithfulness': ratio('supported_claims', 'total_claims'),
        'retrieval_precision': ratio('retrieval_relevant', 'retrieved_chunks'),
        'citation_support': ratio('supporting_citations', 'total_citations'),
        'successful_under_10_seconds_percent': round(100 * sum('error' not in r and r['seconds'] < 10 for r in timed) / len(timed), 2) if timed else None,
        'timed_cases': len(timed),
        'errors': sum('error' in r for r in rows),
    }


def run_cases(live=False, cases_path=None):
    workflow = None
    if live:
        from graph import build_graph
        workflow = build_graph()
    results = []
    for case in json.loads((cases_path or ROOT / 'data/evaluation_cases.json').read_text()):
        row = {**case, 'route_pass': route_question(case['question']) == case['route'],
               'supported_claims': None, 'total_claims': None,
               'retrieval_relevant': None, 'retrieved_chunks': None,
               'supporting_citations': None, 'total_citations': None,
               'fallback_correct': None, 'human_notes': 'Not yet evaluated'}
        if workflow is not None:
            start = time.perf_counter()
            try:
                row['result'] = workflow.invoke({'question': case['question'], 'school_ids': ['joyce', 'glenpark'], **case.get('context', {})})
                row['retrieved_chunks'] = len(row['result'].get('evidence', []))
            except Exception:
                row['error'] = 'Request failed; inspect local configuration.'
            row['seconds'] = round(time.perf_counter() - start, 3)
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true', help='Run configured models; may incur model charges')
    mode.add_argument('--summarize', type=Path, help='Summarize reviewed results without model calls')
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation-results.json')
    parser.add_argument('--cases', type=Path, help='Use a separate evaluation question set')
    args = parser.parse_args()
    if args.summarize:
        results = json.loads(args.summarize.read_text())
    else:
        if args.output.exists():
            parser.error('Output already exists; use --output with a new filename to preserve previous runs and reviews.')
        results = run_cases(args.live, args.cases)
        args.output.write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(summarize(results), indent=2))
    print('Null metrics are unmeasured. Grounding and citation support require human evidence review.')


if __name__ == '__main__':
    main()
