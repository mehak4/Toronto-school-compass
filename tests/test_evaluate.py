import json
import subprocess
import sys
import pytest
from core import ROOT
from evaluate import run_cases, summarize


def test_offline_results_do_not_claim_quality():
    rows = run_cases()
    metrics = summarize(rows)
    assert metrics['cases'] == metrics['route_passes'] == 15
    assert metrics['faithfulness'] == {'reviewed_cases': 0, 'percent': None}
    assert metrics['successful_under_10_seconds_percent'] is None
    assert all('result' not in row for row in rows)


def test_reviewed_metrics_are_weighted_and_include_failed_timings():
    rows = [
        {'supported_claims': 1, 'total_claims': 2, 'seconds': 2},
        {'supported_claims': 8, 'total_claims': 8, 'seconds': 11},
        {'seconds': 1, 'error': 'Failed'},
    ]
    metrics = summarize(rows)
    assert metrics['faithfulness'] == {'reviewed_cases': 2, 'percent': 90}
    assert metrics['successful_under_10_seconds_percent'] == 33.33
    assert metrics['errors'] == 1
    with pytest.raises(ValueError):
        summarize([{'supported_claims': 3, 'total_claims': 2}])
    assert summarize([{'supported_claims': 0, 'total_claims': 0}])['faithfulness']['percent'] is None


def test_cli_preserves_existing_reviews(tmp_path):
    output = tmp_path / 'results.json'
    command = [sys.executable, str(ROOT / 'evaluate.py'), '--output', str(output)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    original = output.read_text()
    assert len(json.loads(original)) == 15
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode != 0
    assert output.read_text() == original
    review = subprocess.run([sys.executable, str(ROOT / 'evaluate.py'), '--summarize', str(output)], capture_output=True, text=True)
    assert review.returncode == 0, review.stderr
    assert '"percent": null' in review.stdout
