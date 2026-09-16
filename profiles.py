"""Merge reviewed profiles with public school records from the current lookup."""
import re
from core import directory


def comparison_schools(result=None):
    schools = directory()
    by_code = {s['profile_url'].split('schno=')[-1]: s for s in schools}
    if not result or result.get('status') != 'matched':
        return schools
    for match in result.get('schools', []):
        code = match['school_code']
        if code in by_code:
            continue
        bounds = match.get('grade_range')
        school = {
            'id': 'tdsb-' + code, 'name': match['name'],
            'address': match['address'], 'school_phone': match.get('phone') or 'Not listed',
            'source_url': match['source_url'], 'profile_url': match['source_url'],
            'grade_range': '–'.join(bounds) if bounds else 'Not stated in lookup',
            'profile_checked_at': result['checked_at'],
            'program_note': 'This school was returned by the official regular-program address lookup. School-specific curriculum and program details have not been reviewed; consult its official page.',
            'childcare': None, 'lookup_profile': True,
            'boundary_links': match.get('boundary_links', []),
        }
        schools.append(school)
        by_code[code] = school
    return schools


def includes_grade(school, grade):
    match = re.fullmatch(r'(JK|SK|\d+)–(\d+)', school['grade_range'])
    if not match:
        return None
    values = {'JK': -1, 'SK': 0, **{str(i): i for i in range(1, 13)}}
    return values[match[1]] <= values[grade] <= values[match[2]]
