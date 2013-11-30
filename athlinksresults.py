#!/usr/bin/python
###########################################################################################
#   athlinksresults - manage race results data from athlinks
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/13/13    Lou King    Create
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
athlinksresults - manage race results data from athlinks
===================================================================

Usage::
    athlinksresults.py [-h] [-v] [-b BEGINDATE] [-e ENDDATE]
                                     searchfile outfile
    
        collect race results from athlinks
    
        searchfile must have at least the following headings:
    
            * GivenName - first name
            * FamilyName - last name
            * Gender - Male or Female (or M or F)
            * DOB - date of birth in yyyy-mm-dd format
            * City - city of residence [optional]
            * State - state of residence [optional]
    
    
    positional arguments:
      searchfile            file with names, genders and birth dates of athletes
                            to search for
      outfile               output file contains race results
    
    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      -b BEGINDATE, --begindate BEGINDATE
                            choose races between begindate and enddate, yyyy-mm-dd
      -e ENDDATE, --enddate ENDDATE
                            choose races between begindate and enddate, yyyy-mm-dd
                        
'''

# standard
import pdb
import argparse
import os.path
import tempfile
import csv
import datetime
import time

# pypi

# github

# other

# home grown
from loutilities import timeu
from loutilities import csvu
from runningclub import agegrade
import athlinks
import version

# see http://api.athlinks.com/Enums/RaceCategories
CAT_RUNNING = 2
CAT_TRAILS = 15
race_category = {CAT_RUNNING:'Running',CAT_TRAILS:'Trail Running'}
ag = agegrade.AgeGrade()
class invalidParameter(Exception): pass

# resultfilehdr needs to associate 1:1 with resultattrs
resultfilehdr = 'GivenName,FamilyName,name,DOB,Gender,athlmember,athlid,race,date,loc,age,miles,km,category,time,ag'.split(',')
resultattrs = 'firstname,lastname,name,dob,gender,member,id,racename,racedate,raceloc,age,distmiles,distkm,racecategory,resulttime,resultagegrade'.split(',')
resultdates = 'dob,racedate'.split(',')
hdrtransform = dict(zip(resultfilehdr,resultattrs))
ftime = timeu.asctime('%Y-%m-%d')

#----------------------------------------------------------------------
def collect(searchfile,outfile,begindate,enddate):
#----------------------------------------------------------------------
    '''
    collect race results from athlinks
    
    :param searchfile: path to file containing names, genders, birth dates to search for
    :param outfile: output file path
    :param begindate: epoch time - choose races between begindate and enddate
    :param enddate: epoch time - choose races between begindate and enddate
    '''
    
    # open files
    _IN = open(searchfile,'rb')
    IN = csv.DictReader(_IN)
    _OUT = open(outfile,'wb')
    OUT = csv.DictWriter(_OUT,resultfilehdr)
    OUT.writeheader()

    # common fields between input and output
    commonfields = 'GivenName,FamilyName,DOB,Gender'.split(',')

    # create athlinks
    athl = athlinks.Athlinks(debug=True)

    # reset begindate to beginning of day, enddate to end of day
    dt_begindate = timeu.epoch2dt(begindate)
    adj_begindate = datetime.datetime(dt_begindate.year,dt_begindate.month,dt_begindate.day,0,0,0)
    begindate = timeu.dt2epoch(adj_begindate)
    dt_enddate = timeu.epoch2dt(enddate)
    adj_enddate = datetime.datetime(dt_enddate.year,dt_enddate.month,dt_enddate.day,23,59,59)
    enddate = timeu.dt2epoch(adj_enddate)
    
    # get today's date for high level age filter
    start = time.time()
    today = timeu.epoch2dt(start)
    
    # loop through runners in the input file
    for runner in IN:
        name = ' '.join([runner['GivenName'],runner['FamilyName']])
        e_dob = ftime.asc2epoch(runner['DOB'])
        dt_dob = ftime.asc2dt(runner['DOB'])
        
        # skip getting results if participant too young
        todayage = timeu.age(today,dt_dob)
        if todayage < 14: continue
        
        # get results for this athlete
        results = athl.listathleteresults(name)
        
        # loop through each result
        for result in results:
            e_racedate = athlinks.gettime(result['Race']['RaceDate'])
            
            # skip result if outside the desired time window
            if e_racedate < begindate or e_racedate > enddate: continue
            
            # skip result if runner's age doesn't match the age within the result
            dt_racedate = timeu.epoch2dt(e_racedate)
            racedateage = timeu.age(dt_racedate,dt_dob)
            if result['Age'] != racedateage: continue
            
            # skip result if runner's gender doesn't match gender within the result
            resultgen = result['Gender'][0]
            if resultgen != runner['Gender'][0]: continue
            
            # get course used for this result
            course = athl.getcourse(result['Race']['RaceID'],result['CourseID'])
            
            # skip result if not Running or Trail Running race
            thiscategory = course['Courses'][0]['RaceCatID']
            if thiscategory not in race_category: continue
            
            # create output record and copy common fields
            outrec = {}
            for field in commonfields:
                outrec[field] = runner[field]
                
            # fill in output record fields from runner, result, course
            # combine name, get age
            outrec['name'] = '{} {}'.format(runner['GivenName'],runner['FamilyName'])
            outrec['age'] = result['Age']

            # leave athlmember and athlid blank if result not from an athlink member
            athlmember = result['IsMember']
            if athlmember:
                outrec['athlmember'] = 'Y'
                outrec['athlid'] = result['RacerID']

            # race name, location; convert from unicode if necessary
            # TODO: make function to do unicode translation -- apply to runner name as well (or should csv just store unicode?)
            racename = csvu.unicode2ascii(course['RaceName'])
            coursename = csvu.unicode2ascii(course['Courses'][0]['CourseName'])
            outrec['race'] = '{} / {}'.format(racename,coursename)
            outrec['date'] = ftime.epoch2asc(athlinks.gettime(course['RaceDate']))
            outrec['loc'] = csvu.unicode2ascii(course['Home'])
            
            # distance, category, time
            distmiles = athlinks.dist2miles(course['Courses'][0]['DistUnit'],course['Courses'][0]['DistTypeID'])
            distkm = athlinks.dist2km(course['Courses'][0]['DistUnit'],course['Courses'][0]['DistTypeID'])
            if distkm < 0.050: continue # skip timed events, which seem to be recorded with 0 distance

            outrec['miles'] = distmiles
            outrec['km'] = distkm
            outrec['category'] = race_category[thiscategory]
            resulttime = result['TicksString']

            # strange case of TicksString = ':00'
            if resulttime[0] == ':':
                resulttime = '0'+resulttime
            while resulttime.count(':') < 2:
                resulttime = '0:'+resulttime
            outrec['time'] = resulttime

            # just leave out age grade if exception occurs
            try:
                agpercent,agresult,agfactor = ag.agegrade(racedateage,resultgen,distmiles,timeu.timesecs(resulttime))
                outrec['ag'] = agpercent
                if agpercent < 15 or agpercent >= 100: continue # skip obvious outliers
            except:
                pass

            OUT.writerow(outrec)
        
    _OUT.close()
    _IN.close()
    
    finish = time.time()
    print 'number of URLs retrieved = {}'.format(athl.geturlcount())
    print 'elapsed time (min) = {}'.format((finish-start)/60)
    
########################################################################
class AthlinksResult():
########################################################################
    '''
    represents single result from athlinks
    '''


    #----------------------------------------------------------------------
    def __init__(self,**myattrs):
    #----------------------------------------------------------------------

        for attr in resultattrs:
            setattr(self,attr,None)
            
        for attr in myattrs:
            if attr not in resultattrs:
                raise invalidParameter,'unknown attribute: {}'.format(attr)
            setattr(self,attr,myattrs[attr])
    
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        
        reprstr = 'athlinksresult.AthlinksResult('
        for attr in resultattrs:
            reprstr += '{}={},'.format(attr,getattr(self,attr))
        reprstr = reprstr[:-1] + ')'
        return reprstr
    
########################################################################
class AthlinksResultFile():
########################################################################
    '''
    represents file of athlinks results collected from athlinks
    
    TODO:: add write methods, and update :func:`collect` to use :class:`AthlinksResult` class
    '''
   
    #----------------------------------------------------------------------
    def __init__(self,filename):
    #----------------------------------------------------------------------
        self.filename = filename
        
    #----------------------------------------------------------------------
    def open(self,mode='rb'):
    #----------------------------------------------------------------------
        '''
        open athlinks result file
        
        :param mode: 'rb' or 'wb' -- TODO: support 'wb'
        '''
        if mode[0] not in 'r':
            raise invalidParameter, 'mode {} not currently supported'.format(mode)
    
        self._fh = open(self.filename,mode)
        if mode[0] == 'r':
            self._csv = csv.DictReader(self._fh)
        else:
            pass
        
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        close athlinks result file
        '''
        if hasattr(self,'_fh'):
            self._fh.close()
            delattr(self,'_fh')
            delattr(self,'_csv')
        
    #----------------------------------------------------------------------
    def next(self):
    #----------------------------------------------------------------------
        '''
        get next :class:`AthlinksResult`
        
        :rtype: :class:`AthlinksResult`, or None when end of file reached
        '''
        try:
            fresult = self._csv.next()
            
        except StopIteration:
            return None
        
        aresultargs = {}
        for fattr in hdrtransform:
            aattr = hdrtransform[fattr]
            
            # special handling for gender
            if aattr == 'gender':
                aresultargs[aattr] = fresult[fattr][0]
                
            # special handling for dates
            elif aattr in resultdates:
                aresultargs[aattr] = ftime.asc2dt(fresult[fattr])
                
            else:
                # convert numbers
                try:
                    aresultargs[aattr] = int(fresult[fattr])
                except ValueError:
                    try:
                        aresultargs[aattr] = float(fresult[fattr])
                    except ValueError:
                        aresultargs[aattr] = fresult[fattr]
                
        return AthlinksResult(**aresultargs)
    
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    collect race results from athlinks
    
    searchfile must have at least the following headings:
    
        * GivenName - first name
        * FamilyName - last name
        * Gender - Male or Female (or M or F)
        * DOB - date of birth in yyyy-mm-dd format
        * City - city of residence [optional]
        * State - state of residence [optional]
    '''
    
    parser = argparse.ArgumentParser(description=descr,formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('running',version.__version__))
    parser.add_argument('searchfile', help="file with names, genders and birth dates of athletes to search for")
    parser.add_argument('outfile', help="output file contains race results")
    parser.add_argument('-b','--begindate', help="choose races between begindate and enddate, yyyy-mm-dd",default=None)
    parser.add_argument('-e','--enddate', help="choose races between begindate and enddate, yyyy-mm-dd",default=None)
    args = parser.parse_args()

    searchfile = args.searchfile
    outfile = args.outfile

    argtime = timeu.asctime('%Y-%m-%d')
    if args.begindate:
        begindate = argtime.asc2epoch(args.begindate)
    else:
        begindate = argtime.asc2epoch('1970-01-01')
    if args.enddate:
        enddate = argtime.asc2epoch(args.enddate)
    else:
        enddate = argtime.asc2epoch('2030-12-31')
        
    # collect all the data
    collect(searchfile,outfile,begindate,enddate)
        
########################################################################
#	__main__
########################################################################
if __name__ == "__main__":
    main()