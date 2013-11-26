#!/usr/bin/python
###########################################################################################
#   ultrasignup - access methods for ultrasignup.com
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/23/13    Lou King    Create
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
ultrasignup - access methods for ultrasignup.com
===================================================
'''

# standard
import argparse
import os.path
import urllib
from lxml import etree
import unicodedata
import logging
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s')

# pypi
import httplib2
from IPython.core.debugger import Tracer; debug_here = Tracer()

# github

# other

# home grown
from loutilities import timeu
from loutilities import csvu
from running import accessError, parameterError

# access stuff
ULTRASIGNUP_URL = 'http://www.ultrasignup.com'
RESULTS_SEARCH = 'results_participant.aspx'
NUMULTRASIGNUPCOLS = 7

HTTPTIMEOUT = 10
MPERMILE = 1609.344

tindate  = timeu.asctime('%b %d, %Y')
toutdate = timeu.asctime('%Y-%m-%d')

#----------------------------------------------------------------------
def racenameanddist(el):
#----------------------------------------------------------------------
    '''
    get race name and distance from etree element
    
    :param el: element from last column of untrasignup.com
    :rtype: racename, distmiles, distkm
    '''

    # one child, a link
    linkel = el.getchildren()[0]
    
    # but all we need is the text, formatted as
    # <racename> - <dist><units>
    racetext = linkel.text.strip()
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
    units = distfield[startunits:]
    
    # kilometers
    if units == 'KM':
        distkm = dist 
        distmiles = (dist * 1000) / MPERMILE
    
    # miles
    elif units == 'M':
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

########################################################################
class UltraSignupResult():
########################################################################
    '''
    holds result from ultrasignup.com
    
    :param ranking: ultra ranking achieved during race
    :param oaplace: overall place
    :param genplace: gender place
    :param age: age on race day
    :param racetime: finishing time h:mm:ss
    :param racedate: date of race yyyy-mm-dd
    :param raceloc: location of race
    :param racename: name of race
    :param distmiles: distance in miles
    :param distkm: distance in kilometers
    '''
    # these are the attributes of UltraSignupResult which are in the same order
    # as the table coming from ultrasignup.com.
    # The remaining attributes, racename, distmiles, distkm are handled individually
    # based on the last column of the table from ultrasignup.com
    attrs = 'ranking,oaplace,genplace,age,racetime,racedate,raceloc,racename,distmiles,distkm'.split(',')
    
    #----------------------------------------------------------------------
    def __init__(self,ranking=None,oaplace=None,genplace=None,age=None,racetime=None,racedate=None,raceloc=None,racename=None,distmiles=None,distkm=None):
    #----------------------------------------------------------------------
        self.ranking = ranking
        self.oaplace = oaplace
        self.genplace = genplace
        self.age = age
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
        data = self._get(RESULTS_SEARCH,
                           fname=fname,
                           lname=lname
                           )
        
        doc = etree.HTML(data)
        for el in doc.iter():
            if el.tag == 'table':
                table = el
                break
            
        results = []
        
        # iterate through the rows of the table
        rows = iter(table)
        
        # for each row in the table, grab the row and associate with the attributes
        rownum = 0
        while True:
            try:
                row = next(rows)
                rownum += 1
                # skip first two rows (colgroup,heading)
                if rownum <= 2: continue
            except StopIteration:
                break

            cols = [c.text for c in row]
            # skip runner identification
            if len(cols) < NUMULTRASIGNUPCOLS: continue
            
            result = UltraSignupResult()
            result.set(zip(UltraSignupResult.attrs,cols))
            result.racename,result.distmiles,result.distkm = racenameanddist(row[-1])
            
            # skip races which are not mileage based
            if result.distmiles == None: continue   
            
            results.append(result)
            
        def _checkfilter(check):
            for key in filt:
                if not hasattr(check,key) or getattr(check,key) != filt[key]:
                    return False
            return True

        results = filter(_checkfilter,results)
        return results
        
    #----------------------------------------------------------------------
    def _get(self,method,**params):
    #----------------------------------------------------------------------
        """
        get method for ultrasignup access
        
        :param method: ultrasignup method to call
        :param **params: parameters for the method
        """
        
        body = urllib.urlencode(params)
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
            except Exception, e:
                if retries == 0:
                    self.log.info('{} requests attempted'.format(self.geturlcount()))
                    self.log.error('http request failure, retries exceeded: {0}'.format(e))
                    raise
                self.log.warning('http request failure: {0}'.format(e))
        
        if resp.status != 200:
            raise accessError, 'URL response status = {0}'.format(resp.status)
        
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