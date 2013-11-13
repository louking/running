#!/usr/bin/python
###########################################################################################
#   athlinks - access methods for athlinks.com
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/12/13    Lou King    Create
#
#   Copyright 2012 Lou King
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###########################################################################################
'''
athlinks - access methods for athlinks.com
===================================================
'''

# standard
import pdb
import argparse
import os.path
import urllib
import json
import os.path

# pypi
import httplib2

# github

# other

# home grown
from loutilities import apikey
from running import accessError

# access stuff
ATHLINKS_URL = 'http://api.athlinks.com'
RESULTS_SEARCH = 'Results/search'
RACE_SEARCH = 'races/{id}'
COURSE_SEARCH = 'races/{raceid}/{courseid}'
MEMBER_SEARCH = 'athletes/results/{id}'
MEMBER_DETAILS = 'athletes/details/{id}'
ATH_CAT_RUNNING = 2

HTTPTIMEOUT = 5
KMPERMILE = 1.609344

########################################################################
class Athlinks():
########################################################################
    '''
    access methods for athlinks.com
    '''

    #----------------------------------------------------------------------
    def __init__(self,debug=False):
    #----------------------------------------------------------------------
        """
        initialize http and get athlinks key
        """
        # get credentials from configuration
        ak = apikey.ApiKey('Lou King','running')
        try:
            self.key = ak.getkey('athlinks')
        except apikey.unknownKey:
            raise parameterError, "'athlinks' key needs to be configured using apikey"
        
        # need http object
        self.http = httplib2.Http(timeout=HTTPTIMEOUT)

        # initial value - modify with self.setdebug(value)
        self.debug = debug
        
    #----------------------------------------------------------------------
    def setdebug(self,debugval):
    #----------------------------------------------------------------------
        '''
        set debugging attribute for this class
        
        :param debugval: set to True to enable debugging
        '''
        self.debug = debugval
        
    #----------------------------------------------------------------------
    def listathleteresults(self,name,**filt):
    #----------------------------------------------------------------------
        """
        return results which match an athlete's name
        
        :param name: name of athlete
        :param **filt: keyword parameters to filter with
        :rtype: list of athlinks Race dicts
        """
        
        # get the data for this athlete
        page = 1
        races = []
        while True:
            data = self._get(RESULTS_SEARCH,
                               pagesize=50,
                               page=page,
                               name=name,
                               includeclaimed=True
                               )
            if len(data['List']) == 0: break
            
            races += data['List']
            page += 1

        def _checkfilter(checkdict):
            for key in filt:
                if not checkdict.has_key(key) or checkdict[key] != filt[key]:
                    return False
            return True

        races = filter(_checkfilter,races)
        return races
        
    #----------------------------------------------------------------------
    def getrace(self,id):
    #----------------------------------------------------------------------
        '''
        get race record associated with id
        
        :param id: id of race
        '''
        data = self._get(RACE_SEARCH.format(id=id)
                           )
        return data
        
    #----------------------------------------------------------------------
    def getcourse(self,raceid,courseid):
    #----------------------------------------------------------------------
        '''
        get race record associated with id
        
        :param id: id of race
        '''
        data = self._get(COURSE_SEARCH.format(raceid=raceid,courseid=courseid)
                           )
        return data
        
    #----------------------------------------------------------------------
    def _get(self,method,**params):
    #----------------------------------------------------------------------
        """
        get method for athlinks access
        
        :param method: athlinks method to call
        :param **params: parameters for the method
        """
        
        params['format'] = 'json'
        params['key'] = self.key
        
        body = urllib.urlencode(params)
        url = '{}/{}?{}'.format(ATHLINKS_URL,method,body)
        if self.debug:
            print url
        resp,jsoncontent = self.http.request(url)
        
        if resp.status != 200:
            raise accessError, 'URL response status = {0}'.format(resp.status)
        
        # unmarshall the response content
        content = json.loads(jsoncontent)
        
        return content 
        
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    unit test for athlinks.py
    '''
    
    parser = argparse.ArgumentParser(description=descr,formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('runningclub',version.__version__))
    args = parser.parse_args()

    # this would be a good place for unit tests
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()