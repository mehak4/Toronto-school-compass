from core import directory
from fraser import rating_for, rating_text


def test_verified_ratings_include_assessment_year_and_source_page():
    for school, expected, page in zip(directory(), [7.7, 5.1], [17,31]):
        rating = rating_for(school)
        assert rating['score']==expected
        assert rating['assessment_year']=='2023–24'
        assert rating['report_year']==2025
        assert rating['pdf_page']==page
        assert f'#page={page}' in rating_text(school)


def test_unverified_or_wrong_school_never_gets_a_score():
    assert rating_for({'name':'Another School', 'profile_url':'https://www.tdsb.on.ca/FindYour/Schools/schno/3182'}) is None
    assert rating_for({'name':'Lawrence Heights Middle School','source_url':'https://www.tdsb.on.ca/FindYour/Schools/schno/3190'}) is None
    assert 'not verified' in rating_text({'name':'Unknown', 'source_url':''})


def test_dynamic_school_ratings():
    school = {'name':'John Polanyi Collegiate Institute','source_url':'https://www.tdsb.on.ca/FindYour/Schools/schno/3437'}
    assert rating_for(school)['score']==4.4
    assert rating_for(school)['school_level']=='secondary'
    school = {'name':'Ledbury Park Elementary and Middle School','source_url':'https://www.tdsb.on.ca/FindYour/Schools/schno/3189'}
    assert rating_for(school)['score']==7.6


def test_rating_visible_in_app():
    from streamlit.testing.v1 import AppTest
    from core import ROOT
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not app.exception
    assert app.metric[0].value=='7.7 / 10'
    app.multiselect[0].set_value(['joyce','glenpark']).run()
    assert not app.exception
    assert [m.value for m in app.metric]==['7.7 / 10','5.1 / 10']


def test_blue_jays_way_school_ratings_and_fraser_only_ui():
    from graph import build_graph
    from streamlit.testing.v1 import AppTest
    from core import ROOT
    schools=[]
    for code,name,score in [('5257','Ogden Junior Public School',6.8),('5273','Ryerson Community School',4.1),('5510','Harbord Collegiate Institute',7.5)]:
        school={'id':'tdsb-'+code,'name':name,'address':'Toronto','source_url':'https://www.tdsb.on.ca/FindYour/Schools/schno/'+code}
        assert rating_for(school)['score']==score
        assert rating_for(school)['fraser_city']=='Toronto'
        schools.append(school)
    answer=build_graph().invoke({'question':'What are their ratings?', 'school_ids':[s['id'] for s in schools], 'school_records':schools})['answer']
    assert all(f'{score}/10' in answer for score in ['6.8','4.1','7.5'])
    assert 'Find EQAO' not in answer
    app=AppTest.from_file(str(ROOT/'app.py')).run()
    assert not app.exception
    assert app.tabs[2].label=='Fraser rating'
    assert not any('EQAO' in b.label for b in app.get('link_button'))


def test_catalog_counts_provenance_and_reviewed_parity():
    import json
    from core import ROOT
    catalog = json.loads((ROOT/'data/fraser_catalog.json').read_text())
    rows = catalog['ratings']
    assert len(rows) == 3799
    assert sum(r['school_level']=='elementary' for r in rows)==3052
    assert sum(r['score'] is None for r in rows)==1
    assert all(r['printed_page']==r['pdf_page']-2 for r in rows)
    for known in json.loads((ROOT/'data/fraser_ratings.json').read_text()).values():
        assert sum(all(row[k]==known[k] for k in ('fraser_name','fraser_city','school_level','score','pdf_page')) for row in rows)==1


def test_automatic_matching_keeps_municipality_and_level_separate():
    school = dict(name='Forest Hill Public School', address='1 Example St, Toronto, ON',
                  grade_range='JK–6', source_url='https://www.tdsb.on.ca/FindYour/Schools/schno/9999')
    assert rating_for(school)['score']==8.3
    school.update(name='Forest Hill Collegiate Institute', grade_range='9–12')
    assert rating_for(school)['score']==7.5
    assert 'Automatic exact' in rating_text(school)
    for changes in [dict(grade_range='Not stated in lookup'), dict(address='1 Example St'),
                    dict(address='1 Example St, North York, ON'), dict(name='Forest Hills Collegiate Institute'),
                    dict(source_url='https://example.com/schno/9999')]:
        assert rating_for(dict(school, **changes)) is None


def test_ambiguous_catalog_match_is_not_shown(monkeypatch):
    import fraser
    row = dict(fraser_name='Example', fraser_city='Toronto', school_level='elementary',score=5.0)
    monkeypatch.setattr(fraser, '_data', lambda name: {} if name=='fraser_ratings.json' else {'ratings':[row,dict(row,score=7.0)]})
    school = dict(name='Example Public School', address='Toronto',grade_range='JK–6',
                  source_url='https://www.tdsb.on.ca/FindYour/Schools/schno/9999')
    assert rating_for(school) is None
