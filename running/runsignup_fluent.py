'''
runsignup_fluent - fluent access to runsignup.com
===================================================
'''

# pypi
from universalclient import Client as UniversalClient

class RunSignupFluent(UniversalClient):

    '''
    Fluent interface to RunSignUp API -- see https://universal-client.readthedocs.io
    '''
    def __init__(self, key=None, secret=None, api_reg_token=None, api_reg_secret=None, debug=False):
        '''
        initialize RunSignUp Fluent client

        :param key: api key for RunSignUp
        :param secret: api secret for RunSignUp
        :param api_reg_token: API caller registration token, sent as rsu_api_reg GET parameter -- see
            https://info.runsignup.com/2026/07/17/new-api-registration-requirements/
        :param api_reg_secret: API caller registration secret, sent as X-RSU-API-REG-SECRET header
        :param debug: debug flag
        '''

        self._params = params = {'api_key'    : key,
                                 'api_secret' : secret,
                                 'format'     : 'json' }
        if api_reg_token:
            params['rsu_api_reg'] = api_reg_token

        client_kwargs = {'url': 'https://api.runsignup.com/rest', 'params': params}
        if api_reg_secret:
            client_kwargs['headers'] = {'X-RSU-API-REG-SECRET': api_reg_secret}

        super().__init__(**client_kwargs)
