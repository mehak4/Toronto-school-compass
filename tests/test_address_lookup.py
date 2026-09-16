from pathlib import Path
import pytest
from address_lookup import TDSBLookup, LookupUnavailable, parse_results, address_parts, street_candidates

FIXTURE = (Path(__file__).parent / 'fixtures/tdsb-public-school-result.html').read_text()
FORM = '''<script>var streetname = ["Joyce Pkwy, North York", "Main St, Toronto", "Main St, York"];</script>
<input type="hidden" name="__VIEWSTATE" value="test-state">
<input id="txtStreetNumber" name="module$number"><input id="txtStreet" name="module$street">
<input id="btnStreetSearch" name="module$search">'''


def client_with_responses(monkeypatch, result=FIXTURE):
    client = TDSBLookup()
    calls = []
    def request(data=None):
        calls.append(data)
        return FORM if data is None else result
    monkeypatch.setattr(client, '_request', request)
    return client, calls


def test_actual_public_response_and_grade_filter(monkeypatch):
    client, calls = client_with_responses(monkeypatch)
    result = client.lookup('26 Joyce Parkway, Toronto', 'JK', '2027–28')
    assert result['status'] == 'matched'
    assert result['canonical_address'] == '26 Joyce Pkwy, North York'
    assert result['year_verified'] is False
    assert [s['school_code'] for s in result['schools']] == ['3182', '3190', '3437']
    assert [s['grade_match'] for s in result['schools']] == [True, None, False]
    assert calls[1]['module$street'] == 'Joyce Pkwy, North York'
    assert calls[1]['module$number'] == '26'
    assert all('tdsb.on.ca' in link['url'] for s in result['schools'] for link in s['boundary_links'])


def test_ambiguous_and_unrecognized_streets_do_not_post(monkeypatch):
    client, calls = client_with_responses(monkeypatch)
    result = client.lookup('1 Main Street, Toronto')
    assert result['status'] == 'ambiguous' and len(calls) == 1
    result = client.lookup('1 Fictional Street')
    assert result['status'] == 'street_not_found' and len(calls) == 2
    client.lookup('1 Main Street', confirmed_street='Main St, York')
    assert calls[-1]['module$street'] == 'Main St, York'
    with pytest.raises(ValueError):
        client.lookup('1 Main Street', confirmed_street='Joyce Pkwy, North York')


def test_invalid_address_and_program_make_no_request(monkeypatch):
    client, calls = client_with_responses(monkeypatch)
    with pytest.raises(ValueError):
        client.lookup('Toronto')
    assert client.lookup('26 Joyce Parkway', program='French Immersion')['status'] == 'unsupported'
    assert not calls
    assert address_parts('Unit 12, 26 Joyce Parkway') == ('26', 'Joyce Parkway')
    with pytest.raises(ValueError):
        address_parts('12-26 Joyce Parkway')


def test_no_match_and_changed_markup_fail_closed(monkeypatch):
    client, _ = client_with_responses(monkeypatch, '<span id="lblMessage">Cannot find that address</span>')
    assert client.lookup('99999 Joyce Parkway')['status'] == 'not_found'
    for html in ['<html>Maintenance</html>', '<div id="pnlResults"></div>', FIXTURE.replace('/FindYour/Schools/schno/3182', 'https://example.invalid/school')]:
        with pytest.raises(LookupUnavailable):
            parse_results(html)


def test_normalization_is_exact_not_fuzzy():
    streets = ['Joyce Pkwy, North York']
    assert street_candidates('Joyce Pky, North York, ON, M6B 2S9', streets) == streets
    assert street_candidates('Joyce Parkway, Toronto', streets) == streets
    assert street_candidates('Joyce Parkway East, Toronto', streets) == []
    assert street_candidates('Joyce Parkway, Scarborough', streets) == []
    assert street_candidates('Joyce Parkway, Ottawa', streets) == []
    assert street_candidates('Joyce Parkway, North York ON M6B 2S9', streets) == streets


def test_ui_lookup_persists_then_invalidates(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import address_lookup
    result = parse_results(FIXTURE)
    result.update(canonical_address='26 Joyce Pkwy, North York', checked_at='2026-09-12T00:00:00+00:00')
    for s in result['schools']:
        s['grade_match'] = True if s['school_code'] == '3182' else None
    seen=[]
    def lookup(self, *args):
        seen.append(args)
        return result
    monkeypatch.setattr(address_lookup.TDSBLookup, 'lookup', lookup)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.text_input[0].set_value('26 Joyce Parkway')
    app.button[0].click().run()
    assert not app.exception
    assert app.success and any(s.value == 'Lawrence Heights Middle School' for s in app.subheader)
    assert app.multiselect[0].value == ['joyce', 'tdsb-3190', 'tdsb-3437']
    assert 'Glen Park Public School' in app.multiselect[0].options
    app.multiselect[0].set_value(['tdsb-3190', 'tdsb-3437']).run()
    assert not app.exception
    assert len(app.tabs) == 6
    assert any('Childcare details have not been reviewed' in m.value for m in app.markdown)
    app.selectbox[1].set_value('2027–28').run()
    assert not app.success
    assert app.multiselect[0].value == []
    assert 'Lawrence Heights Middle School' not in app.multiselect[0].options
    assert len(seen)==1
    def unavailable(self,*args):
        raise LookupUnavailable('The TDSB lookup is unavailable.')
    monkeypatch.setattr(address_lookup.TDSBLookup,'lookup',unavailable)
    app.button[0].click().run()
    assert app.error and not app.success and not app.exception
