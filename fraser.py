"""Reviewed TDSB mappings plus conservative matching against Fraser report rows."""
from functools import lru_cache
import json
import re
import unicodedata
from urllib.parse import urlparse
from core import ROOT


@lru_cache(maxsize=8)
def _read(path, modified):
    return json.loads(path.read_text())


def _data(name):
    path = ROOT / 'data' / name
    return _read(path, path.stat().st_mtime_ns)


def _normalize(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return ''.join(c for c in text if c.isalnum())


def _school_name(name):
    # Strip only terminal TDSB institution labels, retaining distinctive name words.
    suffix = r'\s+(?:Junior Public School|Senior Public School|Junior and Senior Public School|Public School|Community School|Elementary and Middle School|Middle School|Collegiate Institute|Secondary School|School of the Arts|Elementary School)$'
    return _normalize(re.sub(suffix, '', name, flags=re.I))


def _level(school):
    grades = school.get('grade_range', '')
    match = re.fullmatch(r'(JK|SK|\d+)\s*[–-]\s*(\d+)', grades, re.I)
    if match:
        low = 0 if match[1].upper() in ('JK', 'SK') else int(match[1])
        high = int(match[2])
        if high <= 8:
            return 'elementary'
        if low >= 9:
            return 'secondary'
    return None


def rating_for(school):
    url = school.get('profile_url') or school.get('source_url', '')
    if urlparse(url).hostname not in ('www.tdsb.on.ca', 'tdsb.on.ca'):
        return None
    match = re.search(r'(?:schno=|/schno/)(\d+)', url, re.I)
    if not match:
        return None
    record = _data('fraser_ratings.json').get(match[1])
    if record:
        return dict(record, match_method='Reviewed school-code mapping') if school['name'] == record['school_name'] else None
    level = _level(school)
    if not level:
        return None
    address = school.get('address', '')
    cities = [city for city in ('Toronto','North York','Scarborough','Etobicoke','East York','York')
              if re.search(r'(?:^|,)\s*'+re.escape(city)+r'\s*(?:,|$)', address, re.I)]
    if len(cities) != 1:
        return None
    name = _school_name(school['name'])
    candidates = [r for r in _data('fraser_catalog.json')['ratings']
                  if _normalize(r['fraser_name']) == name and r['school_level'] == level
                  and _normalize(r['fraser_city']) == _normalize(cities[0])]
    if len(candidates) != 1 or candidates[0]['score'] is None:
        return None
    return dict(candidates[0], school_name=school['name'], match_method='Automatic exact name, municipality and school-level match')


def rating_text(school):
    rating = rating_for(school)
    if not rating:
        return 'Fraser numeric rating not verified for this school. No score is displayed.'
    return (f"Fraser Institute rating: {rating['score']:.1f}/10; assessment year {rating['assessment_year']}; "
            f"{rating['school_level']} report edition {rating['report_year']}. {rating['match_method']}. "
            f"[Fraser source, printed page {rating['printed_page']}]({rating['source_url']}#page={rating['pdf_page']}).")
