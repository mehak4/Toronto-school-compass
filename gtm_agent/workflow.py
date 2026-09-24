"""Planner → retrieval tool → writer ↔ reviewer → human approval."""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
from gtm_agent.schemas import Plan,Campaign,Critique,grounding_issues,critique_issues
from gtm_agent.retrieval import retrieve
from gtm_agent.model import ModelError

class State(TypedDict,total=False):
    chunks:list[dict]
    brief:dict
    plan:dict
    evidence:list[dict]
    campaign:dict
    review:dict
    revision:int
    status:str
    events:list[dict]
    human_review:dict
    error:str


def build_workflow(model,config,search=retrieve,checkpointer=None,notify=None):
    def event(state,node,message,**updates):
        item={'node':node,'message':message}
        if notify:notify(item)
        return {'events':state.get('events',[])+[item],**updates}
    def guarded(node,fn):
        def wrapped(state):
            try:return fn(state)
            except ModelError as exc:
                return event(state,node,str(exc),status='error',error=f'{node.title()} failed: {exc}')
            except Exception:
                return event(state,node,'Step failed; review configuration and retry as a new campaign.',status='error',error=f'{node} failed. No export is available. Check model configuration and source extraction.')
        return wrapped
    def plan(state):
        result=model.structured('campaign planner','Describe only the steps you will take, not assumed product capabilities or benefits. Plan retrieval queries for the product facts, target audience, dates, features, pricing, constraints and approved messaging. Do not invent facts. The user goal and preferred audience/tone are creative direction, not evidence.',
             {'brief':state['brief'],'document_preview':state['chunks'][0]['text'][:1800]},Plan)
        return event(state,'plan',result['approach'],plan=result,status='running',revision=0)
    def search_node(state):
        evidence=search(state['chunks'],state['plan']['queries'],model,config['top_k'],config['max_evidence'])
        if not evidence:raise ValueError('No evidence')
        return event(state,'retrieve',f"Retrieved {len(evidence)} source passages using {len(state['plan']['queries'])} planned queries.",evidence=evidence)
    def write(state):
        campaign=model.structured('campaign writer',
            'Create exactly four assets: a LinkedIn post, a promotional email with its subject in title and a CTA in body, a short blog draft, and one ads asset containing three clearly numbered ad variations. Keep copy concise. Use only the provided sources for factual claims, including claims in titles. Shared notes does NOT establish real-time collaboration; task assignment does NOT establish automated tracking. Cite EVERY factual sentence, including dates and every ad variation, inline as [1], [2], etc. source_ids lists only IDs actually cited in that body. Never invent URLs, prices, guarantees, dates, testimonials, availability or partnerships. Include confirmed launch date and price in the email or blog if supplied; they need not appear in every asset. Omit missing specifics. A text-only Learn more CTA is sufficient when no URL is supplied. Creative headlines/CTAs are proposals, not facts. Respect the requested tone and use consistent facts across all assets. Fix all prior review issues when revising.',
            # Campaign permissions must not become claims about product availability.
            {'brief':state['brief'],'evidence':state['evidence'],
             'source_interpretation':'A claim not approved for this campaign is unknown, not false. For example, "No free trial is approved for this campaign" means omit trial claims. It does NOT justify writing "No free trial is available" or "No free trial at launch". Do not discuss unavailable plans, trials or discounts unless sources explicitly confirm their actual unavailability.',
             'previous_campaign':state.get('campaign'),
             'review_issues':state.get('review',{}).get('issues',[])},Campaign)
        return event(state,'write',f"Produced campaign draft {state['revision']+1}.",campaign=campaign,revision=state['revision']+1)
    def review(state):
        instructions='''Audit this ready-to-edit campaign against the supplied evidence and creative brief. Return findings only for concrete defects, or an empty findings list when none exist. This is not a request to invent improvements.
For each finding identify the channel, category, exact draft_quote, source_ids checked, and a specific explanation/correction. For a genuinely missing requirement only, draft_quote may be empty. Check titles as well as bodies. A citation number alone does not prove its claim. Quote the offending words, not a paraphrase. Do not repeat the same issue.
Blocking defects: unsupported capabilities or promises; incorrect dates/prices; citations that support a different claim; missing requested formats; missing email CTA or fewer than three distinct ad variations; clear conflict with the requested tone. A confirmed price/date should appear in email or blog when available, not necessarily every asset. Only call other omissions missing requirements if the user or source explicitly requires their inclusion.
Calibration examples: shared notes does not imply real-time collaboration, so an unestablished real-time claim is a defect. "No free trial or discount" does not invalidate a stated paid price. "No free trial is approved for this campaign" is a copy restriction, NOT proof that trials do not exist; a draft saying "no free trial available" or "no free trial at launch" is an unsupported claim unless actual unavailability is explicitly established. When no URL is supplied, "Learn more" is a valid text-only CTA, not a missing link. Prohibited claims are constraints to obey, not disclaimers that must be printed. A source being fictional does not require a disclaimer in every asset: the demo is already labelled in the app. Omitting a prohibited feature is correct, not misleading. General invitations such as "Explore" or "Learn more" are allowed; quantified benefits and factual promises require evidence.
Treat demo facts as authoritative within the fictional example. Do not demand external verification. User goals provide creative direction, not evidence for new product claims. Do not rewrite the campaign.'''
        payload={'brief':state['brief'],'evidence':state['evidence'],'campaign':state['campaign']}
        for attempt in range(2):
            critique=model.structured('campaign evidence reviewer',instructions,payload,Critique)
            errors=critique_issues(critique,state['campaign'],state['evidence'])
            if not errors:break
            payload['previous_critique']=critique
            payload['validation_errors']=errors
        if errors:
            raise ModelError('The reviewer could not provide verifiable draft quotes after one retry. The draft is retained but approval is blocked. Retry the campaign.')
        issues=[f"{f['channel']} ({f['category']}): {f['explanation']}" for f in critique['findings']]
        issues+=grounding_issues(state['campaign'],state['evidence'])
        result={'passed':not issues,'issues':issues,'summary':critique['summary'],'findings':critique['findings']}
        status='awaiting_approval' if result['passed'] else ('needs_changes' if state['revision']>=config['max_revisions']+1 else 'revising')
        return event(state,'review',result['summary'],review=result,status=status)
    def approval(state):
        decision=interrupt({'campaign':state['campaign'],'review':state['review'],'message':'Approve or reject this exact campaign before export.'})
        if not isinstance(decision,dict) or decision.get('decision') not in {'approve','reject'}:
            raise ValueError('Explicit approve or reject decision required')
        return event(state,'human_review',decision['decision'],human_review=decision,
                     status='approved' if decision['decision']=='approve' else 'rejected')
    graph=StateGraph(State)
    for name,fn in [('plan',plan),('retrieve',search_node),('write',write),('review',review)]:graph.add_node(name,guarded(name,fn))
    graph.add_node('approval',approval)
    graph.add_edge(START,'plan')
    for name,next_node in [('plan','retrieve'),('retrieve','write'),('write','review')]:
        graph.add_conditional_edges(name,lambda s,n=next_node: END if s['status']=='error' else n)
    graph.add_conditional_edges('review',lambda s: 'approval' if s['status']=='awaiting_approval' else ('write' if s['status']=='revising' else END))
    graph.add_edge('approval',END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def export_markdown(state):
    if state.get('status')!='approved':raise ValueError('Human approval is required for export')
    parts=['# Approved GTM campaign']
    for asset in state['campaign']['assets']:
        parts.extend([f"## {asset['channel'].title()}: {asset['title']}",asset['body']])
    parts.append('## Source passages')
    for e in state['evidence']:parts.append(f"[{e['id']}] {e['location']}\n\n"+'\n'.join('> '+line for line in e['text'].splitlines()))
    return '\n\n'.join(parts)
