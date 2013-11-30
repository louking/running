#!/usr/bin/python
###########################################################################################
#   runningahead - access methods for runningahead.com
#
#   Date        Author      Reason
#   ----        ------      ------
#   01/08/13    Lou King    Create
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
runningahead - access methods for runningahead.com
===================================================
'''

# standard
import pdb
import argparse
import os.path
import urllib
import json

# pypi
import httplib2

# github

# other

# home grown
from running import *
from loutilities import apikey

# OAuth stuff
auth_url = 'https://www.runningahead.com/oauth2/authorize'
token_url = 'https://api.runningahead.com/oauth2/token'

FIELD = {}
FIELD['workout'] = {
    'eventtype':10,
    'eventsubtype':11,
    'date':12,
    'distance':20,
    'duration':21,  # seconds
    'coursename':22,
    }
HTTPTIMEOUT = 5
KMPERMILE = 1.609344

#----------------------------------------------------------------------
def dist2miles(distance):
#----------------------------------------------------------------------
    '''
    convert distance to miles for distance returned from runningahead
    
    :param dist: distance field from runningahead
    :rtype: float - number of miles represented by the distance field
    '''
    mpermile = KMPERMILE * 1000
    
    unit = distance['unit']
    
    if unit == 'mi':
        distmiles =  distance['value']
    
    elif unit == 'km':
        distmiles = distance['value'] / KMPERMILE
        
    elif unit == 'm':
        distmiles = distance['value'] / mpermile
        
    else:
        raise parameterError, '{0}: invalid unit returned for runningahead distance'.format(unit)
    
    return distmiles

#----------------------------------------------------------------------
def dist2meters(distance):
#----------------------------------------------------------------------
    '''
    convert distance to meters for distance returned from runningahead
    
    :param dist: distance field from runningahead
    :rtype: float - number of meters represented by the distance field
    '''
    mpermile = KMPERMILE * 1000
    
    unit = distance['unit']
    
    if unit == 'mi':
        distmeters =  distance['value'] * mpermile
    
    elif unit == 'km':
        distmeters = distance['value'] * 1000.0
        
    elif unit == 'm':
        distmeters = distance['value']
        
    else:
        raise parameterError, '{0}: invalid unit returned for runningahead distance'.format(unit)
    
    return distmeters

########################################################################
class RunningAhead():
########################################################################
    '''
    access methods for RunningAhead.com
    '''

    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        """
        initialize oauth authentication
        """

        # get credentials from configuration
        ak = apikey.ApiKey('Lou King','running')
        try:
            key = ak.getkey('ra')
            secret = ak.getkey('rasecret')
        except apikey.unknownKey:
            raise parameterError, "'ra'  and 'rasecret' keys needs to be configured using apikey"
        
        # Step 3 from http://api.runningahead.com/docs/authentication (using client_credentials, not authorization_code)
        self.http = httplib2.Http(timeout=HTTPTIMEOUT)
        resp,jsoncontent = self._httpreq('https://api.runningahead.com/oauth2/token',
                                         method='POST',
                                         client_id=key,
                                         client_secret=secret,
                                         grant_type='client_credentials'
                                         )
        content = json.loads(jsoncontent)
        self.client_credentials = content['access_token']
        
    #----------------------------------------------------------------------
    def listusers(self):
    #----------------------------------------------------------------------
        """
        return users accessible to this application
        """
        
        # max number of users in user list is 100, so need to loop, collecting
        # BITESIZE users at a time.  These are all added to users list, and final
        # list is returned to the caller
        BITESIZE = 100
        offset = 0
        users = []
        while True:
            data = self._raget('users',
                               self.client_credentials,
                               limit=BITESIZE,
                               offset=offset,
                               )
            if data['numEntries'] == 0:
                break
            theseusers = data['entries']
            
            users += theseusers
            offset += BITESIZE

            # stop iterating if we've reached the end of the data
            if offset >= data['numEntries']:
                break
        
        return users
        
    #----------------------------------------------------------------------
    def listactivitytypes(self,accesstoken):
    #----------------------------------------------------------------------
        """
        return activity types for this user

        :param accesstoken: access_token to use for api call
        """
        
        data = self._raget('logs/me/activity_types',accesstoken)
        activity_types = data['entries']
        return activity_types
        
    #----------------------------------------------------------------------
    def listworkouts(self,accesstoken,begindate=None,enddate=None,getfields=None):
    #----------------------------------------------------------------------
        """
        return run workouts within date range
        
        :param accesstoken: access_token to use for api call
        :param begindate: date in format yyyy-mm-dd
        :param enddate: date in format yyyy-mm-dd
        :param getfields: list of fields to get in response.  See runningahead.FIELD['workout'].keys() for valid codes
        """
        
        if getfields:
            lpfield = []
            for f in getfields:
                lpfield.append(str(FIELD['workout'][f]))
            fields = ','.join(lpfield)
        
        # fill in optional arguments as needed
        optargs = {}
        optargs['activityID'] = 10  # Run
        if begindate: optargs['beginDate'] = begindate
        if enddate:   optargs['endDate']   = enddate
        if getfields: optargs['fields']    = fields
        
        # max number of workouts in workout list is 100, so need to loop, collecting
        # BITESIZE workouts at a time.  These are all added to workouts list, and final
        # list is returned to the caller
        BITESIZE = 100
        offset = 0
        workouts = []
        while True:
            data = self._raget('logs/me/workouts',
                               accesstoken,
                               limit=BITESIZE,
                               offset=offset,
                               **optargs
                               )
            if data['numEntries'] == 0:
                break
            
            theseworkouts = data['entries']
            workouts += theseworkouts
            offset += BITESIZE

            # stop iterating if we've reached the end of the data
            if offset >= data['numEntries']:
                break
        
        # here would be a fine place to operate on an optional filter parameter.
        # only problem with that is every time I do that I make the filter parameter
        # so complex that I can never figure it out myself
        
        return workouts  
        
    #----------------------------------------------------------------------
    def getworkout(self,accesstoken,id):
    #----------------------------------------------------------------------
        """
        return workout for specified id
        
        :param accesstoken: access_token to use for api call
        :param id: id retrieved from listworkouts for desireed workout
        """
        
        data = self._raget('logs/me/workouts/{0}'.format(id),accesstoken)
        workout = data['workout']
        return workout
        
    #----------------------------------------------------------------------
    def getuser(self,accesstoken):
    #----------------------------------------------------------------------
        """
        return workout for specified id
        
        :param accesstoken: access_token to use for api call
        """
        
        data = self._raget('users/me',accesstoken)
        user = data['user']
        return user
        
    #----------------------------------------------------------------------
    def _raget(self,method,accesstoken,**params):
    #----------------------------------------------------------------------
        """
        get method for runningahead access
        
        :param method: runningahead method to call
        :param accesstoken: access_token to use for api call
        :param **params: parameters for the method
        """
        
        self._authorize(params,accesstoken)
        
        body = urllib.urlencode(params)
        url = 'https://api.runningahead.com/rest/{0}?{1}'.format(method,body)
        resp,jsoncontent = self.http.request(url)
        
        if resp.status != 200:
            raise accessError, 'URL response status = {0}'.format(resp.status)
        
        # unmarshall the response content
        content = json.loads(jsoncontent)
        
        if content['code'] != 0:
            raise accessError, 'RA response code = {0}'.format(content['code'])
    
        data = content['data']
        return data 
        
    #----------------------------------------------------------------------
    def _httpreq(self,url,**params):
    #----------------------------------------------------------------------
        """
        http request
        
        :param method: 'GET' or 'POST'
        :param **params: parameters for the method
        """
        
        method = params.pop('method','GET')
        
        if method == 'GET':
            urlparams = urllib.urlencode(params)
            url = '{0}?{1}'.format(url,urlparams)
            body = None
        elif method == 'POST':
            url = '{0}'.format(url)
            body = urllib.urlencode(params)
        else:
            raise invalidParameter, '{0} not supported'.format(method)
        
        resp,content = self.http.request(url,method,body)
        
        if resp.status != 200:
            raise accessError, 'URL response status = {0}'.format(resp.status)
        
        return resp,content
        
    #----------------------------------------------------------------------
    def _authorize(self,params,accesstoken):
    #----------------------------------------------------------------------
        """
        add authorization to params
        
        :param params: list of parameters for API method
        :param accesstoken: access_token to use
        """

        params['access_token'] = accesstoken

#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    unit test for runningahead.py
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