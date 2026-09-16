import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import fee_label, estimate_month, route_question, directory, address_status, ROOT

def test_missing_fee_not_free():
    assert 'not published' in fee_label({'amount': None})
    assert estimate_month({'amount':None},20) is None

def test_fee_requires_provenance():
    assert 'Incomplete' in fee_label({'amount':10,'unit':'day'})
    fee = {'amount':20, 'unit':'day', 'source_url':'https://example.invalid/rates',
           'effective_date':'2026-09-01'}
    for field in ('source_url', 'effective_date'):
        incomplete = {key: value for key, value in fee.items() if key != field}
        assert 'Incomplete' in fee_label(incomplete)
        assert estimate_month(incomplete, 20) is None

def test_estimate_units():
    fee = {'amount':20, 'unit':'day', 'source_url':'https://example.invalid/rates',
           'effective_date':'2026-09-01'}
    assert estimate_month(fee,20)==400
    assert estimate_month({**fee, 'amount':0},20)==0
    assert estimate_month({'amount':20,'unit':'week'},20) is None

def test_no_inferred_assignment():
    assert 'unverified' in address_status('123 Example Avenue, North York')
    assert 'Enter' in address_status('Toronto')

def test_routes():
    cases=json.loads((ROOT/'data/evaluation_cases.json').read_text())
    for c in cases:
        assert route_question(c['question'])==c['route'], c

def test_directory_missing_values():
    for school in directory():
        care=school['childcare']
        assert care['fee']['amount'] is None
        assert 'Contact provider' in care['vacancy_note']

def test_graph_no_model_for_sensitive_facts():
    from graph import build_graph
    for q in ['What is the cost?', 'Are there spaces?', 'Am I eligible?']:
        r=build_graph().invoke({'question':q,'school_ids':['joyce']})
        assert r['answer']
        assert r['evidence']==[]

def test_waitlist_is_explicitly_unknown():
    from graph import build_graph
    result = build_graph().invoke({'question': 'Is there a waitlist?', 'school_ids': ['joyce']})
    assert 'Waitlist status is not published' in result['answer']
    assert 'current availability' in result['answer']

def test_cited_undated_evidence_has_source_note(monkeypatch):
    import graph, provider
    monkeypatch.setattr(provider, 'verify_selection', lambda q,c: '{"source_ids": [1]}')
    monkeypatch.setattr(provider, 'generate', lambda q, c: '{"source_ids": [1]}')
    result = graph.answer({'question': 'Hours?', 'evidence': [
        {'title': 'Hours summary', 'checked_at': '2026-09-09', 'text': 'An undated school page lists hours.'}
    ]})
    assert 'Relevant source excerpts:' in result['answer']
    assert 'undated' in result['answer']
    assert 'An undated school page lists hours.' in result['answer']

def test_rag_integration_with_mock_provider(tmp_path,monkeypatch):
    import ingest, graph, provider
    monkeypatch.setattr(provider, 'verify_selection', lambda q,c: '{"source_ids": [1]}')
    (tmp_path/'data').mkdir()
    (tmp_path/'data/corpus.json').write_text((ROOT/'data/corpus.json').read_text())
    monkeypatch.setattr(ingest,'ROOT',tmp_path)
    monkeypatch.setattr(graph,'ROOT',tmp_path)
    monkeypatch.setenv('EMBEDDING_MODEL','test-model')
    monkeypatch.setenv('MODEL_BASE_URL','https://example.invalid')
    fake=lambda texts:[[1.0,0.0,0.5] for t in texts]
    monkeypatch.setattr(ingest,'embed',fake)
    monkeypatch.setattr(provider,'embed',fake)
    monkeypatch.setattr(provider,'generate',lambda q,c:'{"source_ids": [1]}')
    ingest.ingest()
    r=graph.build_graph().invoke({'question':'Compare childcare programs','school_ids':['joyce','glenpark']})
    assert {e['school_id'] for e in r['evidence']}=={'joyce','glenpark'}
    assert r['mode']=='RAG answer'
    monkeypatch.setattr(provider,'generate',lambda q,c:'Invented answer [999].')
    r=graph.build_graph().invoke({'question':'What are the hours?','school_ids':['joyce']})
    assert r['mode']=='Grounding fallback'
