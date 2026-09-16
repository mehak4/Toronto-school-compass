from graph import school_source_ids, grounded_excerpts


def test_subject_filters_preserve_comparison_and_explicit_grade():
    state={'school_ids':['joyce','glenpark'],'grade':'JK'}
    assert school_source_ids(dict(state,question='What subjects do children learn in Grade 3?'))==['ontario-curriculum']
    assert school_source_ids(dict(state,question='Describe learning in SK'))==['kindergarten-learning']
    assert school_source_ids(dict(state,question='Compare daycare programs'))==['joyce-care','joyce-hours','glenpark-care','glenpark-hours']
    assert school_source_ids(dict(state,question='What are summer opening times?'))==['joyce-care','joyce-hours','glenpark-care','glenpark-hours']
    assert school_source_ids(dict(state,question='Is there a robotics club?')) is None
    assert school_source_ids(dict(state,question='What are the school opening hours?')) is None


def test_selection_is_auditable_and_failed_selection_is_empty():
    evidence=[dict(title='Test',checked_at='2026-09-12',text='Source passage.')]
    assert grounded_excerpts('{"source_ids":[1]}',evidence)['selected_source_ids']==[1]
    assert grounded_excerpts('{"source_ids":[9]}',evidence)['selected_source_ids']==[]
