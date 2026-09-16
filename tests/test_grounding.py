import json
import pytest
from graph import grounded_excerpts

EVIDENCE = [
    {'title':'Joyce profile', 'checked_at':'2026-09-12', 'text':'Joyce has an inclusive learning environment. Several program sections are marked update pending.'},
    {'title':'Glen Park profile', 'checked_at':'2026-09-12', 'text':'Glen Park describes French and English programming. Confirm placement with the school.'},
    {'title':'Kindergarten learning', 'checked_at':'2026-09-12', 'text':'TDSB describes inquiry and intentional play-based learning.'},
]


@pytest.mark.parametrize('response', [
    'Children learn literacy and numeracy [3].',
    '{"source_ids":[3],"answer":"Invented claim"}',
    '{"source_ids":[0]}', '{"source_ids":[4]}', '{"source_ids":[true]}',
    '{"source_ids":[1,1]}', '{"source_ids":"1"}', 'null', '[]', '{',
    '{"source_ids":[]}', '{"source_ids":[1,2,3,1,2]}',
])
def test_unvalidated_model_output_never_reaches_answer(response):
    result=grounded_excerpts(response,EVIDENCE)
    assert result['mode']=='Grounding fallback'
    assert 'Invented claim' not in result['answer']


def test_learning_cannot_acquire_unsupported_developmental_claims():
    result=grounded_excerpts('{"source_ids":[3]}',EVIDENCE)
    assert EVIDENCE[2]['text'] in result['answer']
    assert 'literacy' not in result['answer']
    assert 'update pending' not in result['answer']
    assert '[3]' in result['answer']


def test_comparison_preserves_attribution_and_qualifiers():
    result=grounded_excerpts(json.dumps({'source_ids':[1,2]}),EVIDENCE)
    assert EVIDENCE[0]['text'] in result['answer']
    assert EVIDENCE[1]['text'] in result['answer']
    glen=result['answer'].split('**Glen Park profile**')[1]
    assert 'update pending' not in glen
    assert 'Confirm placement' in glen


@pytest.mark.parametrize('review', ['{"source_ids":[]}', '{"source_ids":[1]}', 'yes', '{"source_ids":[true]}'])
def test_specific_question_cannot_bypass_answerability_check(monkeypatch, review):
    import provider, graph
    monkeypatch.setattr(provider,'generate',lambda q,c:'{"source_ids":[3]}')
    contexts=[]
    def verify(q,c):
        contexts.append(c)
        return review
    monkeypatch.setattr(provider,'verify_selection',verify)
    result=graph.answer({'question':'Does Kindergarten guarantee daily coding lessons?', 'evidence':EVIDENCE})
    assert result['mode']=='Grounding fallback'
    assert 'Joyce' not in contexts[0]  # Reviewer receives only the proposed source.
    assert EVIDENCE[2]['text'] in contexts[0]


def test_valid_paraphrase_survives_review_and_verifier_failure_abstains(monkeypatch):
    import graph, provider
    monkeypatch.setattr(provider,'generate',lambda q,c:'{"source_ids":[3]}')
    monkeypatch.setattr(provider,'verify_selection',lambda q,c:'{"source_ids":[3]}')
    state={'question':'How do pupils learn in JK?', 'evidence':EVIDENCE}
    assert graph.answer(state)['selected_source_ids']==[3]
    def unavailable(q,c):
        raise RuntimeError('Provider unavailable')
    monkeypatch.setattr(provider,'verify_selection',unavailable)
    assert graph.answer(state)['mode']=='Grounding fallback'
