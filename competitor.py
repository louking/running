#!/usr/bin/python
###########################################################################################
#   competitor - access methods for competitor.com
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
competitor - access methods for competitor.com
===================================================
'''

# standard
import argparse
import os.path
import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup
import unicodedata
import logging
import pdb
import copy
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s')

# pypi
import httplib2
from IPython.core.debugger import Tracer; debug_here = Tracer()

# github

# other

# home grown
from loutilities import timeu
from loutilities import csvu
from runningclub import render
from running import accessError, parameterError

# access stuff
PAGESIZE = 100
COMPETITOR_URL = 'http://running.competitor.com'
RESULTS_METHOD = 'cgiresults'
RESULTS_SEARCH = 'firstname={firstname}&lastname={lastname}&bib={bib}&gender={gender}&division={division}&city={city}&state={state}'
# RACE_RESULTS = 'eId={raceid}&eiId={yearid}&seId={eventid}'
#PAGING = 'resultsPage={pagenum}&rowCount={pagesize}'.format(pagesize=PAGESIZE)

HTTPTIMEOUT = 10
MPERMILE = 1609.344

tindate  = timeu.asctime('%m/%d/%Y %I:%M:%S %p')
toutdate = timeu.asctime('%Y-%m-%d')

#----------------------------------------------------------------------
def racenameanddist(soup):
#----------------------------------------------------------------------
    '''
    get race name and distance from soup
    
    :param soup: BeautifulSoup object for whole page
    :rtype: racename, distmiles, distkm
    '''

    ensoup = soup.find(class_='event-name')
    if ensoup:
        eventstring = ensoup.text
        rawparts = eventstring.split('-')
        eventparts = [p.strip() for p in rawparts]
        distfield = eventparts[-1].strip()
        # note might have been hyphen in event name
        racename = '-'.join(rawparts[0:-1]).strip()
    else:
        raise EventNotFound
        
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
        
    elif distfield == 'Half Marathon' or distfield == '1/2 Marathon':
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
def racedate(soup):
#----------------------------------------------------------------------
    '''
    get race date from soup
    
    :param soup: BeautifulSoup object for whole page
    :rtype: date of race
    '''

    edsoup = soup.find(class_='event-date')
    if edsoup:
        eventdate = edsoup.text.strip()
    else:
        eventdate = None

    # TODO: for now just return string - should return datetime object
    return eventdate

########################################################################
class competitorParse():
########################################################################
    '''
    gparseobject
    
    :param headingsoup: BeautifulSoup object for column header row
    :param get: _get function from competitor() to retrieve additional information
    :param racequery: dict with parameters to get correct race information
    :rtype: competitorParse instance
    '''

    #----------------------------------------------------------------------
    def __init__(self, headingsoup, get, racequery):
    #----------------------------------------------------------------------
        self.headings = []
        for col in headingsoup.find_all('td',recursive=False):
            self.headings.append(col.text)
        
        self.racequery = copy.copy(racequery)
        self.get = get

    #----------------------------------------------------------------------
    def details(self,detailurl):
    #----------------------------------------------------------------------
        '''
        get detail from url
        
        :param detailurl: url to retrieve result detail from
        :rtype: details dict
        '''
        
        # note detailurl may be relative, and if so needs to be added to base url
        if detailurl[0:7] != 'http://':
            detailurl = COMPETITOR_URL + detailurl

        detail = self.get(detailurl)
        detailsoup = BeautifulSoup(detail)
        
        # get age and gender
        agegen = detailsoup.find(class_='detail-pptage').text
        detailsdict = {}
        for attrval in agegen.split('|'):
            attr,val = [av.strip() for av in attrval.split(':')]
            detailsdict[attr] = val
        
        # get performance stats
        perfsoup = detailsoup.find(class_='detail-performance-stats')
        for li in perfsoup.find_all('li'):
            attr,val = [av.strip() for av in li.text.split(':')]
            # these vals are like '100 out of 15245'
            detailsdict['pf'+attr+'Place'],detailsdict['pf'+attr+'Count'] = [vo.strip() for vo in val.split('out of')]
        
        # make values integer if possible
        for attr in detailsdict:
            try:
                detailsdict[attr] = int(detailsdict[attr])
            except ValueError:
                pass

        return detailsdict
    
    #----------------------------------------------------------------------
    def result(self,rowsoup):
    #----------------------------------------------------------------------
        '''
        get result from rowsoup
        
        :param headingsoup: BeautifulSoup object for column header row
        :param rowsoup: BeautifulSoup object for row
        :rtype: competitorResult instance
        '''
    
        # pull rowcell text out of result row
        # save the soup cells so we can pull in the participant details link
        rowcells = []
        soupcells = []
        for cell in rowsoup.find_all('td'):
            rowcells.append(cell.text.strip())
            soupcells.append(cell)
            
        soupdict = dict(list(zip(self.headings,soupcells)))
        rowdict = dict(list(zip(self.headings,rowcells)))
        
        # try to translate integers
        for attr in rowdict:
            try:
                rowdict[attr] = int(rowdict[attr])
            except ValueError:
                pass
            
        # pull in details
        detailurl = soupdict['Name'].find('a')['href']
        details = self.details(detailurl)
        rowdict.update(details)
        
        # convert to competitorResult object
        irsattrs = competitorResult.result_attrs
        orsattrs = competitorResult.attrs
        attrvals = []
        for i in range(len(irsattrs)):
            inattr = irsattrs[i]
            outattr = orsattrs[i]
            attrvals.append((outattr,rowdict[inattr]))
        
        rowresult = competitorResult()
        rowresult.set(attrvals)
        
        return rowresult
    
########################################################################
class competitorResult():
########################################################################
    '''
    holds result from competitor.com
    
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
    # result_attrs are within the response from competitor.com
    # attrs must be in the same order
    # loop needs to be driven by result_attrs because it's shorter than output attrs
    # racename and distance fields are determined from parsing of 'eventname' from competitor.com
    result_attrs = 'pfOverallPlace,pfGenderPlace,pfDivisionPlace,Name'.split(',') + ['City, State'] + 'Age,Gender,Time'.split(',')    
    attrs = 'oaplace,genplace,divplace,name,hometown,age,gender,racetime,racedate,raceloc,racename,distmiles,distkm'.split(',')
    
    #----------------------------------------------------------------------
    def __init__(self,oaplace=None,genplace=None,divplace=None,name=None,hometown=None,age=None,gender=None,racetime=None,racedate=None,raceloc=None,racename=None,distmiles=None,distkm=None):
    #----------------------------------------------------------------------
        self.oaplace = oaplace
        self.genplace = genplace
        self.divplace = divplace
        self.name = name
        self.hometown = hometown
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
class Competitor():
########################################################################
    '''
    access methods for competitor.com
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
        self.log = logging.getLogger('running.competitor')
        self.setdebug(debug)
        
        # count how many pages have been retrieved
        self.urlcount = 0
        
        # query race
        self.racequery = {'eId':'','eiId':'','seId':''}
        
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
    def setraceyear(self,eventid,eventinstanceid,singleeventid):
    #----------------------------------------------------------------------
        '''
        set the raceid, yearid and eventid for subsequent requests
        
        :param eventid: event id from running.competitor.com
        :param eventinstanceid: event instance id from running.competitor.com
        :param singleeventid: single event id from running.competitor.com
        '''
        self.racequery['eId'] = eventid
        self.racequery['eiId'] = eventinstanceid
        self.racequery['seId'] = singleeventid

    #----------------------------------------------------------------------
    def geturlcount(self):
    #----------------------------------------------------------------------
        '''
        each time a url is retrieved, this counter is bumped
        
        :rtype: integer, number of url's retrieved
        '''
        return self.urlcount

    #----------------------------------------------------------------------
    def getresults(self,limit=None):
    #----------------------------------------------------------------------
        '''
        return results for the current race / event
        
        :param limit: limit number of records (for testing only)
        :rtype: list of competitorResult objects
        '''
        
        # get the first page
        first = True
        pagenum = 1
        
        results = []
        while True:
            params = {'resultsPage':pagenum, 'rowCount':PAGESIZE}
            params.update(self.racequery)
            self.log.info(params)
            pagenum += 1
            
            page = self._get(RESULTS_METHOD,**params)
            
            # parse the page
            soup = BeautifulSoup(page)
            
            # first time through, grab the event, distance and date
            if first:
                event,distmiles,distkm = racenameanddist(soup)
                eventdate = racedate(soup)
                first = False
                
            # pull out the rows of results
            # .select returns a list, so take the first entry
            resulttable = soup.select('.cg-runnergrid-table tbody')[0]
            if not resulttable:
                raise ResultsNotFound
            
            # get all the rows in the table
            resultrows = resulttable.find_all('tr',recursive=False)
    
            # get out when there's no data in this page
            if len(resultrows) <= 1: break
            
            # interpret the row information into the rows list
            headerrow = resultrows[0]
            
            # initialize row parse object with header information, and access to competitor.com (self)
            # TODO: probably the _get, _geturl should be encapsulated in a class on it's own, as multiple classes use it
            rr = competitorParse(headerrow,self._geturl,self.racequery)
            
            # save each result in results
            for resultrow in resultrows[1:]:
                result = rr.result(resultrow)
                result.racename = event
                result.distmiles = distmiles
                result.distkm = distkm
                results.append(result)
                
                # break out if testing limit reached
                if limit:
                    if len(results) >= limit: break
            
            # break out if testing limit reached
            if limit:
                if len(results) >= limit: break
        
        # and back to caller
        return results
        
    #----------------------------------------------------------------------
    def _geturl(self,url):
    #----------------------------------------------------------------------
        '''
        get raw url
        
        :param url: url to retrieve
        :rtype: content (html)
        '''
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
    def _get(self,method='',**params):
    #----------------------------------------------------------------------
        '''
        get method for competitor access
        
        :param method: competitor method to call
        :param **params: parameters for the method
        :rtype: content (html)
        '''
        
        body = urllib.parse.urlencode(params)
        url = '{}/{}?{}'.format(COMPETITOR_URL,method,body)
        content = self._geturl(url)
        
        return content 
        
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    unit test for competitor.py
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