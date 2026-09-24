import pytest
from langgraph.types import Command
from gtm_agent.workflow import build_workflow,export_markdown
from gtm_agent.schemas import grounding_issues
from gtm_agent.retrieval import retrieve

CONFIG={'max_revisions':2,'top_k':4,'max_evidence':12}
CHUNKS=[{'id':1,'location':'block 1','text':'Atlas Notes launches October 15, 2026.'}]
EVIDENCE=[{**CHUNKS[0],'chunk_id':1,'retrieved_for':'launch'}]

class FakeModel:
    def __init__(self,fail_reviews=0,bad_citations=False):
        self.fail_reviews=fail_reviews;self.reviews=0;self.writes=[];self.bad=bad_citations
    def structured(self,role,instructions,payload,schema):
        if 'planner' in role:return {'approach':'Look up launch facts','queries':['launch']}
        if 'writer' in role:
            self.writes.append(payload)
            return {'assets':[{'channel':c,'title':c,'body':'Launch October 15, 2026. [99]' if self.bad else 'Launch October 15, 2026. [1]','source_ids':[99] if self.bad else [1]} for c in ['linkedin','email','blog','ads']]}
        self.reviews+=1
        failed=self.reviews<=self.fail_reviews
        return {'findings':[{'channel':'linkedin','category':'contradiction','draft_quote':'Launch October 15, 2026.','source_ids':[1],'explanation':'Correct launch date'}] if failed else [],'summary':'Needs correction' if failed else 'Supported'}
    def embed(self,texts):return [[1.0,0.1,0.5] for _ in texts]


def start(model,search=lambda *args:EVIDENCE):
    graph=build_workflow(model,CONFIG,search=search)
    config={'configurable':{'thread_id':'test'},'recursion_limit':40}
    result=graph.invoke({'chunks':CHUNKS,'brief':{'goal':'Introduce product'},'events':[]},config)
    return graph,config,result


def test_revision_observes_review_then_pauses_for_approval():
    model=FakeModel(fail_reviews=1)
    graph,config,result=start(model)
    assert result['status']=='awaiting_approval' and result['__interrupt__']
    assert result['revision']==2 and 'Correct launch date' in model.writes[1]['review_issues'][0]
    with pytest.raises(ValueError):export_markdown(result)
    result=graph.invoke(Command(resume={'decision':'approve'}),config)
    assert result['status']=='approved'
    assert '# Approved GTM campaign' in export_markdown(result)


def test_rejection_and_revision_exhaustion_block_exports():
    graph,config,result=start(FakeModel())
    rejected=graph.invoke(Command(resume={'decision':'reject'}),config)
    with pytest.raises(ValueError):export_markdown(rejected)
    _,_,failed=start(FakeModel(fail_reviews=100))
    assert failed['status']=='needs_changes' and failed['revision']==3
    assert '__interrupt__' not in failed
    with pytest.raises(ValueError):export_markdown(failed)


def test_deterministic_citation_checks_override_reviewer_pass():
    _,_,result=start(FakeModel(bad_citations=True))
    assert result['status']=='needs_changes'
    assert any('inline citations' in issue for issue in result['review']['issues'])


def test_tool_failure_stops_cleanly():
    def broken(*args):raise RuntimeError('Synthetic tool failure')
    _,_,result=start(FakeModel(),broken)
    assert result['status']=='error' and 'campaign' not in result
    with pytest.raises(ValueError):export_markdown(result)


def test_ephemeral_vector_retrieval_isolates_documents():
    a=retrieve(CHUNKS,['launch'],FakeModel())
    b=retrieve([{'id':1,'location':'page 2','text':'Different confidential product'}],['product'],FakeModel())
    assert a[0]['text']==CHUNKS[0]['text']
    assert b[0]['text']=='Different confidential product'
    assert a[0]['chunk_id']==1 and a[0]['id']==1


