"""Streamlit workspace for the GTM Content Agent."""
from pathlib import Path
import sys
import json
import tempfile
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from langgraph.types import Command
from gtm_agent.document_loader import load_document, Document, clean
from gtm_agent.model import Model
from gtm_agent.workflow import build_workflow,export_markdown

ROOT=Path(__file__).parent
st.set_page_config(page_title='Launch Studio · GTM Agent',page_icon='✦',layout='wide')
st.markdown('''<style>
/* Keep Streamlit's theme colors paired for readable light and dark modes. */
[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.3);border-radius:12px;padding:16px;}
</style>''',unsafe_allow_html=True)
st.caption('LAUNCH STUDIO  /  WEEK 3 · AGENTIC AI')
st.title('One brief. A coordinated campaign.')
st.write('Turn a product or event document into reviewed content for LinkedIn, email, a blog and ads.')
with st.sidebar:
    st.header('Campaign brief')
    demo=st.checkbox('Use fictional demo brief',value=True)
    input_mode=st.radio('Your product source',['Upload document','Paste product details'],disabled=demo)
    uploaded=st.file_uploader('Product or event document',type=['pdf','docx'],disabled=demo or input_mode!='Upload document')
    product_details=st.text_area('Product details (source facts)',
        placeholder='Product name, what it does, features, audience, and any confirmed price or launch date. Leave unknown facts out.',
        disabled=demo or input_mode!='Paste product details',max_chars=20000)
    if demo:
        st.info('Source: Atlas Notes, a fictional meeting-notes product. Changing the campaign goal does not change this product. For fitness, turn off the demo and upload or paste your product details.')
    else:
        st.caption('The product source supplies facts. The campaign goal below tells the agent what to do with those facts.')
    goal=st.text_area('Campaign goal',value='Introduce the product and invite readers to learn more.',max_chars=1500)
    audience=st.text_input('Preferred audience',value='Small-team project managers',max_chars=300)
    tone=st.selectbox('Tone',['Clear and professional','Warm and approachable','Energetic and concise'])
    st.caption('Clicking Generate sends extracted document passages and your brief to the configured model provider. No content is posted or emailed.')
    generate=st.button('Generate campaign',type='primary',use_container_width=True)
    if st.button('Clear this session',use_container_width=True):
        for key in ['workflow','run_config','result','source_name','warnings','generation_error']:st.session_state.pop(key,None)
        st.rerun()

if generate:
    # Drop approval on every new run, even if the new input fails validation.
    for key in ['workflow','run_config','result','source_name','warnings','generation_error']:st.session_state.pop(key,None)
    try:
        if not goal.strip() or not audience.strip():raise ValueError('Add a campaign goal and preferred audience.')
        config=json.loads((ROOT/'config.json').read_text())
        if demo:
            document=load_document(ROOT/'examples/atlas_launch.docx',config['chunk_chars'])
        elif input_mode=='Paste product details':
            text=clean(product_details)
            if len(text)<30:raise ValueError('Add product details—not only a campaign goal. Include the product name, what it does and its features.')
            chunks=[{'id':i+1,'location':f'Pasted brief section {i+1}','text':text[start:start+config['chunk_chars']]} for i,start in enumerate(range(0,len(text),config['chunk_chars']))]
            document=Document('Your pasted product brief',chunks,[])
        else:
            if uploaded is None:raise ValueError('Upload a PDF or Word brief first.')
            if uploaded.size>25*1024*1024:raise ValueError('Use a document smaller than 25 MB.')
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/('upload'+Path(uploaded.name).suffix.lower())
                path.write_bytes(uploaded.getvalue())
                document=load_document(path,config['chunk_chars'])
                document.name=Path(uploaded.name).name
        if len(document.chunks)>config['max_chunks']:raise ValueError('This brief is too large. Use a shorter document (at most 150 chunks).')
        with st.status('Building your campaign…',expanded=True) as progress:
            workflow=build_workflow(Model(),config,notify=lambda event:st.write(f"**{event['node'].title()}** · {event['message']}"))
            run_config={'configurable':{'thread_id':uuid4().hex},'recursion_limit':40}
            result=workflow.invoke({'chunks':document.chunks,'brief':{'goal':goal,'audience':audience,'tone':tone},'events':[]},run_config)
            progress.update(label='Campaign generation failed — see the error below' if result['status']=='error' else 'Campaign workflow finished',state='error' if result['status']=='error' else 'complete',expanded=result['status']=='error')
        st.session_state.update(workflow=workflow,run_config=run_config,result=result,source_name=document.name,warnings=document.warnings)
    except (ValueError,RuntimeError,OSError,KeyError) as exc:
        st.session_state['generation_error']=str(exc)

