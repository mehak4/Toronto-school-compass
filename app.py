import streamlit as st
from core import directory, school_guidance, registration_note, LOCATOR
from graph import build_graph
from address_lookup import TDSBLookup, LookupUnavailable
from profiles import comparison_schools, includes_grade
from fraser import rating_for

st.set_page_config(page_title='Toronto School Compass', page_icon='🏫', layout='wide')
st.title('Toronto School Compass')
st.write('Explore curriculum, registration dates and Fraser ratings with source-backed guidance.')
st.caption('Live regular-program address lookup from TDSB. Explore every returned school alongside the reviewed profiles.')
grade = st.selectbox('Grade', ['JK', 'SK', '1', '2', '3', '4', '5', '6', '7', '8'])
year = st.selectbox('School year', ['2026–27', '2027–28'])
program = st.selectbox('Attendance program', ['Regular', 'French Immersion / other specialized program'])
st.caption('Searching sends your street address directly to TDSB. It is kept only in this session, not saved to disk or sent to the AI. The board lookup has no school-year selector.')
context = (grade, year, program)
if st.session_state.get('lookup_context') != context:
    st.session_state.pop('address_result', None)
    st.session_state.pop('pending_address', None)
    st.session_state['lookup_context'] = context

schools = directory()

def search_address(value, confirmed_street=None):
    st.session_state.pop('address_result', None)
    st.session_state.pop('pending_address', None)
    try:
        with st.spinner('Checking official TDSB address records…'):
            result = TDSBLookup().lookup(value, grade, year, program, confirmed_street)
        st.session_state['address_result'] = result
        if result['status'] == 'ambiguous':
            st.session_state['pending_address'] = value
        if result['status'] == 'matched':
            matches = {r['school_code'] for r in result['schools']}
            available = comparison_schools(result)
            st.session_state['pilot_schools'] = [s['id'] for s in available if s['id'].removeprefix('tdsb-') in matches or s['profile_url'].split('schno=')[-1] in matches]
    except (LookupUnavailable, ValueError) as error:
        st.error(str(error))

with st.form('address'):
    address = st.text_input('Full home address', placeholder='Street number, street name, Toronto; omit apartment number')
    submitted = st.form_submit_button('Find schools for this address')
if submitted:
    search_address(address)

result = st.session_state.get('address_result')
if result:
    status = result['status']
    if status == 'ambiguous':
        st.info('More than one official street matches. Select the municipality before searching.')
        chosen = st.selectbox('Official street', result['candidates'])
        if st.button('Search selected street'):
            search_address(st.session_state['pending_address'], chosen)
            st.rerun()
    elif status == 'street_not_found':
        st.warning('Street not recognized in the TDSB list. Include the street type and direction, separated from the city by a comma. Use the official finder if needed.')
    elif status == 'not_found':
        st.warning('TDSB returned no result for this street number. Check the address or contact the board; this does not establish that the address is ineligible.')
    elif status == 'unsupported':
        st.info(result['notes'][0])
    elif status == 'matched':
        st.success('Schools returned by the official TDSB address finder')
        st.write('Matched street address: ' + result['canonical_address'])
        st.caption('Retrieved ' + result['checked_at'] + ' · Regular programs. Requested year: ' + year + '; the source does not verify a specific school year. Confirm admission and any exceptions with the board.')
        for match in result['schools']:
            with st.container(border=True):
                st.subheader(match['name'])
                st.write(match['address'] + ' ' + match['postal_code'])
                st.write('School office: ' + match['phone'])
                if match['grade_match'] is True:
                    st.caption('The returned grade range includes your selected grade.')
                elif match['grade_match'] is False:
                    st.caption('Other grade range returned by TDSB; does not include your selected grade.')
                else:
                    st.caption('Grade range not stated in this lookup result; confirm with the school.')
                st.link_button('Official matched-school page', match['source_url'])
                for link in match['boundary_links']:
                    st.link_button(link['label'], link['url'])
                with st.expander('Full board result text'):
                    st.write(match['board_result_text'])
        for note in result['notes']:
            st.info(note)
st.link_button('Open official TDSB address finder', LOCATOR)

schools = comparison_schools(result)
valid_ids = {s['id'] for s in schools}
if 'pilot_schools' in st.session_state:
    st.session_state['pilot_schools'] = [sid for sid in st.session_state['pilot_schools'] if sid in valid_ids]
