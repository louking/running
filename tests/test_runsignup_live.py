'''
opt-in live smoke tests against the real RunSignUp.com API

these hit the network and are skipped by default. to run them, set environment
variables and run:

    pytest tests/test_runsignup_live.py -v

RSU_TEST_RACE_ID (a real, public race_id on runsignup.com) is required for the
public/unauthenticated tests. RSU_KEY / RSU_SECRET (and optionally
RSU_API_REG_TOKEN / RSU_API_REG_SECRET, per
https://info.runsignup.com/2026/07/17/new-api-registration-requirements/) enable
the authenticated tests. RSU_TEST_CLUB_ID (a real club_id the RSU_KEY/RSU_SECRET
account can administer) additionally enables the bad-credential rejection tests.
'''

import os

import pytest

from running.runsignup import RunSignUp, accessError
from running.runsignup_fluent import RunSignupFluent

RACE_ID = os.environ.get('RSU_TEST_RACE_ID')
CLUB_ID = os.environ.get('RSU_TEST_CLUB_ID')
KEY = os.environ.get('RSU_KEY')
SECRET = os.environ.get('RSU_SECRET')
API_REG_TOKEN = os.environ.get('RSU_API_REG_TOKEN')
API_REG_SECRET = os.environ.get('RSU_API_REG_SECRET')

needs_race_id = pytest.mark.skipif(not RACE_ID, reason='set RSU_TEST_RACE_ID to run live tests')
needs_credentials = pytest.mark.skipif(
    not (KEY and SECRET), reason='set RSU_KEY/RSU_SECRET to run authenticated live tests'
)
needs_api_reg = pytest.mark.skipif(
    not (API_REG_TOKEN and API_REG_SECRET),
    reason='set RSU_API_REG_TOKEN/RSU_API_REG_SECRET to run registered-caller live tests',
)
needs_club_id = pytest.mark.skipif(
    not CLUB_ID, reason='set RSU_TEST_CLUB_ID to run bad-credential rejection live tests'
)


@needs_race_id
class TestRunSignUpLive:
    def test_getrace_public(self):
        with RunSignUp() as rsu:
            race = rsu.getrace(int(RACE_ID))
        assert str(race['race_id']) == str(RACE_ID)

    @needs_api_reg
    def test_getrace_with_api_reg(self):
        with RunSignUp(api_reg_token=API_REG_TOKEN, api_reg_secret=API_REG_SECRET) as rsu:
            race = rsu.getrace(int(RACE_ID))
        assert str(race['race_id']) == str(RACE_ID)

    @needs_credentials
    def test_getrace_authenticated(self):
        with RunSignUp(key=KEY, secret=SECRET, api_reg_token=API_REG_TOKEN, api_reg_secret=API_REG_SECRET) as rsu:
            race = rsu.getrace(int(RACE_ID))
        assert str(race['race_id']) == str(RACE_ID)


@needs_race_id
class TestRunSignupFluentLive:
    def test_get_race_public(self):
        rsu = RunSignupFluent()
        resp = rsu.race._(int(RACE_ID)).get()
        assert resp.status_code == 200
        assert str(resp.json()['race']['race_id']) == str(RACE_ID)

    @needs_credentials
    def test_get_race_authenticated(self):
        rsu = RunSignupFluent(key=KEY, secret=SECRET, api_reg_token=API_REG_TOKEN, api_reg_secret=API_REG_SECRET)
        resp = rsu.race._(int(RACE_ID)).get()
        assert resp.status_code == 200
        assert str(resp.json()['race']['race_id']) == str(RACE_ID)


@needs_credentials
@needs_club_id
class TestBadPasswordLive:
    '''confirms a wrong secret (right key, wrong password) is actually rejected by the live API'''

    def test_runsignup_wrong_secret_rejected(self):
        with RunSignUp(key=KEY, secret=SECRET + '-wrong-for-testing') as rsu:
            with pytest.raises(accessError):
                rsu.members(int(CLUB_ID))

    def test_runsignup_fluent_wrong_secret_rejected(self):
        rsu = RunSignupFluent(key=KEY, secret=SECRET + '-wrong-for-testing')
        resp = rsu.club._(int(CLUB_ID)).members.get()
        assert resp.status_code != 200 or 'error' in resp.json()


@needs_credentials
@needs_club_id
class TestBadApiRegTokenLive:
    '''
    confirms that when an api_reg_token/api_reg_secret IS supplied, RunSignUp actually validates it
    and rejects a wrong one -- distinct from omitting it entirely, which RunSignUp currently accepts
    since registered-caller credentials aren't required until 2027-01-01 per
    https://info.runsignup.com/2026/07/17/new-api-registration-requirements/. This test only tells you
    whether a *provided* bad token/secret is checked, not whether one is required yet.
    '''

    def test_runsignup_wrong_api_reg_rejected(self):
        with RunSignUp(key=KEY, secret=SECRET,
                        api_reg_token='bad-token-for-testing', api_reg_secret='bad-secret-for-testing') as rsu:
            with pytest.raises(accessError):
                rsu.members(int(CLUB_ID))

    def test_runsignup_fluent_wrong_api_reg_rejected(self):
        rsu = RunSignupFluent(key=KEY, secret=SECRET,
                               api_reg_token='bad-token-for-testing', api_reg_secret='bad-secret-for-testing')
        resp = rsu.club._(int(CLUB_ID)).members.get()
        assert resp.status_code != 200 or 'error' in resp.json()