result=st.session_state.get('result')
if not result:
    if st.session_state.get('generation_error'):st.error(st.session_state['generation_error'])
    st.info('Choose the demo brief or upload a document, then generate a campaign.')
    cols=st.columns(4)
    for col,title,text in zip(cols,['01 · Plan','02 · Write','03 · Review','04 · Approve'],
        ['Choose what to retrieve.','Create four coordinated formats.','Check facts and revise issues.','Review sources and unlock export.']):
        with col:st.subheader(title);st.write(text)
    if demo:
        with st.expander('Preview the fictional demo brief'):
            for c in load_document(ROOT/'examples/atlas_launch.docx').chunks:st.write(c['text'])
else:
    st.caption('Current result source: '+st.session_state['source_name']+' · Sidebar changes apply only after Generate campaign.')
    cols=st.columns(3)
    cols[0].metric('Status',result['status'].replace('_',' ').title())
    cols[1].metric('Draft versions',result.get('revision',0))
    cols[2].metric('Source passages',len(result.get('evidence',[])))
    if result.get('error'):st.error(result['error'])
    if not result.get('campaign'):
        st.warning('No campaign was created. Check the error above, confirm the selected product source, then click Generate campaign to retry.')
    if result.get('campaign'):
        plain_text=st.checkbox('Show drafts as plain text',help='Display the original draft text without Markdown formatting.')
        tabs=st.tabs(['LinkedIn','Email','Blog','Ads'])
        assets={a['channel']:a for a in result['campaign']['assets']}
        for tab,channel in zip(tabs,['linkedin','email','blog','ads']):
            with tab:
                asset=assets.get(channel)
                if asset and asset.get('body','').strip():
                    st.subheader(asset['title'])
                    if plain_text:st.code(asset['body'],language=None,wrap_lines=True)
                    else:st.markdown(asset['body'])
                    st.caption('Source citations: '+', '.join(map(str,asset['source_ids'])))
                else:
                    st.warning(f'No {channel.title()} draft was returned. Check Reviewer findings below for generation issues.')
    with st.expander('Reviewer findings',expanded=result['status']=='needs_changes'):
        review=result.get('review',{})
        st.write(review.get('summary','No review completed.'))
        for issue in review.get('issues',[]):st.warning(issue)
        st.caption('A model review is not a guarantee. Check the source passages before approving.')
    with st.expander('Source passages and extraction warnings'):
        for warning in st.session_state.get('warnings',[]):st.caption(warning)
        for e in result.get('evidence',[]):
            st.markdown(f"**[{e['id']}] {e['location']}**")
            st.text(e['text'])
    with st.expander('Workflow trace'):
        st.caption('The planner proposes a search strategy, not verified product facts. Only source passages support factual claims.')
        st.json({'brief':result['brief'],'plan':result.get('plan'),'events':result['events']})
    if result['status']=='awaiting_approval':
        with st.form('human_review'):
            st.subheader('Your final review')
            note=st.text_input('Review note (optional)')
            confirmed=st.checkbox('I checked the drafts against the source passages.')
            left,right=st.columns(2)
            approve=left.form_submit_button('Approve and unlock export',type='primary')
            reject=right.form_submit_button('Reject campaign')
        if approve or reject:
            if approve and not confirmed:st.warning('Check the source-review box before approving.')
            else:
                decision={'decision':'approve' if approve else 'reject','note':note}
                updated=st.session_state['workflow'].invoke(Command(resume=decision),st.session_state['run_config'])
                st.session_state['result']=updated
                st.rerun()
    elif result['status']=='needs_changes':
        st.warning('The revision limit was reached with unresolved issues. Improve the source brief or campaign instructions and generate again. Export is blocked.')
    elif result['status']=='rejected':st.info('Campaign rejected. Adjust your brief and generate a new version.')
    elif result['status']=='approved':
        st.success('Approved for export. Nothing has been published or sent.')
        st.download_button('Download campaign · Markdown',export_markdown(result),file_name='approved_campaign.md',mime='text/markdown')
        bundle={k:result.get(k) for k in ['brief','campaign','evidence','review','human_review','events','status']}
        st.download_button('Download campaign · JSON',json.dumps(bundle,indent=2),file_name='approved_campaign.json',mime='application/json')
