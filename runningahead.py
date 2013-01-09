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

# general purpose exceptions
class parameterError(Exception): pass
class accessError(Exception): pass

# OAuth stuff
APIKEY = '8561dc05fb554510a2a6bcf443463712'
APISECRET = '69468bfc99c8401db01556b1e46e2523'
auth_url = 'https://www.runningahead.com/oauth2/authorize'
token_url = 'https://api.runningahead.com/oauth2/token'
FLOW = oaclient.OAuth2WebServerFlow(APIKEY,APISECRET,'authorization_code',redirect_uri='urn:ietf:wg:oauth:2.0:oob',
                                 auth_uri=auth_url,token_uri=token_url)

# TODO: use CONFIGDIR from __init__.py
#RADAT = os.path.join(CONFIGDIR,'runningahead.dat')
RADAT = 'runningahead.dat'

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
    def __init__(self):
    #----------------------------------------------------------------------
        """
        initialize oauth authentication
        """

        storage = oafile.Storage(RADAT)
        self.credentials = storage.get()
        if self.credentials is None or self.credentials.invalid == True:
            self.credentials = oatools.run(FLOW, storage)
        http = httplib2.Http(timeout=HTTPTIMEOUT)
        self.http = self.credentials.authorize(http)
        
    #----------------------------------------------------------------------
    def getruns(self,begindate='2013-01-01',enddate='2013-12-31',fields=FIELD['workout'].keys()):
        # TODO: remove defaults
    #----------------------------------------------------------------------
        """
        return run workouts within date range
        
        :param userid: RA userid for which data should be retrieved
        :param begindate: date in format yyyy-mm-dd
        :param enddate: date in format yyyy-mm-dd
        """
        
        lpfield = []
        for f in fields:
            lpfield.append(str(FIELD['workout'][f]))
        fields = ','.join(lpfield)
        
        BITESIZE = 100
        #params = {
        #    'activityID':10,  # run
        #    'beginDate':begindate,
        #    'endDate':enddate,
        #    'limit':BITESIZE,
        #    'offset':0, # initial offset, updated while iterating below
        #    'fields':fields,
        #}
        #self._authorize(params)
        offset = 0
        
        runs = []
        while True:
            #body = urllib.urlencode(params)
            #url = 'https://api.runningahead.com/rest/logs/me/workouts?' + body
            #resp,jsoncontent = self.http.request(url)
            #
            #if resp.status != 200:
            #    raise accessError, 'URL response status = '.format(resp.status)
            #
            ## unmarshall the response content
            #content = json.loads(jsoncontent)
            #
            #if content['code'] != 0:
            #    raise accessError, 'RA response code = '.format(content['code'])
            #
            #theseruns = content['data']['entries']
            data = self._raget('workouts',
                               activityID=10,  # run
                               beginDate=begindate,
                               endDate=enddate,
                               limit=BITESIZE,
                               offset=offset,
                               fields=fields,
                               )
            theseruns = data['entries']
            runs += theseruns
            offset += BITESIZE
            #params['offset'] += BITESIZE
            
            # stop iterating if we've reached the end of the data
            #if params['offset'] >= content['data']['numEntries']:
            if offset >= data['numEntries']:
                break
            
        return runs  
        
    #----------------------------------------------------------------------
    def getactivitytypes(self):
    #----------------------------------------------------------------------
        """
        return run activity types for this user
        """
        
        #params = {
        #}
        #self._authorize(params)
        #
        #body = urllib.urlencode(params)
        #url = 'https://api.runningahead.com/rest/logs/me/activity_types?' + body
        #resp,jsoncontent = self.http.request(url)
        #
        #if resp.status != 200:
        #    raise accessError, 'URL response status = '.format(resp.status)
        #
        ## unmarshall the response content
        #content = json.loads(jsoncontent)
        #
        #if content['code'] != 0:
        #    raise accessError, 'RA response code = '.format(content['code'])
        #
        #activity_types = content['data']['entries']
        #return activity_types
        
        data = self._raget('activity_types')
        activity_types = data['entries']
        return activity_types
        
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
        url = 'https://api.runningahead.com/rest/logs/me/{0}?'.format(method) + body
        resp,jsoncontent = self.http.request(url)
        
        if resp.status != 200:
            raise accessError, 'URL response status = '.format(resp.status)
        
        # unmarshall the response content
        content = json.loads(jsoncontent)
        
        if content['code'] != 0:
            raise accessError, 'RA response code = '.format(content['code'])
    
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
