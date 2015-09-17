#!/usr/bin/python
###########################################################################################
#   strava - access methods for strava.com
#
#   Date        Author      Reason
#   ----        ------      ------
#   09/08/15    Lou King    Create
#
#   Copyright 2016 Lou King
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
strava - access methods for strava.com
===================================================
'''

# standard
import pdb
import argparse
import urllib
import json
import time
import logging

# pypi
import requests

# github

# other

# home grown
from running import *
from loutilities import apikey
from loutilities import timeu
stravatime = timeu.asctime('%Y-%m-%dT%H:%M:%SZ')

KMPERMILE = 1.609344

# set up debug logging
logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

DATEFIELD = 'start_date'

#----------------------------------------------------------------------
def dist2miles(distance):
#----------------------------------------------------------------------
    '''
    convert distance to miles for distance returned from strava (meters)
    
    :param distance: distance field from strava
    :rtype: float - number of miles represented by the distance field
    '''
    mpermile = KMPERMILE * 1000
    
    distmiles = distance / mpermile
    
    return distmiles

########################################################################
class Strava():
########################################################################
    '''
    access methods for Strava.com
    '''

    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        """
        initialize 
        """

        # get credentials from configuration
        ak = apikey.ApiKey('Lou King','running')
        try:
            # key = ak.getkey('stravakey')
            # secret = ak.getkey('stravasecret')
            user = ak.getkey('stravauser')
        except apikey.unknownKey:
            raise parameterError, "'stravauser' needs to be configured using apikey"
        
        self.user = user
        
    #----------------------------------------------------------------------
    def getclubactivities(self,club,before=None,after=None,perpage=200,maxactivities=None,**filters):
    #----------------------------------------------------------------------
        """
        retrieve activities for a club

        :param club: strava id for club
        :param before: epoch time activities should be before
        :param after: epoch time activities should be after
        :param perpage: (debug) how many activities per request, max 200 per strava api docs
        :param maxactivities: (debug) max number of activities to return, None means all
        :param filters: additional filters to compare against returned activities {'field1':value, 'field2':[list,of,values]}
        """

        # requires python 2.7.9+ for secure ssl
        url = 'https://www.strava.com/api/v3/clubs/{}/activities'.format(club)

        # initialize payload
        if not before:
            before = int(time.time())
        payload = {'access_token':self.user, 'per_page':perpage}
        payload['page'] = 1
        #payload['before'] = before

        # activities are returned in a list, most recent activity first
        # loop getting activities until oldest one is older than 'after' argument
        activities = []
        more = True
        while more:
            r = requests.get(url, params=payload)
            # r.raise_for_status()

            theseactivities = r.json()
            if len(theseactivities) > 0:
                earliestactivity = theseactivities[-1]
                earliesttime = stravatime.asc2epoch(earliestactivity[DATEFIELD])

                # are we done?
                if after and earliesttime < after:
                    more = False
                    # get rid of activities at the end which are before 'after'
                    while earliesttime < after:
                        theseactivities.pop()
                        if len(theseactivities) == 0: break
                        earliestactivity = theseactivities[-1]
                        earliesttime = stravatime.asc2epoch(earliestactivity[DATEFIELD])
            
            # collect these activities -- are there any left?
            if len(theseactivities) > 0: 
                activities += theseactivities
                #payload['before'] = earliesttime
                payload['page'] += 1


            # we're done if theseactivities is empty
            else:
                more = False

            # we're done if caller wanted limit on number of activities, and we're at or over the limit
            if maxactivities:
                if len(activities) >= maxactivities:
                    more = False
                    activities = activities[:maxactivities]

        # we're outta here
        return activities

    #----------------------------------------------------------------------
    def getathleteactivities(self,athlete,after=None,perpage=200,maxactivities=None,**filters):
    #----------------------------------------------------------------------
        '''
        This doesn't work. Why does strava not allow viewing other athlete data?
        '''

        # requires python 2.7.9+ for secure ssl
        url = 'https://www.strava.com/api/v3/athletes/{}/activities'.format(athlete)

        # initialize payload
        payload = {'access_token':self.user}
        # payload['per_page'] = perpage
        # payload['page'] = 1

        r = requests.get(url, params=payload)
        # r.raise_for_status()

        return r.json()

#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    unit test for strava.py
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