def test_streamlit_generate_review_approve_and_new_run(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    import gtm_agent.model
    monkeypatch.setattr(gtm_agent.model,'Model',FakeModel)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    assert not app.exception
    next(b for b in app.button if b.label=='Generate campaign').click().run()
    assert not app.exception
    assert app.session_state['result']['status']=='awaiting_approval'
    next(b for b in app.button if b.label=='Approve and unlock export').click().run()
    assert app.session_state['result']['status']=='awaiting_approval'
    next(c for c in app.checkbox if 'checked the drafts' in c.label).check().run()
    next(b for b in app.button if b.label=='Approve and unlock export').click().run()
    assert not app.exception and app.session_state['result']['status']=='approved'
    assert len(app.get('download_button'))==2
    next(b for b in app.button if b.label=='Generate campaign').click().run()
    assert app.session_state['result']['status']=='awaiting_approval'
    assert len(app.get('download_button'))==0


def test_short_brief_keeps_constraints_even_when_top_k_is_small():
    chunks=[{'id':i,'location':f'block {i}','text':f'Source {i}'} for i in range(1,7)]
    result=retrieve(chunks,['launch'],FakeModel(),top_k=1,max_evidence=12)
    assert {e['chunk_id'] for e in result}==set(range(1,7))
    assert any(e['retrieved_for']=='Full short-brief coverage' for e in result)


def test_pasted_fitness_source_reaches_writer(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    import gtm_agent.model
    model=FakeModel()
    monkeypatch.setattr(gtm_agent.model,'Model',lambda:model)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    next(c for c in app.checkbox if c.label=='Use fictional demo brief').uncheck().run()
    app.radio[0].set_value('Paste product details').run()
    next(t for t in app.text_area if t.label=='Product details (source facts)').set_value('Move Journal is a fictional fitness journal. It records workouts and weekly exercise goals.')
    next(t for t in app.text_area if t.label=='Campaign goal').set_value('Introduce the product on fitness and invite readers to learn more.')
    next(b for b in app.button if b.label=='Generate campaign').click().run()
    assert not app.exception
    assert model.writes and all('Atlas Notes' not in e['text'] for e in model.writes[0]['evidence'])
    assert 'Move Journal' in model.writes[0]['evidence'][0]['text']
    assert len(app.tabs)==4


def test_provider_error_visible_without_campaign(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    import gtm_agent.model
    class FailedModel(FakeModel):
        def structured(self,*args):raise gtm_agent.model.ModelError('The provider rejected the API token. Check MODEL_API_KEY.')
    monkeypatch.setattr(gtm_agent.model,'Model',FailedModel)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run()
    next(b for b in app.button if b.label=='Generate campaign').click().run()
    assert not app.exception
    assert any('provider rejected' in e.value for e in app.error)
    assert any('No campaign was created' in e.value for e in app.warning)
    assert len(app.get('download_button'))==0


def test_structured_response_accepts_fences_rejects_empty_fields():
    from gtm_agent.model import Model,ModelError
    from gtm_agent.schemas import Plan
    model=object.__new__(Model);model.chat='test'
    model.call=lambda *args:{'choices':[{'message':{'content':'```json\n{"approach":"Read the source", "queries":["product"]}\n```'}}]}
    assert model.structured('planner','Plan',{},Plan)['queries']==['product']
    model.call=lambda *args:{'choices':[{'message':{'content':'{"approach":"   ", "queries":["product"]}'}}]}
    with pytest.raises(ModelError):model.structured('planner','Plan',{},Plan)


def test_http_error_does_not_expose_response_or_key(monkeypatch):
    import urllib.error
    from gtm_agent.model import Model,ModelError
    model=object.__new__(Model);model.base='https://example.invalid';model.key='SECRET_TEST_TOKEN'
    def fail(*args,**kwargs):raise urllib.error.HTTPError('https://example.invalid',401,'SECRET_TEST_TOKEN',{},None)
    monkeypatch.setattr('urllib.request.urlopen',fail)
    with pytest.raises(ModelError) as exc:model.call('/chat/completions',{})
    assert 'API token' in str(exc.value) and 'SECRET_TEST_TOKEN' not in str(exc.value)


def test_invented_reviewer_quote_retries_then_blocks_approval():
    class BadReviewer(FakeModel):
        def structured(self,role,instructions,payload,schema):
            result=super().structured(role,instructions,payload,schema)
            if 'reviewer' in role:
                result['findings']=[{'channel':'linkedin','category':'unsupported_claim',
                    'draft_quote':'Guaranteed 100% improvement','source_ids':[1],
                    'explanation':'Unsupported guarantee'}]
            return result
    model=BadReviewer()
    _,_,result=start(model)
    assert model.reviews==2 and result['status']=='error'
    assert result['campaign']['assets'] and '__interrupt__' not in result
    with pytest.raises(ValueError):export_markdown(result)


def test_reviewer_repairs_invalid_quote_without_rewriting_campaign():
    class RepairingReviewer(FakeModel):
        def structured(self,role,instructions,payload,schema):
            result=super().structured(role,instructions,payload,schema)
            if 'reviewer' in role and self.reviews==1:
                result['findings']=[{'channel':'email','category':'contradiction',
                    'draft_quote':'Invented quote','source_ids':[1], 'explanation':'Wrong date'}]
            elif 'reviewer' in role:
                assert payload['validation_errors'] and payload['previous_critique']
            return result
    model=RepairingReviewer()
    _,_,result=start(model)
    assert model.reviews==2 and result['status']=='awaiting_approval'
    assert len(model.writes)==1


def test_real_unsupported_claim_still_blocks_even_with_valid_citation():
    class UnsupportedWriter(FakeModel):
        def structured(self,role,instructions,payload,schema):
            result=super().structured(role,instructions,payload,schema)
            if 'writer' in role:
                result['assets'][0]['body']='Guaranteed results. [1]'
            if 'reviewer' in role:
                result['findings']=[{'channel':'linkedin','category':'unsupported_claim',
                    'draft_quote':'Guaranteed results.','source_ids':[1],
                    'explanation':'The source establishes only a launch date, not a guarantee.'}]
            return result
    _,_,result=start(UnsupportedWriter())
    assert result['status']=='needs_changes' and result['revision']==3
    assert 'guarantee' in result['review']['issues'][0]


def test_gtm_model_override_is_scoped_and_optional(monkeypatch):
    from gtm_agent.model import Model
    monkeypatch.setattr('gtm_agent.model.load_dotenv',lambda *args,**kwargs:None)
    for name,value in {'MODEL_BASE_URL':'https://example.invalid','MODEL_API_KEY':'test',
                       'CHAT_MODEL':'shared-model','EMBEDDING_MODEL':'embedding-model',
                       'GTM_CHAT_MODEL':'campaign-model'}.items():
        monkeypatch.setenv(name,value)
    assert Model().chat=='campaign-model'
    monkeypatch.delenv('GTM_CHAT_MODEL')
    assert Model().chat=='shared-model'
