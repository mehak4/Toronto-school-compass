"""Deterministic facts: never infer enrollment or turn missing prices into zero."""
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
LOCATOR = 'https://www.tdsb.on.ca/Find-your/School/By-Home-Address'

def school_guidance():
    return json.loads((ROOT / 'data/school_guidance.json').read_text())

def registration_note(grade, year):
    registration = school_guidance()['registration']
    notes = [f'School year: {year}.']
    if grade in ('JK', 'SK'):
        notes.append(registration['english_note'])
    notes.append(registration['regular_note'])
    if grade == 'JK' and year == registration['french_entry_year']:
        notes.append(f"Early French Immersion applications for September 2027: {registration['french_opens']} to {registration['french_closes']}. {registration['french_note']}")
    return ' '.join(notes)

def directory():
    # In-memory SQLite keeps the packaged source of truth easy to review.
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE schools (id TEXT PRIMARY KEY, record TEXT)')
    for s in json.loads((ROOT / 'data/schools.json').read_text()):
        db.execute('INSERT INTO schools VALUES (?, ?)', (s['id'], json.dumps(s)))
    rows = [json.loads(r[0]) for r in db.execute('SELECT record FROM schools')]
    db.close()
    return rows

def address_status(address):
    if not re.match(r'^\s*\d+\s+\S+', address):
        return 'Enter a street number and street name.'
    return 'Assignment unverified. Use the official TDSB finder, then select the returned school below. This prototype does not perform automatic address matching.'

def fee_is_complete(fee):
    return fee.get('amount') is not None and all(
        fee.get(field) for field in ('unit', 'source_url', 'effective_date')
    )

def fee_label(fee):
    if fee.get('amount') is None:
        return 'Cost not published in checked sources — contact provider'
    if not fee_is_complete(fee):
        return 'Incomplete fee record — contact provider'
    return f"CAD ${fee['amount']:.2f} per {fee['unit']} (effective {fee['effective_date']})"

def estimate_month(fee, days):
    if not fee_is_complete(fee) or fee.get('unit') != 'day':
        return None
    if not 1 <= days <= 31:
        raise ValueError('Days must be between 1 and 31')
    return round(fee['amount'] * days, 2)

def route_question(question):
    q = question.lower()
    address_like = re.search(r'\b\d+\s+(?:[a-z]+\s+){0,4}(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|parkway|pky|boulevard|blvd|court|ct|crescent|cres|way)\b', q)
    if address_like or any(x in q for x in ['assigned', 'boundary', 'catchment', 'eligible', 'can my child attend', 'home address', 'designated']):
        return 'boundary'
    if any(x in q for x in ['register', 'registration', 'deadline', 'application', 'enrol', 'admission']):
        return 'registration'
    if any(x in q for x in ['rating', 'ranking', 'ranked', 'eqao', 'fraser', 'best school', 'better school']):
        return 'ratings'
    if any(x in q for x in ['cost', 'fee', 'price', 'monthly', 'how much', 'cheapest']):
        return 'fees'
    if any(x in q for x in ['vacan', 'space', 'waitlist', 'spot available']):
        return 'vacancy'
    return 'retrieve'
