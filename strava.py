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
from tempfile import NamedTemporaryFile
import sys
import os.path
from collections import OrderedDict, defaultdict

# pypi
import requests

# github

# other

# home grown
import version
from loutilities import apikey
from loutilities import timeu
from loutilities.csvwt import record2csv

stravatime = timeu.asctime('%Y-%m-%dT%H:%M:%SZ')

KMPERMILE = 1.609344

DATEFIELD = 'start_date'

# from https://strava.github.io/api/v3/activities/
xworkout_type = {
    None : 'default',
    0    : 'default',
    1    : 'race',
    2    : 'long run',
    3    : 'workout',
    10   : 'default',
    11   : 'race',
    12   : 'workout',
}
workout_type = defaultdict(lambda: 'unknown',**xworkout_type)

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

    :param cachefilename: name of cache file
    '''

    #----------------------------------------------------------------------
    def __init__(self, clubactivitycachefilename=None, debug=False):
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

        # set up debug logging, if desired
        if debug:
            logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True

        # bring in clubactivitycache file, if requested
        self.clubactivitycache = {}
        self.clubactivitycachefilename = clubactivitycachefilename
        if self.clubactivitycachefilename:
            # only read clubactivitycache if file exists
            if os.path.isfile(clubactivitycachefilename):
                with open(clubactivitycachefilename,'r') as clubactivitycachefile:
                    # members are stored one per line, in json format
                    for line in clubactivitycachefile:
                        activity = json.loads(line)
                        id = activity['id']
                        # make sure there are no duplicates initially
                        if id not in self.clubactivitycache:
                            self.clubactivitycache[id] = activity
        
        # keep track of size of cache and number of activities added
        self.clubactivitycachesize = len(self.clubactivitycache)
        self.clubactivitycacheadded = 0
        
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        close the connection when we're done, and save the cache
        '''
        # save the cache in a temporary file, if requested and it's been updated
        if self.clubactivitycachefilename and self.clubactivitycacheadded > 0:
            # get full path for self.clubactivitycachefilename to assure cachedir isn't relative
            cachedir = os.path.dirname(os.path.abspath(self.clubactivitycachefilename))
            with NamedTemporaryFile(mode='w', suffix='.stravacache', delete=False, dir=cachedir) as tempcache:
                tempclubactivitycachefilename = tempcache.name
                for id in self.clubactivitycache:
                    tempcache.write('{}\n'.format(json.dumps(self.clubactivitycache[id])))

            # now overwrite the previous version of the clubactivitycachefile with the new clubactivitycachefile
            try:
                # atomic operation in Linux
                os.rename(tempclubactivitycachefilename, self.clubactivitycachefilename)

            # should only happen under windows
            except OSError:
                os.remove(self.clubactivitycachefilename)
                os.rename(tempclubactivitycachefilename, self.clubactivitycachefilename)

    #----------------------------------------------------------------------
    def getathleteclubs(self):
    #----------------------------------------------------------------------
        """
        retrieve current athlete's clubs
        """

        # requires python 2.7.9+ for secure ssl
        url = 'https://www.strava.com/api/v3/athlete/clubs'

        # initialize payload
        payload = {'access_token':self.user}
        # payload['per_page'] = perpage
        # payload['page'] = 1

        r = requests.get(url, params=payload)
        r.raise_for_status()

        return r.json()

    #----------------------------------------------------------------------
    def getclubdetails(self,clubid):
    #----------------------------------------------------------------------
        """
        retrieve club information

        :param clubid: strava id for club
        """

        # requires python 2.7.9+ for secure ssl
        url = 'https://www.strava.com/api/v3/clubs/{}'.format(clubid)

        # initialize payload
        payload = {'access_token':self.user}
        # payload['per_page'] = perpage
        # payload['page'] = 1

        r = requests.get(url, params=payload)
        r.raise_for_status()

        return r.json()

    #----------------------------------------------------------------------
    def getclubactivities(self,clubid,before=None,after=None,perpage=200,maxactivities=None,**filters):
    #----------------------------------------------------------------------
        """
        retrieve activities for a club

        :param clubid: strava id for club
        :param before: epoch time activities should be before
        :param after: epoch time activities should be after
        :param perpage: (debug) how many activities per request, max 200 per strava api docs
        :param maxactivities: (debug) max number of activities to return, None means all
        :param filters: additional filters to compare against returned activities {'field1':value, 'field2':[list,of,values]}
        """

        # requires python 2.7.9+ for secure ssl
        url = 'https://www.strava.com/api/v3/clubs/{}/activities'.format(clubid)

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
            r.raise_for_status()

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

        # update activity cache
        for activity in activities:
            id = activity['id']
            if id not in self.clubactivitycache:
                self.clubactivitycache[id] = activity
                self.clubactivitycacheadded += 1
        self.clubactivitycachesize = len(self.clubactivitycache)

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
        r.raise_for_status()

        return r.json()

    #----------------------------------------------------------------------
    def clubactivitycache2csv(self,mapping=None,outfile=None):
    #----------------------------------------------------------------------
        '''
        dump the club activity cache to a csv file

       :param mapping: OrderedDict {'outfield1':'infield1', 'outfield2':outfunction(cacherecord), ...} or ['inoutfield1', 'inoutfield2', ...]
       :param outfile: optional output file
       :rtype: lines from output file
           '''
        # set up default mapping
        if not mapping:
            mapping = OrderedDict([
                ('workout_id',      'id'),
                ('start_date',      'start_date_local'),
                ('name',            lambda rec: '{} {}'.format(rec['athlete']['firstname'], rec['athlete']['lastname'])),
                ('type',            'type'),
                ('workout_type',    lambda rec: workout_type[rec['workout_type']]),
                ('distance(m)',     'distance'),
                ('time(s)',         'elapsed_time'),
            ])

        activities = self.clubactivitycache.values()
        csvrecords = record2csv(activities,mapping,outfile=outfile)
        return csvrecords

#----------------------------------------------------------------------
def updatestravaclubactivitycache(): 
#----------------------------------------------------------------------
    '''
    script to update the strava club activity cache

    usage: updatestravaclubactivitycache [-h] [-v] cachefile clubname

        script to update the strava club activity cache


    positional arguments:
      cachefile      pathname of file in which cache is saved
      clubname       full name of club as known to strava

    optional arguments:
      -h, --help     show this help message and exit
      -v, --version  show program's version number and exit
    '''

    descr = '''
    script to update the strava club activity cache
    '''
    
    parser = argparse.ArgumentParser(description=descr,formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('running',version.__version__))
    parser.add_argument('cachefile', help="pathname of file in which cache is saved")
    parser.add_argument('clubname', help="full name of club as known to strava")
    args = parser.parse_args()

    # let user know what is going on
    print 'Updating Strava club activity cache for "{}"'.format(args.clubname)

    # instantiate the Strava object, which opens the cache
    ss = Strava(args.cachefile)

    # get the club id
    clubs = ss.getathleteclubs()
    clubid = None
    for club in clubs:
        if club['name'] == args.clubname:
            clubid = club['id']
            break
    
    # error if we didn't find the club
    if not clubid:
        sys.exit('ERROR: club "{}" not found'.format(args.clubname))

    # retrieve all the latest activities
    activities = ss.getclubactivities(clubid)
    numadded = ss.clubactivitycacheadded
    cachesize = ss.clubactivitycachesize

    # close the object, which saves the cache
    ss.close()

    # let user know how we did
    print '   update complete:'
    print '      {} activities received from Strava'.format(len(activities))
    print '      added {} of these to cache'.format(numadded)
    print '      new cache size = {}'.format(cachesize)

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