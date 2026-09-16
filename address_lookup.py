"""Read-only adapter for the public TDSB regular-program address finder.

No address is sent to a model, stored on disk, or cached across users. The
public HTML form is not a versioned API; unexpected markup fails closed.
"""
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, Request

from core import LOCATOR


class LookupUnavailable(RuntimeError):
    pass


class Node:
    def __init__(self, tag='', attrs=None):
        self.tag, self.attrs, self.children = tag, dict(attrs or []), []

    def text(self):
        return ' '.join(' '.join(c.text() if isinstance(c, Node) else c for c in self.children).split())

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'input', 'img', 'image', 'br', 'hr', 'meta', 'link', 'source', 'area', 'wbr', 'embed', 'base', 'param', 'col'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def by_id(self, identifier):
        return next((n for n in self.root.walk() if n.attrs.get('id') == identifier), None)


def safe_url(href):
    url = urljoin(LOCATOR, href)
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.hostname != 'www.tdsb.on.ca':
        raise LookupUnavailable('The board returned an unexpected link. Use its official finder.')
    return url


def parse_form(html):
    page = Page(html)
    fields = {n.attrs['name']: n.attrs.get('value', '') for n in page.root.walk()
              if n.tag == 'input' and n.attrs.get('type') == 'hidden' and n.attrs.get('name')}
    names = {}
    for identifier in ('txtStreetNumber', 'txtStreet', 'btnStreetSearch'):
        node = page.by_id(identifier)
        if node is None or not node.attrs.get('name'):
            raise LookupUnavailable('The board lookup form changed. Use the official finder.')
        names[identifier] = node.attrs['name']
    match = re.search(r'var\s+streetname\s*=\s*(\[.*?\])\s*;', html, re.S)
    if not match or not fields.get('__VIEWSTATE'):
        raise LookupUnavailable('The board lookup form changed. Use the official finder.')
    try:
        streets = json.loads(match.group(1))
    except ValueError:
        raise LookupUnavailable('The board street list could not be read.') from None
    if not streets or not all(isinstance(s, str) for s in streets):
        raise LookupUnavailable('The board street list could not be read.')
    return fields, names, sorted(set(streets))


ALIASES = {'street':'st', 'avenue':'ave', 'road':'rd', 'drive':'dr', 'lane':'ln',
           'parkway':'pkwy', 'pky':'pkwy', 'boulevard':'blvd', 'crescent':'cres',
           'court':'crt', 'ct':'crt', 'place':'pl', 'terrace':'terr',
           'north':'n', 'south':'s', 'east':'e', 'west':'w'}


def normalized(text):
    tokens = re.sub(r'[^\w\s]', ' ', text.casefold()).split()
    return ' '.join(ALIASES.get(t, t) for t in tokens)


def address_parts(address):
    text = address.strip()
    if len(text) > 240:
        raise ValueError('Please enter only the street number, street name and city.')
    # A unit prefix must be explicit; a bare 12-34 could be a civic-number range.
    text = re.sub(r'^(?:unit|apt|apartment|suite)\s+[\w-]+\s*[,;-]\s*', '', text, flags=re.I)
    match = re.fullmatch(r'(\d+[A-Za-z]?)\s+(.+)', text)
    if not match:
        raise ValueError('Enter a street number and name, such as 26 Joyce Parkway, North York. Put apartment details after the street or omit them.')
    return match.group(1), match.group(2)


