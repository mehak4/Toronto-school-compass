import json
from core import ROOT, registration_note, route_question
from graph import build_graph


def test_school_routes_and_dates():
    for case in json.loads((ROOT / 'data/school_evaluation_cases.json').read_text()):
        assert route_question(case['question']) == case['route']
    assert '2026-11-02' in registration_note('JK', '2027–28')
    assert '2026-11-02' not in registration_note('3', '2027–28')
    assert '2026-11-02' not in registration_note('JK', '2028–29')


def test_explicit_grade_and_year_override_context():
    graph = build_graph()
    answer = graph.invoke({'question':'Grade 3 registration deadline in 2028?', 'school_ids':['joyce'], 'grade':'JK','year':'2027–28'})['answer']
    assert 'School year: 2028–29' in answer
    assert '2026-11-02' not in answer
    assert 'English Kindergarten registration begins' not in answer


def test_ratings_do_not_invent_scores():
    result = build_graph().invoke({'question':'Which has the best rating?', 'school_ids':['joyce','glenpark']})
    assert '7.7/10' in result['answer'] and '5.1/10' in result['answer']
    assert '2023–24' in result['answer']
    assert 'Fraser' in result['answer'] and 'Find EQAO' not in result['answer']
    assert result['evidence'] == []


def test_app_school_tabs_and_year_context():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / 'app.py')).run()
    assert not app.exception
    assert [t.label for t in app.tabs] == ['Curriculum & programs', 'Registration dates', 'Fraser rating']
    app.selectbox[1].set_value('2027–28').run()
    assert any('2026-11-02' in m.value for m in app.markdown)
    app.selectbox[0].set_value('3').run()
    assert not any('2026-11-02' in m.value for m in app.markdown)
    assert not any('**Cost:**' in m.value for m in app.markdown)
    app.multiselect[0].set_value(['joyce','glenpark']).run()
    assert not app.exception
    app.selectbox[0].set_value('7').run()
    assert len(app.warning)==2


def test_curriculum_retrieval_excludes_childcare_and_wrong_grade():
    from graph import school_source_ids
    ids = school_source_ids({'question':'What do children learn in Kindergarten?', 'school_ids':['joyce','glenpark'], 'grade':'JK'})
    assert ids == ['kindergarten-learning']
    assert school_source_ids({'question':'Compare childcare programs', 'school_ids':['joyce']}) == ['joyce-care','joyce-hours']
    ids = school_source_ids({'question':'Compare school programs', 'school_ids':['joyce','glenpark']})
    assert 'joyce-care' not in ids and 'ontario-curriculum' in ids
