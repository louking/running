#!/usr/bin/python
###########################################################################################
# clubmember - manage club member information 
#
#	Date		Author		Reason
#	----		------		------
#       01/07/13        Lou King        Create
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
clubmember - manage club member information
===================================================
'''

# standard
import pdb
import argparse
import datetime
import difflib
import csv

# pypi

# github

# home grown
import version
from loutilities import timeu, csvwt
from running import racedb

# exceptions for this module.  See __init__.py for package exceptions

# module globals
tYmd = timeu.asctime('%Y-%m-%d')
tHMS = timeu.asctime('%H:%M:%S')
tMS  = timeu.asctime('%M:%S')


# SequenceMatcher to determine matching ratio, which can be used to evaluate CUTOFF value
sm = difflib.SequenceMatcher()

#----------------------------------------------------------------------
def getratio(a,b):
#----------------------------------------------------------------------
    '''
    return the SequenceMatcher ratio for two strings
    
    :rettype: float in range [0,1]
    '''
    sm.set_seqs(a,b)
    return sm.ratio()

########################################################################
class ClubMember():
########################################################################
    '''
    ClubMember object 
    
    first row in filename has at least First,Last,DOB,Gender,City,State
    
    :params csvfile: csv file from which club members are to be retrieved
    :params cutoff: cutoff for getmember.  float in (0,1].  higher means strings have to match more closely to be considered "close".  Default 0.6
    '''
    #----------------------------------------------------------------------
    def __init__(self,csvfile,cutoff=0.6):
    #----------------------------------------------------------------------
        _IN = open(csvfile,'rb')
        IN = csv.DictReader(_IN)
        
        # collect member information by member name
        self.members = {}
        
        # set getmember cutoff.  This is a float within (0,1]
        # higher means strings have to match more closely to be considered "close"
        self.cutoff = cutoff
        
        # read each row in input file, and create the member data structure
        for thisrow in IN:
            name = ' '.join([thisrow['First'],thisrow['Last']])
            thismember = {}
            thismember['name'] = name.strip()
            if thismember['name'] == '': break   # assume first blank 'name' is the end of the data
            try:
                dob = tYmd.dt2asc(timeu.excel2dt(thisrow['DOB']))
            except ValueError:   # handle invalid dates
                dob = ''
            thismember['dob'] = dob
            thismember['gender'] = thisrow['Gender'].upper().strip()
            thismember['hometown'] = ', '.join([thisrow['City'].strip(),thisrow['State'].strip()])
            if name not in self.members:
                self.members[name] = []
            self.members[name].append(thismember)    # allows for possibility that multiple members have same name
    
    #----------------------------------------------------------------------
    def getmembers(self):
    #----------------------------------------------------------------------
        '''
        returns dict keyed by names of members, each containing list of member entries with same name
        
        :rtype: {name:[{'name':name,'dob':dateofbirth,'gender':'M'|'F','hometown':City,ST}]}
        '''
        
        return self.members
    
    #----------------------------------------------------------------------
    def getmember(self,name):
    #----------------------------------------------------------------------
        '''
        returns dict containing list of members entries having same name as most likely match
        for this membername, whether exact match was found, and list of other possible
        membernames which were close
        
        if name wasn't found, {} is returned
        
        :param name: name to search for
        :rtype: {'matchingmembers':member record list, 'exactmatch':boolean, 'closematches':member name list}
        '''
        
        # TODO: could make self.lmembers be dict {'lmember':member,...} and search for lower case matches, to remove case from the uncertainty
        closematches = difflib.get_close_matches(name,self.members.keys(),cutoff=self.cutoff)
        
        rval = {}
        if len(closematches) > 0:
            topmatch = closematches.pop(0)
            rval['exactmatch'] = (name.lower() == topmatch.lower()) # ok to ignore case
            rval['matchingmembers'] = self.members[topmatch][:] # make a copy
            rval['closematches'] = closematches[:]
            
        return rval
        
    #----------------------------------------------------------------------
    def findmember(self,name,age,asofdate):
    #----------------------------------------------------------------------
        '''
        returns (name,dateofbirth) for a specific member, after checking age
        
        if name wasn't found, None is returned (self.getmissedmatches() returns a list of missed matches)
        if no dob in members file, None is returned for dateofbirth
        
        :param name: name to search for
        :param age: age to match for
        :param asofdate: 'yyyy-mm-dd' date for which age is to be matched
        :rtype: (name,dateofbirth) or None if not found.  dateofbirth is ascii yyyy-mm-dd
        '''
        
        # self.missedmatches keeps list of possible matches.  Can be retrieved via self.getmissedmatches()
        self.missedmatches = []
        matches = self.getmember(name)
        
        if not matches: return None
        
        foundmember = False
        membersage = None
        checkmembers = iter([matches['matchingmembers'][0]['name']] + matches['closematches'])
        while not foundmember:
            try:
                checkmember = next(checkmembers)
            except StopIteration:
                break
            matches = self.getmember(checkmember)
            for member in matches['matchingmembers']:
                # assume match for first member of correct age -- TODO: need to do better age checking
                asofdate_dt = tYmd.asc2dt(asofdate)
                try:
                    memberdob = tYmd.asc2dt(member['dob'])
                    # note below that True==1 and False==0
                    memberage = asofdate_dt.year - memberdob.year - int((asofdate_dt.month, asofdate_dt.day) < (memberdob.month, memberdob.day))
                    if memberage == age:
                        foundmember = True
                        membername = member['name']
                    else:
                        self.missedmatches.append({'name':name,'asofdate':asofdate,'age':age,
                                                   'dbname':member['name'],'dob':member['dob'],
                                                   'ratio':getratio(name,member['name'])})
                # invalid dob in member database
                except ValueError:
                    foundmember = True
                    membername = member['name']
                if foundmember: break
                
        if foundmember:
            return membername,member['dob']
        else:
            return None
        
    #----------------------------------------------------------------------
    def getmissedmatches(self):
    #----------------------------------------------------------------------
        '''
        can be called after findmembers() to return list of members found in database, but did not match age
        
        :rtype: [{'name':requestedname,'asofdate':asofdate,'age':age,'dbname':membername,'dob':memberdob}, ...]
        '''
        
        return self.missedmatches
    
########################################################################
class XlClubMember(ClubMember):
########################################################################
    '''
    ClubMember object with excel input
    
    :params xlfilename: excel file from which club members are to be retrieved
    :params cutoff: cutoff for getmember.  float in (0,1].  higher means strings have to match more closely to be considered "close".  Default 0.6
    '''
    
    #----------------------------------------------------------------------
    def __init__(self,xlfilename,cutoff=0.6):
    #----------------------------------------------------------------------
        c = csvwt.Xls2Csv(xlfilename)   # allow automated header conversion

        # retrieve first sheet's csv filename
        csvfiles = c.getfiles()
        csvsheets = csvfiles.keys()
        csvfile = csvfiles[csvsheets[0]]

        # do all the work
        ClubMember.__init__(self,csvfile,cutoff=cutoff)
        
        ## csv files not needed any more
        #del c
    
########################################################################
class DbClubMember(ClubMember):
########################################################################
    '''
    ClubMember object with database input
    
    :params dbfilename: database file from which club members are to be retrieved
    :params cutoff: cutoff for getmember.  float in (0,1].  higher means strings have to match more closely to be considered "close".  Default 0.6
    :params **kwfilter: keyword parameters for racedb.Runner database filter
    '''
    
    #----------------------------------------------------------------------
    def __init__(self,dbfilename,cutoff=0.6,**kwfilter):
    #----------------------------------------------------------------------
        # create database session
        racedb.setracedb(dbfilename)
        s = racedb.Session()
        
        def _dob2excel(s,f):
            try:
                xl = tYmd.asc2excel(f)
            except ValueError:
                xl = None
            return xl
        
        # map database table column names to output column names, and optionally function for transformation
        # function x is x(s,f), where s is session, f is field value
        # note it is ok to split name like this, because it will just get joined together when the csv is processed in clubmember
        d = csvwt.Db2Csv()
        hdrmap = {'dateofbirth':{'DOB':_dob2excel},
                  'gender':'Gender',
                  'name':{'First':lambda s,f: ' '.join(f.split(' ')[0:-1]),'Last':lambda s,f: f.split(' ')[-1]},
                  'hometown':{'City':lambda s,f: ','.join(f.split(',')[0:-1]), 'State': lambda s,f: f.split(',')[-1]}
                    }
        d.addtable('Sheet1',s,racedb.Runner,hdrmap,**kwfilter)
        
        # done with database
        s.close()

        # retrieve first sheet's csv filename
        csvfiles = d.getfiles()
        csvsheets = csvfiles.keys()
        csvfile = csvfiles[csvsheets[0]]
        
        # do all the work
        ClubMember.__init__(self,csvfile,cutoff=cutoff)
        
        ## csv files not needed any more
        #del d
    
#----------------------------------------------------------------------
def main(): # TODO: Update this for testing
#----------------------------------------------------------------------
    pass
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()