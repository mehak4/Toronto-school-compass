import json
from pathlib import Path
from address_lookup import parse_results
from profiles import comparison_schools, includes_grade
from core import ROOT


def lookup_result():
    result = parse_results((Path(__file__).parent / 'fixtures/tdsb-public-school-result.html').read_text())
    result['checked_at'] = '2026-09-12T00:00:00+00:00'
    return result


def test_merge_deduplicates_known_schools_and_preserves_unknowns():
    schools = comparison_schools(lookup_result())
    assert [s['id'] for s in schools] == ['joyce','glenpark','tdsb-3190','tdsb-3437']
    assert schools[0]['childcare']
    assert schools[2]['childcare'] is None
    assert includes_grade(schools[2], '7') is None
    assert includes_grade(schools[3], 'JK') is False
    assert includes_grade(schools[3], '9') is True
    assert len(comparison_schools({'status':'not_found'})) == 2


def test_dynamic_school_facts_and_rag_use_selected_public_profile(tmp_path, monkeypatch):
    import graph, provider, ingest
    monkeypatch.setattr(provider, 'verify_selection', lambda q,c: '{"source_ids": [1]}')
    school = comparison_schools(lookup_result())[2]
    state = {'school_ids':[school['id']], 'school_records':[school]}
    result = graph.build_graph().invoke({**state, 'question':'What is its rating?'})
    assert school['name'] in result['answer']
    result = graph.build_graph().invoke({**state, 'question':'Are childcare spaces available?'})
    assert 'Childcare details have not been reviewed' in result['answer']
    (tmp_path/'data').mkdir()
    (tmp_path/'data/corpus.json').write_text((ROOT/'data/corpus.json').read_text())
    monkeypatch.setattr(graph,'ROOT',tmp_path)
    monkeypatch.setattr(ingest,'ROOT',tmp_path)
    monkeypatch.setenv('EMBEDDING_MODEL','test-model')
    monkeypatch.setenv('MODEL_BASE_URL','https://example.invalid')
    fake = lambda texts: [[1.0, 0.5, 0.0] for _ in texts]
    monkeypatch.setattr(provider,'embed',fake)
    monkeypatch.setattr(ingest,'embed',fake)
    contexts = []
    def generate(question, context):
        contexts.append(context)
        return '{"source_ids": [1]}'
    monkeypatch.setattr(provider,'generate',generate)
    ingest.ingest()
    result = graph.build_graph().invoke({**state, 'question':'Compare school programs'})
    assert result['mode']=='RAG answer'
    assert result['evidence'][0]['school_id']==school['id']
    assert school['name'] in contexts[0] and school['school_phone'] in contexts[0]
    assert 'Joyce Public School' not in contexts[0]
    assert result['evidence'][0]['source_url']==school['source_url']
