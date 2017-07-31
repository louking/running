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
import logging
import json
from tempfile import NamedTemporaryFile

# pypi
import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

# github

# other

# home grown
# from running import *
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
KMPERMILE = 1.609344

class accessError(Exception): pass

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

    :param membercachefilename: name of optional file to cache detailed member data
    :param debug: set to True for debug logging of http requests, default False
    :param key: ra key for oauth, if omitted retrieved from apikey
    :param secret: ra secret for oauth, if omitted retrieved from apikey
    '''

    #----------------------------------------------------------------------
    def __init__(self, membercachefilename=None, debug=False, key=None, secret=None):
    #----------------------------------------------------------------------
        """
        initialize oauth authentication, and load member cache
        """

        # does user want to debug?
        if debug:
            # set up debug logging
            logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        else:
            pass # how to stop?

        # get credentials from configuration if not provided
        if not (key and secret):
            ak = apikey.ApiKey('Lou King','running')
            try:
                key = ak.getkey('ra')
                secret = ak.getkey('rasecret')
            except apikey.unknownKey:
                raise parameterError, "'ra' and 'rasecret' keys needs to be configured using apikey"
        
        # Step 3 from http://api.runningahead.com/docs/authentication (using client_credentials, not authorization_code)
        # see http://requests-oauthlib.readthedocs.org/en/latest/oauth2_workflow.html#legacy-application-flow
        client = BackendApplicationClient(client_id=key)
        oauth = OAuth2Session(client=client)
        data = oauth.fetch_token(token_url='https://api.runningahead.com/oauth2/token', client_id=key, client_secret=secret)
        self.client_credentials = data['access_token']

        # set up session for multiple requests
        self.rasession = requests.Session()

        # bring in cache file, if requested
        self.membercache = {}
        self.membercachefilename = membercachefilename
        if self.membercachefilename:
            # only read cache if file exists
            if os.path.isfile(membercachefilename):
                with open(membercachefilename,'r') as membercachefile:
                    # members are stored one per line, in json format
                    for line in membercachefile:
                        member = json.loads(line)
                        self.membercache[member['id']] = member
        # optimization - no write on close if not updated
        self.membercacheupdated = False

    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        close the connection when we're done, and save the cache
        '''
        # done here
        self.rasession.close()

        # save the cache in a temporary file, if requested and it's been updated
        if self.membercachefilename and self.membercacheupdated:
            # get full path for self.membercachefilename to assure cachedir isn't relative
            cachedir = os.path.dirname(os.path.abspath(self.membercachefilename))

            # save temporary file with cache
            with NamedTemporaryFile(mode='w', suffix='.racache', delete=False, dir=cachedir) as tempcache:
                tempmembercachefilename = tempcache.name
                for id in self.membercache:
                    tempcache.write('{}\n'.format(json.dumps(self.membercache[id])))

            # set mode of temp file to be same as current cache file (see https://stackoverflow.com/questions/5337070/how-can-i-get-a-files-permission-mask)
            cachemode = os.stat(self.membercachefilename).st_mode & 0777
            os.chmod(tempmembercachefilename, cachemode)

            # now overwrite the previous version of the membercachefile with the new membercachefile
            try:
                # atomic operation in Linux
                os.rename(tempmembercachefilename, self.membercachefilename)

            # should only happen under windows
            except OSError:
                os.remove(self.membercachefilename)
                os.rename(tempmembercachefilename, self.membercachefilename)


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
        filters = []
        if begindate: filters.append(['date','ge',begindate])
        if enddate:   filters.append(['date','le',enddate])
        if getfields: optargs['fields']    = fields
        if filters:
            # need to json encode the parameter, so requests doesn't unwravel it, as RA expects the json array of arrays
            optargs['filters'] = json.dumps(filters)
        
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
        rauser = data['user']
        
        # flatten user structure, as expected by caller
        user = {}
        for raf in rauser:
            if type(rauser[raf]) == dict:
                for f in rauser[raf]:
                    user[f] = rauser[raf][f]
            else:
                user[raf] = rauser[raf]
                
        return user
        
    #----------------------------------------------------------------------
    def listmemberships(self,club,accesstoken,**filters):
    #----------------------------------------------------------------------
        """
        return list of club memberships
        
        :param club: RA slug name of club
        :param accesstoken: access token for a priviledged viewer for this club
        :param filters: see http://api.runningahead.com/docs/club/list_members for valid filters
        :rtype: list of memberships
        """
        
        # retrieve all the members
        method = 'clubs/{}/members'.format(club)
        data = self._raget(method,accesstoken,**filters)
        memberships = data['entries']
        
        return memberships
        
    #----------------------------------------------------------------------
    def getmember(self,club,id,accesstoken,update=False):
    #----------------------------------------------------------------------
        """
        return list of club members
        
        :param club: RA slug name of club
        :param id: id of member
        :param accesstoken: access token for a priviledged viewer
        :param update: update based on latest information from RA
        :rtype: member record
        """
        
        # do we need to retrieve from RunningAHEAD?
        if update or id not in self.membercache:
            method = 'clubs/{}/members/{}'.format(club,id)
            data = self._raget(method,accesstoken)
            member = data['member']
            self.membercache[id] = member
            self.membercacheupdated = True

        # use member data from cache
        else:
            member = self.membercache[id]
        
        return member
        
    #----------------------------------------------------------------------
    def listmembershiptypes(self,club,accesstoken):
    #----------------------------------------------------------------------
        """
        return list of club membership types
        
        :param club: RA slug name of club
        :param accesstoken: access token for a priviledged viewer for this club
        :rtype: list of memberships
        """
        
        # retrieve all the members
        method = 'clubs/{}/memberships'.format(club)
        data = self._raget(method,accesstoken)
        membershiptypes = data['entries']
        
        return membershiptypes
        
    #----------------------------------------------------------------------
    def _raget(self,method,accesstoken,**payload):
    #----------------------------------------------------------------------
        """
        get method for runningahead access
        
        :param method: runningahead method to call
        :param accesstoken: access_token to use for api call
        :param **payload: parameters for the method
        """
        
        payload['access_token'] = accesstoken
        
        url = 'https://api.runningahead.com/rest/{0}'.format(method)
        r = self.rasession.get(url,params=payload)
        if r.status_code != 200:
            raise accessError, 'HTTP response code={}, url={}'.format(r.status_code,r.url)

        content = r.json()

        if content['code'] != 0:
            raise accessError, 'RA response code={}, url={}'.format(content['code'],r.url)
    
        data = content['data']
        return data 
        
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
