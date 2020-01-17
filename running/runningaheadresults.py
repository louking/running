#!/usr/bin/python
###########################################################################################
#   runningaheadresults - manage race results data from runningahead
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/27/13    Lou King    Create
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
runningaheadresults - manage race results data from runningahead
===================================================================

Usage::
    runningaheadresults.py [-h] [-v] [-b BEGINDATE] [-e ENDDATE]
                                     searchfile outfile
    
        collect race results from runningahead
    
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
import logging
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s')
log = logging.getLogger('running.runningahead')
log.setLevel(logging.DEBUG)

# pypi
#from IPython.core.debugger import Tracer; debughere = Tracer(); debughere() # set breakpoint where needed

# github

# other

# home grown
from loutilities import timeu
from loutilities import csvu
from runningclub import agegrade
from runningclub import render
from .runningahead import FIELD
from running.running import version, runningahead

ag = agegrade.AgeGrade()
class invalidParameter(Exception): pass

fdate = timeu.asctime('%Y-%m-%d')
METERSPERMILE = 1609.344

#----------------------------------------------------------------------
def collect(searchfile,outfile,begindate,enddate):
#----------------------------------------------------------------------
    '''
    collect race results from runningahead
    
    :param searchfile: path to file containing names, genders, birth dates to search for
    :param outfile: output file path
    :param begindate: epoch time - choose races between begindate and enddate
    :param enddate: epoch time - choose races between begindate and enddate
    '''
    
    outfilehdr = 'GivenName,FamilyName,name,DOB,Gender,race,date,age,miles,km,time'.split(',')
    
    # open files
    _IN = open(searchfile,'rb')
    IN = csv.DictReader(_IN)
    _OUT = open(outfile,'wb')
    OUT = csv.DictWriter(_OUT,outfilehdr)
    OUT.writeheader()

    # common fields between input and output
    commonfields = 'GivenName,FamilyName,DOB,Gender'.split(',')

    # create runningahead access, grab users who have used the steeplechasers.org portal to RA
    ra = runningahead.RunningAhead()
    users = ra.listusers()
    rausers = []
    for user in users:
        rauser = ra.getuser(user['token'])
        rausers.append((user,rauser))

    # reset begindate to beginning of day, enddate to end of day
    dt_begindate = timeu.epoch2dt(begindate)
    a_begindate = fdate.dt2asc(dt_begindate)
    adj_begindate = datetime.datetime(dt_begindate.year,dt_begindate.month,dt_begindate.day,0,0,0)
    e_begindate = timeu.dt2epoch(adj_begindate)
    dt_enddate = timeu.epoch2dt(enddate)
    a_enddate = fdate.dt2asc(dt_enddate)
    adj_enddate = datetime.datetime(dt_enddate.year,dt_enddate.month,dt_enddate.day,23,59,59)
    e_enddate = timeu.dt2epoch(adj_enddate)
    
    # get today's date for high level age filter
    start = time.time()
    today = timeu.epoch2dt(start)
    
    # loop through runners in the input file
    for runner in IN:
        fname,lname = runner['GivenName'],runner['FamilyName']
        membername = '{} {}'.format(fname,lname)
        log.debug('looking for {}'.format(membername))
        e_dob = fdate.asc2epoch(runner['DOB'])
        dt_dob = fdate.asc2dt(runner['DOB'])
        dob = runner['DOB']
        gender = runner['Gender'][0]

        # find thisuser
        foundmember = False
        for user,rauser in rausers:
            if 'givenName' not in rauser or 'birthDate' not in rauser: continue    # we need to know the name and birth date
            givenName = rauser['givenName'] if 'givenName' in rauser else ''
            familyName = rauser['familyName'] if 'familyName' in rauser else ''
            rausername = '{} {}'.format(givenName,familyName)
            if rausername == membername and dt_dob == fdate.asc2dt(rauser['birthDate']):
                foundmember = True
                log.debug('found {}'.format(membername))
                break
            # member is not this ra user, keep looking

        # if we couldn't find this member in RA, try the next member
        if not foundmember: continue
        
        ## skip getting results if participant too young
        #todayage = timeu.age(today,dt_dob)
        #if todayage < 14: continue
        
        # if we're here, found the right user, now let's look at the workouts
        workouts = ra.listworkouts(user['token'],begindate=a_begindate,enddate=a_enddate,getfields=list(FIELD['workout'].keys()))

        # save race workouts, if any found
        results = []
        if workouts:
            for wo in workouts:
                if wo['workoutName'].lower() != 'race': continue
                if 'duration' not in wo['details']: continue        # seen once, not sure why
                thisdate = wo['date']
                dt_thisdate = fdate.asc2dt(thisdate)
                thisdist = runningahead.dist2meters(wo['details']['distance'])
                thistime = wo['details']['duration']
                thisrace = wo['course']['name'] if 'course' in wo else 'unknown'
                if thistime == 0:
                    log.warning('{} has 0 time for {} {}'.format(membername,thisrace,thisdate))
                    continue
                stat = {'GivenName':fname,'FamilyName':lname,'name':membername,
                        'DOB':dob,'Gender':gender,'race':thisrace,'date':thisdate,'age':timeu.age(dt_thisdate,dt_dob),
                        'miles':thisdist/METERSPERMILE,'km':thisdist/1000.0,'time':render.rendertime(thistime,0)}
                results.append(stat)
        
        # loop through each result
        for result in results:
            e_racedate = fdate.asc2epoch(result['date'])
            
            # skip result if outside the desired time window
            if e_racedate < begindate or e_racedate > enddate: continue
            
            # create output record and copy fields
            outrec = result
            resulttime = result['time']

            # strange case of TicksString = ':00'
            if resulttime[0] == ':':
                resulttime = '0'+resulttime
            while resulttime.count(':') < 2:
                resulttime = '0:'+resulttime
            outrec['time'] = resulttime

            OUT.writerow(outrec)
        
    _OUT.close()
    _IN.close()
    
    finish = time.time()
    print('elapsed time (min) = {}'.format((finish-start)/60))
    
