import json
import os
import re
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from fraser import rating_text
from core import ROOT, LOCATOR, directory, route_question, fee_label, school_guidance, registration_note

class State(TypedDict, total=False):
    question: str
    school_ids: list[str]
    answer: str
    evidence: list[dict]
    selected_source_ids: list[int]
    mode: str
    grade: str
    year: str
    school_records: list[dict]

def facts(state):
    route = route_question(state['question'])
    records = {s['id']: s for s in directory()}
    records.update({s['id']: s for s in state.get('school_records', [])})
    schools = [s for s in records.values() if s['id'] in state['school_ids']]
    if route == 'boundary':
        return {'answer': f'Use the address form above for a live regular-program school lookup. Chat does not look up or verify addresses. Confirm your school year, grade and program with the board or the [official TDSB finder]({LOCATOR}).', 'mode': 'Official verification needed', 'evidence': []}
    if route == 'registration':
        guide = school_guidance()
        years = re.findall(r'\b20\d{2}\b', state['question'])
        year = state.get('year', '2026–27')
        if years:
            start = int(years[0])
            year = f'{start}–{str(start + 1)[-2:]}'
        grade_match = re.search(r'\bgrade\s+([1-8])\b', state['question'], re.I)
        grade = grade_match.group(1) if grade_match else state.get('grade', 'JK')
        text = registration_note(grade, year)
        text += '\n\nDates depend on entry year and program. Only the September 2027 JK French Immersion window is verified here; dates for other entry years are not verified.'
        text += f"\n\n[Official registration guidance]({guide['registration']['source_url']}) · checked {guide['checked_at']}."
        return {'answer': text, 'mode': 'Registration guidance', 'evidence': []}
    if route == 'ratings':
        ratings = school_guidance()['ratings']
        text = '\n\n'.join(f"**{s['name']} ({s['address']}):** {rating_text(s)}" for s in schools)
        text += f"\n\n{ratings['fraser_note']}"
        return {'answer': text, 'mode': 'Fraser school ratings', 'evidence': []}
    lines = []
    for s in schools:
        c = s.get('childcare')
        if not c:
            lines.append(f"**{s['name']}:** Childcare details have not been reviewed for this school. Contact the [school office]({s['source_url']}) for provider information.")
            continue
        fact = fee_label(c['fee']) if route == 'fees' else c['vacancy_note']
        if route == 'vacancy' and 'waitlist' in state['question'].lower():
            fact = 'Waitlist status is not published in the checked sources; contact the provider to ask about joining a waitlist. ' + fact
        lines.append(f"**{s['name']} — {c['name']}:** {fact}. [Source]({c['source_url']}); checked {c['checked_at']}.")
    return {'answer': '\n\n'.join(lines) or 'Select a school first.', 'mode': 'Verified directory fields', 'evidence': []}

def school_source_ids(state):
    q = state['question'].lower()
    schools = state['school_ids']
    childcare = bool(re.search(r'child\s*care|day\s*care|before[- ](?:and[- ])?after[- ]school|after[- ]school', q))
    hours = bool(re.search(r'\bhours?\b|opening times?|session times?', q))
    if childcare or (hours and re.search(r"summer|cent(?:re|er)|session", q)):
        # Retain both providers for comparisons, including explicit missing-fee facts.
        return [sid + suffix for sid in schools for suffix in ('-care', '-hours')]
    learning = any(word in q for word in ('curricul', 'learn', 'subjects'))
    profiles = 'school program' in q or ('compare' in q and 'school' in q)
    if not learning and not profiles:
        return None  # Unknown topics keep broad retrieval, then evidence selection may abstain.
    ids = [sid + '-profile' for sid in schools] if profiles else []
    if learning or profiles:
        explicit_grade = re.search(r'\bgrade\s+([1-8])\b', q)
        kindergarten = 'kindergarten' in q or bool(re.search(r'\b(?:jk|sk)\b', q))
        if not explicit_grade and state.get('grade') in ('JK', 'SK'):
            kindergarten = True
        ids.append('kindergarten-learning' if kindergarten else 'ontario-curriculum')
    return ids


