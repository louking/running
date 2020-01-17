#!/usr/bin/python
###########################################################################################
#   ultrasignupresults - manage race results data from ultrasignup
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
ultrasignupresults - manage race results data from ultrasignup
===================================================================

Usage::
    ultrasignupresults.py [-h] [-v] [-b BEGINDATE] [-e ENDDATE]
                                     searchfile outfile
    
        collect race results from ultrasignup
    
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
import argparse
import csv
import datetime
import time

# pypi
#from IPython.core.debugger import Tracer; debug_here = Tracer()

# github

# other

# home grown
from loutilities import timeu
from loutilities import csvu
from runningclub import agegrade
from running.running import version, ultrasignup

# see http://api.ultrasignup.com/Enums/RaceCategories
ag = agegrade.AgeGrade()
class invalidParameter(Exception): pass

ftime = timeu.asctime('%Y-%m-%d')

#----------------------------------------------------------------------
def collect(searchfile,outfile,begindate,enddate):
#----------------------------------------------------------------------
    '''
    collect race results from ultrasignup
    
    :param searchfile: path to file containing names, genders, birth dates to search for
    :param outfile: output file path
    :param begindate: epoch time - choose races between begindate and enddate
    :param enddate: epoch time - choose races between begindate and enddate
    '''
    
    # open files
    _IN = open(searchfile,'rb')
    IN = csv.DictReader(_IN)
    _OUT = open(outfile,'wb')
    OUT = csv.DictWriter(_OUT,UltraSignupResultFile.filehdr)
    OUT.writeheader()

    # common fields between input and output
    commonfields = 'GivenName,FamilyName,DOB,Gender'.split(',')

    # create ultrasignup access
    ultra = ultrasignup.UltraSignup(debug=True)

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
        fname,lname = runner['GivenName'],runner['FamilyName']
        e_dob = ftime.asc2epoch(runner['DOB'])
        dt_dob = ftime.asc2dt(runner['DOB'])
        gender = runner['Gender'][0]
        
        ## skip getting results if participant too young
        #todayage = timeu.age(today,dt_dob)
        #if todayage < 14: continue
        
        # get results for this athlete
        results = ultra.listresults(fname,lname)
        
        # loop through each result
        for result in results:
            e_racedate = ftime.asc2epoch(result.racedate)
            
            # skip result if outside the desired time window
            if e_racedate < begindate or e_racedate > enddate: continue
            
            # skip result if runner's age doesn't match the age within the result
            dt_racedate = timeu.epoch2dt(e_racedate)
            racedateage = timeu.age(dt_racedate,dt_dob)
            if result.age != racedateage: continue
            
            # skip result if runner's gender doesn't match gender within the result
            resultgen = result.gender
            if resultgen != runner['Gender'][0]: continue
            
            # create output record and copy common fields
            outrec = {}
            for field in commonfields:
                outrec[field] = runner[field]
                
            # fill in output record fields from runner, result
            # combine name, get age
            outrec['name'] = '{} {}'.format(runner['GivenName'],runner['FamilyName'])
            outrec['age'] = result.age

            # race name, location; convert from unicode if necessary
            racename = result.racename
            outrec['race'] = racename
            outrec['date'] = ftime.epoch2asc(e_racedate)
            outrec['loc'] = '{}, {}'.format(result.racecity, result.racestate)
            
            # distance, category, time
            distmiles = result.distmiles
            distkm = result.distkm
            if distkm is None or distkm < 0.050: continue # should already be filtered within ultrasignup, but just in case

            outrec['miles'] = distmiles
            outrec['km'] = distkm
            resulttime = result.racetime

            # int resulttime means DNF, most likely -- skip this result
            if isinstance(resulttime, int): continue
            
            # strange case of TicksString = ':00'
            if resulttime[0] == ':':
                resulttime = '0'+resulttime
            while resulttime.count(':') < 2:
                resulttime = '0:'+resulttime
            outrec['time'] = resulttime

            # just leave out age grade if exception occurs
            try:
                agpercent,agresult,agfactor = ag.agegrade(racedateage,gender,distmiles,timeu.timesecs(resulttime))
                outrec['ag'] = agpercent
                if agpercent < 15 or agpercent >= 100: continue # skip obvious outliers
            except:
                pass

            OUT.writerow(outrec)
        
    _OUT.close()
    _IN.close()
    
    finish = time.time()
    print('number of URLs retrieved = {}'.format(ultra.geturlcount()))
    print('elapsed time (min) = {}'.format((finish-start)/60))
    