if 'pilot_schools' not in st.session_state:
    st.session_state['pilot_schools'] = [schools[0]['id']]
selected = st.multiselect('Explore or compare schools', [s['id'] for s in schools],
    key='pilot_schools', format_func=lambda sid: next(s['name'] for s in schools if s['id'] == sid))
st.caption('Profile selections can be changed independently of the address result. They do not establish admission eligibility.')

for s in schools:
    if s['id'] not in selected:
        continue
    with st.container(border=True):
        st.subheader(s['name'])
        st.write(s['address'])
        st.link_button('Official school page', s['source_url'])
        st.caption(f"Grades {s['grade_range']} · School office: {s['school_phone']}")
        grade_match = includes_grade(s, grade)
        if grade_match is False:
            st.warning(f"This school lists grades {s['grade_range']}, which do not include your selected grade.")
        elif grade_match is None:
            st.info('Grade range not stated in this lookup; confirm with the school.')
        if s.get('lookup_profile'):
            st.caption('Live lookup profile · School-specific programs and childcare have not yet been reviewed. Available ratings are shown with their source year.')
        guide = school_guidance()
        curriculum, registration, ratings = st.tabs(['Curriculum & programs', 'Registration dates', 'Fraser rating'])
        with curriculum:
            st.caption('Board-wide guidance for the selected grade; this does not confirm a program at this school.')
            st.write(guide['curriculum']['kindergarten_summary'] if grade in ('JK', 'SK') else guide['curriculum']['summary'])
            st.write(s['program_note'])
            st.link_button('School program profile', s['profile_url'])
            st.link_button('Curriculum guidance', guide['curriculum']['kindergarten_source_url'] if grade in ('JK', 'SK') else guide['curriculum']['source_url'])
        with registration:
            if grade_match is False:
                st.info('Choose a grade served by this school before using registration guidance. Contact the office for its admissions process.')
            else:
                st.write(registration_note(grade, year))
            st.link_button('Official registration guidance', guide['registration']['source_url'])
            st.write(f"Confirm dates and documents with the school office: {s['school_phone']}.")
        with ratings:
            rating = rating_for(s)
            if rating:
                st.metric('Fraser Institute rating', f"{rating['score']:.1f} / 10")
                st.caption(f"Assessment year {rating['assessment_year']} · {rating['school_level'].title()} report {rating['report_year']} · Checked {rating['checked_at']}")
                st.caption(rating['match_method'])
                st.link_button('View rating in Fraser report', rating['source_url'] + f"#page={rating['pdf_page']}")
            else:
                st.write(guide['ratings']['score_note'])
            st.write(guide['ratings']['fraser_note'])
            st.link_button('View Fraser school report', guide['ratings']['fraser_url'])
        st.caption('School profile and guidance checked ' + s['profile_checked_at'])
        with st.expander('Optional before- and after-school childcare'):
            c = s.get('childcare')
            if not c:
                st.write('Childcare details have not been reviewed for this school. Contact the school office for available providers.')
            else:
                st.write('**Provider:** ' + c['name'])
                st.write(c['program_note'])
                st.write('**Hours:** ' + c['hours_note'])
                st.write('**Spaces:** ' + c['vacancy_note'])
                st.write('**Contact:** ' + c['phone'])
                st.caption('Childcare is separate from school registration. Checked ' + c['checked_at'])
                st.link_button('Childcare source', c['source_url'])

st.subheader('Ask about selected schools')
st.caption('Try “What do children learn?”, “When can I register?” or “What are the school ratings?” Do not include your home address in the question.')
question = st.chat_input('Ask a school or childcare question', disabled=not selected)
if question:
    with st.chat_message('user'):
        st.write(question)
    with st.chat_message('assistant'):
        try:
            with st.spinner('Checking sources…'):
                result = build_graph().invoke({'question': question, 'school_ids': selected, 'grade': grade, 'year': year, 'school_records': [s for s in schools if s['id'] in selected]})
            st.caption(result['mode'])
            st.markdown(result['answer'])
            for i, e in enumerate(result.get('evidence', []), 1):
                with st.expander(f"[{i}] {e['title']}"):
                    st.write(e['text'])
                    st.link_button('View source', e['source_url'])
        except Exception:
            st.error('Unable to complete document search. Check model configuration and run ingest.py; directory information remains available.')
