'''
mocked (no network) tests for running.runsignup.RunSignupBase / RunSignUp

covers the RunSignupBase/RunSignUp split and the api_reg_token/api_reg_secret
wiring required per https://info.runsignup.com/2026/07/17/new-api-registration-requirements/
'''

from urllib.parse import urlparse, parse_qs

import pytest
import responses

from running.runsignup import RunSignUp, accessError, parameterError

KEY = 'testkey'
SECRET = 'testsecret'
REG_TOKEN = 'testregtoken'
REG_SECRET = 'testregsecret'


def _qs(url):
    return parse_qs(urlparse(url).query)


class TestInitValidation:
    def test_key_without_secret(self):
        with pytest.raises(parameterError):
            RunSignUp(key=KEY)

    def test_secret_without_key(self):
        with pytest.raises(parameterError):
            RunSignUp(secret=SECRET)

    def test_api_reg_token_without_secret(self):
        with pytest.raises(parameterError):
            RunSignUp(key=KEY, secret=SECRET, api_reg_token=REG_TOKEN)

    def test_api_reg_secret_without_token(self):
        with pytest.raises(parameterError):
            RunSignUp(key=KEY, secret=SECRET, api_reg_secret=REG_SECRET)

    def test_no_credentials_is_userpriv(self):
        rsu = RunSignUp()
        assert rsu.userpriv is True
        assert rsu.credentials_type == 'none'

    def test_key_secret_sets_credentials_type(self):
        rsu = RunSignUp(key=KEY, secret=SECRET)
        assert rsu.userpriv is False
        assert rsu.credentials_type == 'key'


class TestOpen:
    def test_open_sets_api_key_secret_only(self):
        with RunSignUp(key=KEY, secret=SECRET) as rsu:
            assert rsu.client_credentials == {'api_key': KEY, 'api_secret': SECRET}
            assert 'X-RSU-API-REG-SECRET' not in rsu.session.headers

    def test_open_sets_api_reg_token_as_param_and_secret_as_header(self):
        with RunSignUp(key=KEY, secret=SECRET, api_reg_token=REG_TOKEN, api_reg_secret=REG_SECRET) as rsu:
            assert rsu.client_credentials == {
                'api_key': KEY, 'api_secret': SECRET, 'rsu_api_reg': REG_TOKEN,
            }
            assert rsu.session.headers['X-RSU-API-REG-SECRET'] == REG_SECRET

    def test_open_userpriv_with_api_reg_only(self):
        # public endpoint access, but still registered as an API caller
        with RunSignUp(api_reg_token=REG_TOKEN, api_reg_secret=REG_SECRET) as rsu:
            assert rsu.client_credentials == {'rsu_api_reg': REG_TOKEN}
            assert rsu.session.headers['X-RSU-API-REG-SECRET'] == REG_SECRET


class TestRsuget:
    @responses.activate
    def test_sends_credentials_and_reg_token_on_request(self):
        race_id = 12345
        responses.add(
            responses.GET,
            f'https://api.runsignup.com/rest/race/{race_id}',
            json={'race': {'race_id': race_id, 'name': 'Test Race'}},
            status=200,
        )
        with RunSignUp(key=KEY, secret=SECRET, api_reg_token=REG_TOKEN, api_reg_secret=REG_SECRET) as rsu:
            race = rsu.getrace(race_id)

        assert race == {'race_id': race_id, 'name': 'Test Race'}
        sent = responses.calls[0].request
        assert sent.headers['X-RSU-API-REG-SECRET'] == REG_SECRET
        params = _qs(sent.url)
        assert params['api_key'] == [KEY]
        assert params['api_secret'] == [SECRET]
        assert params['rsu_api_reg'] == [REG_TOKEN]
        assert params['format'] == ['json']

    @responses.activate
    def test_public_endpoint_sends_no_credentials(self):
        race_id = 999
        responses.add(
            responses.GET,
            f'https://api.runsignup.com/rest/race/{race_id}',
            json={'race': {'race_id': race_id}},
            status=200,
        )
        with RunSignUp() as rsu:
            race = rsu.getrace(race_id)

        assert race == {'race_id': race_id}
        params = _qs(responses.calls[0].request.url)
        assert 'api_key' not in params
        assert 'rsu_api_reg' not in params
        assert 'X-RSU-API-REG-SECRET' not in responses.calls[0].request.headers

    @responses.activate
    def test_error_response_raises_accesserror(self):
        race_id = 1
        responses.add(
            responses.GET,
            f'https://api.runsignup.com/rest/race/{race_id}',
            json={'error': {'error_code': 100, 'error_msg': 'bad request'}},
            status=200,
        )
        with RunSignUp() as rsu:
            with pytest.raises(accessError):
                rsu.getrace(race_id)

    @responses.activate
    def test_http_error_raises_accesserror(self):
        race_id = 1
        responses.add(
            responses.GET,
            f'https://api.runsignup.com/rest/race/{race_id}',
            json={},
            status=500,
        )
        with RunSignUp() as rsu:
            with pytest.raises(accessError):
                rsu.getrace(race_id)


class TestMembersPagination:
    @responses.activate
    def test_paginates_until_short_page(self):
        club_id = 42
        url = f'https://api.runsignup.com/rest/club/{club_id}/members'
        page1 = {'club_members': [{'user': {'user_id': i}} for i in range(100)]}
        page2 = {'club_members': [{'user': {'user_id': 100}}]}
        responses.add(responses.GET, url, json=page1, status=200)
        responses.add(responses.GET, url, json=page2, status=200)

        with RunSignUp(key=KEY, secret=SECRET) as rsu:
            members = rsu.members(club_id)

        assert len(members) == 101
        assert len(responses.calls) == 2
