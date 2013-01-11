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
from oauth2client import client as oaclient
from oauth2client import file as oafile
from oauth2client import tools as oatools
import httplib2

# github

# other

# home grown
from . import *

# OAuth stuff
auth_url = 'https://www.runningahead.com/oauth2/authorize'
token_url = 'https://api.runningahead.com/oauth2/token'

# authorized credentials are stored here
RADAT = os.path.join(CONFIGDIR,'runningahead.dat')

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

########################################################################
class RunningAhead():
########################################################################
    '''
    access methods for RunningAhead.com
    '''

    #----------------------------------------------------------------------
    def __init__(self, apikey, apisecret):
    #----------------------------------------------------------------------
        """
        initialize oauth authentication
        
        :param apikey: key for runningahead api
        :param apisecret: secret for runningahead api
        """

        storage = oafile.Storage(RADAT)
        self.credentials = storage.get()
        if self.credentials is None or self.credentials.invalid == True:
#            flow = oaclient.OAuth2WebServerFlow(apikey,apisecret,'authorization_code',
            flow = oaclient.OAuth2WebServerFlow(apikey,apisecret,'client_credentials',
                                                redirect_uri='urn:ietf:wg:oauth:2.0:oob',
                                                auth_uri=auth_url,token_uri=token_url)
            self.credentials = oatools.run(flow, storage)
        http = httplib2.Http(timeout=HTTPTIMEOUT)
        self.http = self.credentials.authorize(http)
        
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
                               limit=BITESIZE,
                               offset=offset,
                               )
            theseusers = data['entries']
            users += theseusers
            offset += BITESIZE

            # stop iterating if we've reached the end of the data
            if offset >= data['numEntries']:
                break
        
        return users
        
    #----------------------------------------------------------------------
    def listactivitytypes(self):
    #----------------------------------------------------------------------
        """
        return activity types for this user
        """
        
        data = self._raget('logs/me/activity_types')
        activity_types = data['entries']
        return activity_types
        
    #----------------------------------------------------------------------
    def listworkouts(self,begindate=None,enddate=None,getfields=None):
    #----------------------------------------------------------------------
        """
        return run workouts within date range
        
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
                               limit=BITESIZE,
                               offset=offset,
                               **optargs
                               )
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
    def getworkout(self,id):
    #----------------------------------------------------------------------
        """
        return workout for specified id
        
        :param id: id retrieved from listworkouts for desireed workout
        """
        
        data = self._raget('logs/me/workouts/{0}'.format(id))
        workout = data['workout']
        return workout
        
    #----------------------------------------------------------------------
    def _raget(self,method,**params):
    #----------------------------------------------------------------------
        """
        get method for runningahead access
        
        :param method: runningahead method to call
        :param **params: parameters for the method
        """
        
        self._authorize(params)
        
        body = urllib.urlencode(params)
        url = 'https://api.runningahead.com/rest/{0}?'.format(method) + body
        resp,jsoncontent = self.http.request(url)
        
        if resp.status != 200:
            raise accessError, 'URL response status = '.format(resp.status)
        
        # unmarshall the response content
        content = json.loads(jsoncontent)
        
        if content['code'] != 0:
            raise accessError, 'RA response code = {0}'.format(content['code'])
    
        data = content['data']
        return data 
        
    #----------------------------------------------------------------------
    def _authorize(self,params):
    #----------------------------------------------------------------------
        """
        add authorization to params
        
        :param params: list of parameters for API method
        """

        auth = {}
        self.credentials.apply(auth)
        accesstoken = auth['Authorization'].split()[1]
        params['access_token'] = accesstoken
