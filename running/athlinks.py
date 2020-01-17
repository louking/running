#!/usr/bin/python
###########################################################################################
#   athlinks - access methods for athlinks.com
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/12/13    Lou King    Create
#
#   Copyright 2013 Lou King
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
import urllib.request, urllib.parse, urllib.error
import json
import time
import logging
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s')

# pypi
import httplib2

# github

# other

# home grown
from loutilities import apikey
from running import accessError, parameterError

# access stuff
ATHLINKS_URL = 'https://api.athlinks.com'
RESULTS_SEARCH = 'Results/search'
RACE_SEARCH = 'races/{id}'
COURSE_SEARCH = 'races/{raceid}/{courseid}'
MEMBER_RESULTS_SEARCH = 'athletes/results/{id}'
MEMBER_DETAILS = 'athletes/details/{handle}'
ATH_CAT_RUNNING = 2

HTTPTIMEOUT = 60
SERVERDELAY = 20
MPERMILE = 1609.344


#----------------------------------------------------------------------
def gettime(athlinkstime):
#----------------------------------------------------------------------
    '''
    return epoch time based on athlinks time
    
    :param athlinkstime: time from athlinks record
    :rtype: int containing epoch time
    '''
    # parse racedate.  racedate is '\Date(<epochtime*1000>)\'  
    while athlinkstime[0] not in '0123456789':
        athlinkstime = athlinkstime[1:]
    while athlinkstime[-1] not in '0123456789':
        athlinkstime = athlinkstime[:-1]
    return int(athlinkstime)/1000  # strange format, but that's what it is

#----------------------------------------------------------------------
def dist2miles(distunit,disttypeid):
#----------------------------------------------------------------------
    '''
    get distance in miles, based on athlinks distunit, disttypeid
    
    :param distunit: number of units of distance, unit based on disttypeid
    :param disttypeid: meters=6, others unknown
    '''
    if disttypeid != 6:
        raise parameterError('unknown disttypeid {}'.format(disttypeid))
    return distunit / MPERMILE

#----------------------------------------------------------------------
def dist2km(distunit,disttypeid):
#----------------------------------------------------------------------
    '''
    get distance in kilometers, based on athlinks distunit, disttypeid
    
    :param distunit: number of units of distance, unit based on disttypeid
    :param disttypeid: meters=6, others unknown
    '''
    if disttypeid != 6:
        raise parameterError('unknown disttypeid {}'.format(disttypeid))
    return distunit / 1000

########################################################################
class Athlinks():
########################################################################
    '''
    access methods for athlinks.com
    '''

    #----------------------------------------------------------------------
    def __init__(self, key=None, debug=False):
    #----------------------------------------------------------------------
        """
        initialize http and get athlinks key
        """
        # get credentials from configuration
        self.key = key
        if not self.key:
            ak = apikey.ApiKey('Lou King','running')
            try:
                self.key = ak.getkey('athlinks')
            except apikey.unknownKey:
                raise parameterError("'athlinks' key needs to be configured using apikey")
        
        # need http object
        self.http = httplib2.Http(timeout=HTTPTIMEOUT)

        # set up logging level
        self.log = logging.getLogger('running.athlinks')
        self.setdebug(debug)
        
        # count how many pages have been retrieved
        self.urlcount = 0
        
    #----------------------------------------------------------------------
    def setdebug(self,debugval):
    #----------------------------------------------------------------------
        '''
        set debugging attribute for this class
        
        :param debugval: set to True to enable debugging
        '''
        if not debugval:
            level = logging.INFO
        else:
            level = logging.DEBUG
        self.log.setLevel(level)
        
    #----------------------------------------------------------------------
    def geturlcount(self):
    #----------------------------------------------------------------------
        '''
        each time a url is retrieved, this counter is bumped
        
        :rtype: integer, number of url's retrieved
        '''
        return self.urlcount

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
                               pagesize=500,
                               page=page,
                               name=name,
                               includeclaimed=True
                               )
            if len(data['List']) == 0: break
            
            races += data['List']
            page += 1

        def _checkfilter(checkdict):
            for key in filt:
                if key not in checkdict or checkdict[key] != filt[key]:
                    return False
            return True

        races = list(filter(_checkfilter,races))
        return races
        
    #----------------------------------------------------------------------
    def getmember(self,handle):
    #----------------------------------------------------------------------
        '''
        get member record associated with handle
        
        :param handle: handle for member, ID or email should work
        '''
        handle = urllib.parse.quote(str(handle))
        data = self._get(MEMBER_DETAILS.format(handle=handle)
                           )
        return data
        
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
        
        body = urllib.parse.urlencode(params)
        url = '{}/{}?{}'.format(ATHLINKS_URL,method,body)
        
        # loop RETRIES times for timeout or other error
        retries = 20
        while retries > 0:
            retries -= 1
            try:
                self.log.debug(url)
                resp,jsoncontent = self.http.request(url)

                if resp.status != 200:
                    raise accessError('URL response status = {0}'.format(resp.status))
                
                # unmarshall the response content
                content = json.loads(jsoncontent)

                self.urlcount += 1
                break

            except Exception as e:
                if retries == 0:
                    self.log.info('{} requests attempted'.format(self.geturlcount()))
                    self.log.error('http request failure, retries exceeded: {0}'.format(e))
                    if repr(e) == 'ValueError: No JSON object could be decoded':
                        self.log.error('   jsoncontent={}'.format(jsoncontent))
                    raise
                self.log.warning('http request failure: {0}'.format(e))
                time.sleep(SERVERDELAY)  # give the server some time to recover

        return content 
        
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    unit test for athlinks.py
    '''
    
    parser = argparse.ArgumentParser(description=descr,formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('running',version.__version__))
    args = parser.parse_args()

    # this would be a good place for unit tests
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()