########################################################################
class RunningAheadFileResult():
########################################################################
    '''
    holds result from runningahead file
    
    :param firstname: first name
    :param lastname: last name
    :param name: firstname lastname
    :param dob: date of birth, datetime
    :param gender: M or F
    :param race: name of race
    :param date: date of race, datetime
    :param age: age on race day
    :param miles: race distance, miles
    :param km: race distance, kilometers
    :param time: race time, seconds
    '''
    attrs = 'firstname,lastname,name,dob,gender,race,date,age,miles,km,time'.split(',')
    
    #----------------------------------------------------------------------
    def __init__(self,firstname=None,lastname=None,name=None,dob=None,gender=None,race=None,date=None,age=None,miles=None,km=None,time=None):
    #----------------------------------------------------------------------
        self.firstname = firstname
        self.lastname = lastname
        self.name = name
        self.dob = dob
        self.gender = gender
        self.race = race
        self.date = date
        self.age = age
        self.miles = miles
        self.km = km
        self.time = time
        
    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        reprval = '{}('.format(self.__class__)
        for attr in self.attrs:
            val = getattr(self,attr)
            if attr in ['dob','date']:
                val = fdate.dt2asc(val)
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
class RunningAheadResultFile():
########################################################################
    '''
    represents file of runningahead results collected from runningahead
    
    TODO:: add write methods, and update :func:`collect` to use :class:`RunningAheadFileResult` class
    '''
    filehdr = 'GivenName,FamilyName,name,DOB,Gender,race,date,age,miles,km,time'.split(',')
    # RunningAheadResultFile.filehdr needs to associate 1:1 with RunningAheadFileResult.attrs
    hdrtransform = dict(list(zip(filehdr,RunningAheadFileResult.attrs)))

    resultdates = 'dob,date'.split(',')

    #----------------------------------------------------------------------
    def __init__(self,filename):
    #----------------------------------------------------------------------
        self.filename = filename
        
    #----------------------------------------------------------------------
    def open(self,mode='rb'):
    #----------------------------------------------------------------------
        '''
        open runningahead result file
        
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
        close runningahead result file
        '''
        if hasattr(self,'_fh'):
            self._fh.close()
            delattr(self,'_fh')
            delattr(self,'_csv')
        
    #----------------------------------------------------------------------
    def __next__(self):
    #----------------------------------------------------------------------
        '''
        get next :class:`RunningAheadFileResult`
        
        :rtype: :class:`RunningAheadFileResult`, or None when end of file reached
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
                aresultargs[aattr] = fdate.asc2dt(fresult[fattr])
                
            else:
                # convert numbers
                aresultargs[aattr] = csvu.str2num(fresult[fattr])
                
        return RunningAheadFileResult(**aresultargs)
    
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    collect race results from runningahead
    
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