########################################################################
class UltraSignupFileResult():
########################################################################
    '''
    holds result from ultrasignup file
    
    :param firstname: first name
    :param lastname: last name
    :param name: firstname lastname
    :param dob: date of birth, datetime
    :param gender: M or F
    :param race: name of race
    :param date: date of race, datetime
    :param loc: location of race
    :param age: age on race day
    :param miles: race distance, miles
    :param km: race distance, kilometers
    :param time: race time, seconds
    :param ag: age grade percentage
    '''
    attrs = 'firstname,lastname,name,dob,gender,race,date,loc,age,miles,km,time,ag'.split(',')
    
    #----------------------------------------------------------------------
    def __init__(self,firstname=None,lastname=None,name=None,dob=None,gender=None,race=None,date=None,loc=None,age=None,miles=None,km=None,time=None,ag=None):
    #----------------------------------------------------------------------
        self.firstname = firstname
        self.lastname = lastname
        self.name = name
        self.dob = dob
        self.gender = gender
        self.race = race
        self.date = date
        self.loc = loc
        self.age = age
        self.miles = miles
        self.km = km
        self.time = time
        self.ag = ag
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        reprval = '{}('.format(self.__class__)
        for attr in self.attrs:
            val = getattr(self,attr)
            if attr in ['dob','date']:
                val = ftime.dt2asc(val)
            reprval += '{}={},'.format(attr,val)
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
            
            setattr(self,attr,val)

########################################################################
class UltraSignupResultFile():
########################################################################
    '''
    represents file of ultrasignup results collected from ultrasignup
    
    TODO:: add write methods, and update :func:`collect` to use :class:`UltraSignupFileResult` class
    '''
    filehdr = 'GivenName,FamilyName,name,DOB,Gender,race,date,loc,age,miles,km,time,ag'.split(',')
    # UltraSignupResultFile.filehdr needs to associate 1:1 with UltraSignupFileResult.attrs
    hdrtransform = dict(list(zip(filehdr,UltraSignupFileResult.attrs)))

    resultdates = 'dob,date'.split(',')

    #----------------------------------------------------------------------
    def __init__(self,filename):
    #----------------------------------------------------------------------
        self.filename = filename
        
    #----------------------------------------------------------------------
    def open(self,mode='rb'):
    #----------------------------------------------------------------------
        '''
        open ultrasignup result file
        
        :param mode: 'rb' or 'wb' -- TODO: support 'wb'
        '''
        if mode[0] not in 'r':
            raise invalidParameter('mode {} not currently supported'.format(mode))
    
        self._fh = open(self.filename,mode)
        if mode[0] == 'r':
            self._csv = csv.DictReader(self._fh)
        else:
            pass
        
    #----------------------------------------------------------------------
    def close(self):
    #----------------------------------------------------------------------
        '''
        close ultrasignup result file
        '''
        if hasattr(self,'_fh'):
            self._fh.close()
            delattr(self,'_fh')
            delattr(self,'_csv')
        
    #----------------------------------------------------------------------
    def __next__(self):
    #----------------------------------------------------------------------
        '''
        get next :class:`UltraSignupFileResult`
        
        :rtype: :class:`UltraSignupFileResult`, or None when end of file reached
        '''
        try:
            fresult = next(self._csv)
            
        except StopIteration:
            return None
        
        aresultargs = {}
        for fattr in self.hdrtransform:
            aattr = self.hdrtransform[fattr]
            
            # special handling for gender
            if aattr == 'gender':
                aresultargs[aattr] = fresult[fattr][0]
                
            # special handling for dates
            elif aattr in self.resultdates:
                aresultargs[aattr] = ftime.asc2dt(fresult[fattr])
                
            else:
                # convert numbers
                aresultargs[aattr] = csvu.str2num(fresult[fattr])
                
        return UltraSignupFileResult(**aresultargs)
    
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    collect race results from ultrasignup
    
    searchfile must have at least the following headings:
    
        * GivenName - first name
        * FamilyName - last name
        * Gender - Male or Female (or M or F)
        * DOB - date of birth in yyyy-mm-dd format
        * City - city of residence [optional]
        * State - state of residence [optional]
    '''
    
    parser = argparse.ArgumentParser(description=descr, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('running', version.__version__))
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