def street_candidates(street_text, streets):
    parts = [p.strip() for p in street_text.split(',')]
    street = re.split(r'\s+(?:unit|apt|apartment|suite)\b', parts[0], flags=re.I)[0]
    # Common pasted postal-code/province suffixes do not form part of a street.
    street = re.sub(r'\s+[A-Z]\d[A-Z]\s?\d[A-Z]\d$', '', street, flags=re.I)
    target = normalized(street)
    matches = [s for s in streets if normalized(s.split(',')[0]) == target]
    # Respect a recognized municipality, but never guess a fuzzy street name.
    cities = {normalized(s.split(',')[-1]) for s in streets if ',' in s}
    cities.update({'toronto', 'north york', 'york', 'east york', 'etobicoke', 'scarborough'})
    supplied = []
    for part in parts[1:]:
        if re.match(r'^(?:unit|apt|apartment|suite)\b', part, re.I):
            continue
        part = re.sub(r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b', '', part, flags=re.I)
        part = re.sub(r'\b(?:ON|Ontario|Canada)\b', '', part, flags=re.I).strip()
        if not part:
            continue
        city = normalized(part)
        if city not in cities:
            return []
        supplied.append(city)
    if supplied and supplied[0] != 'toronto':
        matches = [s for s in matches if normalized(s.split(',')[-1]) == supplied[0]]
    return matches


def parse_results(html):
    page = Page(html)
    panel = page.by_id('pnlResults')
    message = page.by_id('lblMessage')
    if panel is None:
        if message is not None and 'cannot find' in message.text().lower():
            return {'status': 'not_found', 'schools': [], 'notes': []}
        raise LookupUnavailable('The board did not return a recognized result. Use the official finder.')
    schools = []
    for card in panel.walk():
        if 'divSchool' not in card.attrs.get('class', '').split():
            continue
        nodes = list(card.walk())
        link = next((n for n in nodes if n.tag == 'a' and 'schoolName' in n.attrs.get('class', '').split()), None)
        if link is None:
            raise LookupUnavailable('A school result could not be read. Use the official finder.')
        url = safe_url(link.attrs.get('href', ''))
        code = re.search(r'/schno/(\d+)', url, re.I)
        if not code:
            raise LookupUnavailable('A school identifier could not be read.')
        def field(fragment):
            node = next((n for n in nodes if fragment in n.attrs.get('id', '')), None)
            return node.text() if node else ''
        title = link.text()
        grades = re.search(r'\((JK|SK|\d+)\s*[-–]\s*(\d+)\)', title, re.I)
        grade_range = [grades.group(1).upper(), grades.group(2)] if grades else None
        if grades:
            title = title[:grades.start()].strip()
        links = [{'label': n.text(), 'url': safe_url(n.attrs['href'])} for n in nodes
                 if n.tag == 'a' and any(term in n.attrs.get('id', '') for term in ('hylBoundary', 'hylTextVersion'))]
        schools.append({'school_code': code.group(1), 'name': title, 'grade_range': grade_range,
                        'address': field('lblAddress'), 'postal_code': field('lblPostalcode'),
                        'phone': field('lblPhone'), 'source_url': url, 'boundary_links': links,
                        'board_result_text': card.text()})
    if not schools:
        raise LookupUnavailable('The board returned an empty or changed result. Use its official finder.')
    notes = [n.text() for n in panel.walk() if 'footnotes' in n.attrs.get('class', '').split() and n.text()]
    return {'status': 'matched', 'schools': schools, 'notes': notes}


class TDSBLookup:
    def __init__(self):
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self.opener.addheaders = [('User-Agent', 'TorontoSchoolCompass/0.1 (public school lookup)')]

    def _request(self, data=None):
        try:
            request = Request(LOCATOR, data=urlencode(data).encode() if data is not None else None)
            with self.opener.open(request, timeout=20) as response:
                safe_url(response.geturl())
                content = response.read(3_000_001)
            if len(content) > 3_000_000:
                raise ValueError('Oversized response')
            return content.decode('utf-8')
        except Exception:
            raise LookupUnavailable('The TDSB lookup is unavailable. Try again or use the official finder.') from None

    def lookup(self, address, grade='JK', year='2026–27', program='Regular', confirmed_street=None):
        if program != 'Regular':
            return {'status': 'unsupported', 'schools': [], 'notes': ['This official lookup covers regular programs only. Use the board program admissions process.']}
        number, street = address_parts(address)
        fields, names, streets = parse_form(self._request())
        candidates = street_candidates(street, streets)
        if confirmed_street is not None:
            if confirmed_street not in candidates:
                raise ValueError('Choose a street from the current board matches.')
            canonical = confirmed_street
        elif len(candidates) != 1:
            return {'status': 'ambiguous' if candidates else 'street_not_found', 'candidates': candidates, 'schools': [], 'notes': []}
        else:
            canonical = candidates[0]
        fields.update({names['txtStreetNumber']: number, names['txtStreet']: canonical, names['btnStreetSearch']: 'Search'})
        result = parse_results(self._request(fields))
        result.update({'canonical_address': f'{number} {canonical}', 'source_url': LOCATOR,
                       'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                       'requested_grade': grade, 'requested_year': year, 'program': 'Regular',
                       'year_verified': False})
        # Do not discard schools with unspecified grades or infer grades from level names.
        values = {'JK': -1, 'SK': 0, **{str(i): i for i in range(1, 13)}}
        for school in result['schools']:
            bounds = school['grade_range']
            school['grade_match'] = (values[bounds[0]] <= values[grade] <= values[bounds[1]]) if bounds and grade in values and all(b in values for b in bounds) else None
        return result
