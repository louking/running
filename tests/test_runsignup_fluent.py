'''
mocked (no network) tests for running.runsignup_fluent.RunSignupFluent

covers the api_reg_token/api_reg_secret wiring required per
https://info.runsignup.com/2026/07/17/new-api-registration-requirements/
'''

from urllib.parse import urlparse, parse_qs

import responses

from running.runsignup_fluent import RunSignupFluent

KEY = 'testkey'
SECRET = 'testsecret'
REG_TOKEN = 'testregtoken'
REG_SECRET = 'testregsecret'


def _qs(url):
    return parse_qs(urlparse(url).query)


class TestConstructorArgs:
    def test_key_secret_only(self):
        rsu = RunSignupFluent(key=KEY, secret=SECRET)
        args = rsu.getArgs()
        assert args['params'] == {'api_key': KEY, 'api_secret': SECRET, 'format': 'json'}
        assert 'headers' not in args

    def test_api_reg_token_added_to_params(self):
        rsu = RunSignupFluent(key=KEY, secret=SECRET, api_reg_token=REG_TOKEN)
        args = rsu.getArgs()
        assert args['params']['rsu_api_reg'] == REG_TOKEN
        assert 'headers' not in args

    def test_api_reg_secret_added_as_header(self):
        rsu = RunSignupFluent(key=KEY, secret=SECRET, api_reg_token=REG_TOKEN, api_reg_secret=REG_SECRET)
        args = rsu.getArgs()
        assert args['headers'] == {'X-RSU-API-REG-SECRET': REG_SECRET}


class TestRequestWiring:
    @responses.activate
    def test_get_sends_credentials_and_reg_token(self):
        race_id = 12345
        responses.add(
            responses.GET,
            f'https://api.runsignup.com/rest/race/{race_id}',
            json={'race': {'race_id': race_id, 'name': 'Test Race'}},
            status=200,
        )
        rsu = RunSignupFluent(key=KEY, secret=SECRET, api_reg_token=REG_TOKEN, api_reg_secret=REG_SECRET)
        resp = rsu.race._(race_id).get()

        assert resp.json() == {'race': {'race_id': race_id, 'name': 'Test Race'}}
        sent = responses.calls[0].request
        assert sent.headers['X-RSU-API-REG-SECRET'] == REG_SECRET
        params = _qs(sent.url)
        assert params['api_key'] == [KEY]
        assert params['api_secret'] == [SECRET]
        assert params['rsu_api_reg'] == [REG_TOKEN]
        assert params['format'] == ['json']

    @responses.activate
    def test_get_without_api_reg_sends_no_header(self):
        race_id = 999
        responses.add(
            responses.GET,
            f'https://api.runsignup.com/rest/race/{race_id}',
            json={'race': {'race_id': race_id}},
            status=200,
        )
        rsu = RunSignupFluent(key=KEY, secret=SECRET)
        rsu.race._(race_id).get()

        sent = responses.calls[0].request
        assert 'X-RSU-API-REG-SECRET' not in sent.headers
        params = _qs(sent.url)
        assert 'rsu_api_reg' not in params