def retrieve(state):
    from provider import embed
    import chromadb
    if not (ROOT / '.index.json').exists():
        return {'answer': 'The document index is not configured yet. School and childcare cards work now; follow README to enable AI answers.', 'mode': 'Setup required', 'evidence': []}
    config = json.loads((ROOT / '.index.json').read_text())
    if config['model'] != os.environ.get('EMBEDDING_MODEL') or config['base_url'] != os.environ.get('MODEL_BASE_URL'):
        raise RuntimeError('Embedding configuration changed; run ingest.py again.')
    collection = chromadb.PersistentClient(path=str(ROOT / '.chroma')).get_collection(config['collection'])
    vector = embed([state['question']])[0]
    evidence = []
    source_ids = school_source_ids(state)
    for school in state.get('school_records', []):
        if (school['id'] in state['school_ids'] and school.get('lookup_profile')
                and (source_ids is None or school['id'] + '-profile' in source_ids)):
            evidence.append({
                'id': school['id'] + '-profile', 'school_id': school['id'],
                'title': school['name'] + ' — official lookup profile',
                'source_url': school['source_url'], 'checked_at': school['profile_checked_at'],
                'text': f"{school['name']}. School address: {school['address']}. Grade range: {school['grade_range']}. School office: {school['school_phone']}. {school['program_note']} Childcare details have not been reviewed for this school. {rating_text(school)}",
            })
    # Balanced retrieval includes each compared school and board guidance.
    for sid in list(dict.fromkeys(state['school_ids'] + ['board'])):
        where = {'school_id': sid}
        if source_ids:
            where = {'$and': [where, {'id': {'$in': source_ids}}]}
        result = collection.query(query_embeddings=[vector], n_results=3, where=where)
        for text, meta in zip(result['documents'][0], result['metadatas'][0]):
            evidence.append({'text': text, **meta})
    return {'evidence': evidence, 'mode': 'RAG answer'}

def answer(state):
    from provider import generate, verify_selection
    if not state.get('evidence'):
        return {'answer': state.get('answer', 'I could not find supporting information.')}
    context = '\n\n'.join(f"[{i}] {e['title']} — checked {e['checked_at']}\n{e['text']}" for i, e in enumerate(state['evidence'], 1))
    question = state['question']
    if state.get('grade') or state.get('year'):
        question += f"\nSelected grade: {state.get('grade', 'not specified')}; school year: {state.get('year', 'not specified')}."
    response = generate(question, context)
    evidence = state['evidence']
    proposed = grounded_excerpts(response, evidence)
    ids = proposed['selected_source_ids']
    if not ids:
        return proposed
    selected_context = '\n\n'.join(
        f"[{i}] {evidence[i-1]['title']}\n{evidence[i-1]['text']}" for i in ids)
    try:
        checked = grounded_excerpts(verify_selection(question, selected_context), evidence)
    except RuntimeError:
        return grounded_excerpts('{"source_ids": []}', evidence)
    # A reviewer cannot introduce sources that were not supplied to it.
    if not set(checked['selected_source_ids']).issubset(ids):
        return grounded_excerpts('{"source_ids": []}', evidence)
    return checked


def grounded_excerpts(response, evidence):
    """Only trusted source text reaches the answer; model prose is never rendered."""
    fallback = {'answer': 'I could not find a supported answer in the supplied sources. Please check with the school or provider.',
                'mode': 'Grounding fallback', 'selected_source_ids': []}
    try:
        selection = json.loads(response)
        if not isinstance(selection, dict) or set(selection) != {'source_ids'}:
            return fallback
        ids = selection['source_ids']
        if (not isinstance(ids, list) or len(ids) > 4 or
                any(type(i) is not int or not 1 <= i <= len(evidence) for i in ids) or
                len(ids) != len(set(ids))):
            return fallback
    except (ValueError, TypeError):
        return fallback
    if not ids:
        return fallback
    blocks = ['Relevant source excerpts:']
    for i in ids:
        source = evidence[i-1]
        # Keep the whole excerpt, preserving school attribution, dates and caveats.
        blocks.append(f"**{source['title']}** — checked {source['checked_at']} [{i}]\n\n" +
                      '\n'.join('> ' + line for line in source['text'].splitlines()))
    blocks.append('These excerpts describe the supplied sources; they do not confirm future-year offerings or current availability.')
    return {'answer': '\n\n'.join(blocks), 'mode': 'RAG answer', 'selected_source_ids': ids}


def build_graph():
    graph = StateGraph(State)
    graph.add_node('facts', facts)
    graph.add_node('retrieve', retrieve)
    graph.add_node('answer', answer)
    graph.add_conditional_edges(START, lambda s: 'retrieve' if route_question(s['question']) == 'retrieve' else 'facts')
    graph.add_edge('facts', END)
    graph.add_edge('retrieve', 'answer')
    graph.add_edge('answer', END)
    return graph.compile()
