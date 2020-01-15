#!/usr/bin/python
###########################################################################################
#   ultrasignup - access methods for ultrasignup.com
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/23/13    Lou King    Create
#
#   Copyright 2013,2014 Lou King
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
ultrasignup - access methods for ultrasignup.com
===================================================
'''

# standard
import argparse
import os.path
import urllib.request, urllib.parse, urllib.error
import unicodedata
import logging
import json
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s')

# pypi
import httplib2
# from IPython.core.debugger import Tracer; debug_here = Tracer()

# github

# other

# home grown
from loutilities import timeu
from loutilities import csvu
from loutilities import renderrun as render
from running import accessError, parameterError

# access stuff
ULTRASIGNUP_URL = 'http://ultrasignup.com'
RESULTS_SEARCH = 'service/events.svc/history/{fname}/{lname}'

HTTPTIMEOUT = 10
MPERMILE = 1609.344

tindate  = timeu.asctime('%m/%d/%Y %I:%M:%S %p')
toutdate = timeu.asctime('%Y-%m-%d')

#----------------------------------------------------------------------
def racenameanddist(eventname):
#----------------------------------------------------------------------
    '''
    get race name and distance 
    
    :param eventname: eventname from untrasignup.com
    :rtype: racename, distmiles, distkm
    '''

    # eventname is formatted as <racename> - <dist><units>
    racetext = eventname.strip()
    fields = racetext.split('-')
    
    # include distance in racename, as sometimes it's missing
    racename = racetext
    distfield = fields[-1].strip()
    
    # accumulate distance, and figure out where units field starts
    dist = 0
    startunits = 0
    for digit in distfield:
        if not digit.isdigit():
            break
        dist *= 10
        dist += int(digit)
        startunits += 1
    
    # pull out the units from the distance field, and interpret
    units = distfield[startunits:].strip()
    
    # special cases
    if distfield == 'Marathon':
        distmiles = 26.21875    # true marathon
        distkm = distmiles * (MPERMILE/1000)
        
    elif distfield == '1/2 Marathon':
        distmiles = 13.109375   # true half marathon
        distkm = distmiles * (MPERMILE/1000)
        
    # kilometers
    elif units == 'K':
        distkm = dist 
        distmiles = (dist * 1000) / MPERMILE
    
    # miles
    elif units == 'Miler':
        # some special cases
        if dist == 13:
            distmiles = 13.109375   # true half marathon
        elif dist == 26:
            distmiles = 26.21875    # true marathon
        else:
            distmiles = dist
        distkm = distmiles * (MPERMILE/1000)
    
    else:
        distmiles = None
        distkm = None

    return racename,distmiles,distkm

#----------------------------------------------------------------------
def racenameanddur(eventname):
#----------------------------------------------------------------------
    '''
    get race name and duration 
    
    :param eventname: eventname from untrasignup.com
    :rtype: racename, duration
    '''

    # eventname is formatted as <racename> - <dist><units>
    racetext = eventname.strip()
    fields = racetext.split('-')
    
    # include distance in racename, as sometimes it's missing
    racename = racetext
    durfield = fields[-1].strip()
    
    # accumulate duration, and figure out where units field starts
    dur = 0
    startunits = 0
    for digit in durfield:
        if not digit.isdigit():
            break
        dur *= 10
        dur += int(digit)
        startunits += 1
    
    # pull out the units from the durance field, and interpret
    units = durfield[startunits:]
    
    # hours
    if units == 'hrs':
        duration = dur
    
    else:
        duration = None

    return racename,duration

########################################################################
class UltraSignupResult():
########################################################################
    '''
    holds result from ultrasignup.com
    
    :param ranking: ultra ranking achieved during race
    :param oaplace: overall place
    :param genplace: gender place
    :param age: age on race day
    :param gender: gender
    :param racetime: finishing time h:mm:ss
    :param racedate: date of race yyyy-mm-dd
    :param raceloc: location of race
    :param racename: name of race
    :param distmiles: distance in miles
    :param distkm: distance in kilometers
    '''
    # us_event_attrs are within the json response from ultrasignup.com
    # attrs must be in the same order
    # loop needs to be driven by us_event_attrs because it's shorter than output attrs
    # racename and distance fields are determined from parsing of 'eventname' from ultrasignup.com
    # gender comes from the outer list returned by ultrasignup
    us_event_attrs = 'runner_rank,place,gender_place,age,time,eventdate,city,state'.split(',')    
    attrs = 'ranking,oaplace,genplace,age,racetime,racedate,racecity,racestate,racename,distmiles,distkm,gender'.split(',')
    
    #----------------------------------------------------------------------
    def __init__(self,ranking=None,oaplace=None,genplace=None,age=None,gender=None,racetime=None,racedate=None,raceloc=None,racename=None,distmiles=None,distkm=None):
    #----------------------------------------------------------------------
        self.ranking = ranking
        self.oaplace = oaplace
        self.genplace = genplace
        self.age = age
        self.gender = gender
        self.racetime = racetime
        self.racedate = racedate
        self.raceloc = raceloc
        self.racename = racename
        self.distmiles = distmiles
        self.distkm = distkm

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        reprval = '{}('.format(self.__class__)
        for attr in self.attrs:
            reprval += '{}={},'.format(attr,getattr(self,attr))
        reprval = reprval[:-1]
        reprval += ')'
        return reprval
    
    #----------------------------------------------------------------------
    def set(self,attrvals):
    #----------------------------------------------------------------------
        '''
        set attributes based on list of attr,val pairs
        
        :param attrvals: [(attr,val),...]
        '''
        
        for attr,inval in attrvals:
            val = csvu.str2num(inval)
            
            # special processing for dates
            if attr in ['racedate']:
                val = toutdate.epoch2asc(tindate.asc2epoch(val))
                
            setattr(self,attr,val)

########################################################################
class UltraSignup():
########################################################################
    '''
    access methods for ultrasignup.com
    '''

    #----------------------------------------------------------------------
    def __init__(self,debug=False):
    #----------------------------------------------------------------------
        """
        initialize http 
        """
        # need http object
        self.http = httplib2.Http(timeout=HTTPTIMEOUT)

        # set up logging level
        self.log = logging.getLogger('running.ultrasignup')
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
    def listresults(self,fname,lname,**filt):
    #----------------------------------------------------------------------
        '''
        return results which match an athlete's name
        
        :param fname: first name of athlete
        :param lname: last name of athlete
        :param **filt: keyword parameters to filter with
        :rtype: list of ultrasignup Race dicts
        '''
        
        # get the data for this athlete
        races = []
        data = self._get(RESULTS_SEARCH.format(
                           fname=urllib.parse.quote(fname),
                           lname=urllib.parse.quote(lname))
                           )
        
        content = json.loads(data)
        
        results = []
        
        # iterate through the rows of the table
        # content contains a list with an entry for each runner of the same name
        for runner in content:
            usresults = runner['Results']
            gender = runner['Gender']
            
            # for each row in the table, grab the row and associate with the attributes
            for usresult in usresults:
                
                # seems like anything other than 1 is not good
                if usresult['status'] != 1: continue
                
                # pull out values from row, in same order as UltraSignupResult.attrs
                vals = []
                for a in UltraSignupResult.us_event_attrs:
                    vals.append(usresult[a])
                
                # zip values into result and parse event name to get name and distances
                result = UltraSignupResult()
                result.set(list(zip(UltraSignupResult.attrs,vals)))
                result.racename,result.distmiles,result.distkm = racenameanddist(usresult['eventname'])
                
                # distmiles == None if this was a timed race.  result.racetime has distance in miles
                if result.distmiles == None:
                    result.racename,duration = racenameanddur(usresult['eventname'])
                    if duration is None: continue   # didn't recognize units
                    
                    result.distmiles = result.racetime
                    result.distkm = result.distmiles * (MPERMILE/1000)
                    # this is in hours so should render correctly
                    result.racetime = render.rendertime(duration*60*60.0,0)
                
                # gender comes from outer runner list
                result.gender = gender
                
                results.append(result)
            
        def _checkfilter(check):
            for key in filt:
                if not hasattr(check,key) or getattr(check,key) != filt[key]:
                    return False
            return True

        results = list(filter(_checkfilter,results))
        return results
        
    #----------------------------------------------------------------------
    def _get(self,method,**params):
    #----------------------------------------------------------------------
        """
        get method for ultrasignup access
        
        :param method: ultrasignup method to call
        :param **params: parameters for the method
        """
        
        body = urllib.parse.urlencode(params)
        url = '{}/{}?{}'.format(ULTRASIGNUP_URL,method,body)
        
        # loop RETRIES times for timeout
        retries = 10
        while retries > 0:
            retries -= 1
            try:
                self.log.debug(url)
                resp,content = self.http.request(url)
                self.urlcount += 1
                break
            except Exception as e:
                if retries == 0:
                    self.log.info('{} requests attempted'.format(self.geturlcount()))
                    self.log.error('http request failure, retries exceeded: {0}'.format(e))
                    raise
                self.log.warning('http request failure: {0}'.format(e))
        
        if resp.status != 200:
            raise accessError('URL response status = {0}'.format(resp.status))
        
        return content 
        
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    unit test for ultrasignup.py
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