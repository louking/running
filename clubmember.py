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

# pypi
import xlrd

# github

# home grown
import version
from loutilities import timeu

# exceptions for this module.  See __init__.py for package exceptions

# module globals
tYmd = timeu.asctime('%Y-%m-%d')
tHMS = timeu.asctime('%H:%M:%S')
tMS  = timeu.asctime('%M:%S')

########################################################################
class ClubMember():
########################################################################
    '''
    ClubMember object 
    
    :params filename: excel file from which club members are to be retrieved
    '''
    #----------------------------------------------------------------------
    def __init__(self,filename):
    #----------------------------------------------------------------------
        # get the worksheet from the workbook
        workbook = xlrd.open_workbook(filename)
        sheet = workbook.sheet_by_index(0)    # only first sheet is considered
        workbook.release_resources()    # sheet is already loaded so we can save memory
        
        # header row is first, has at least First,Last,DOB,Gender,City,State
        hdr = sheet.row_values(0)
        
        # collect member information by member name
        self.members = {}
        
        nrows = sheet.nrows
        for rowndx in range(1,nrows):
            thisrow_list = sheet.row_values(rowndx)
            thisrow_dict = dict(zip(hdr,thisrow_list))
            name = ' '.join([thisrow_dict['First'],thisrow_dict['Last']])
            thismember = {}
            thismember['name'] = name.strip()
            if thismember['name'] == '': continue   # skip empty names, probably junk at the bottom of member list
            try:
                dob = tYmd.dt2asc(timeu.excel2dt(thisrow_dict['DOB']))
            except TypeError:   # handle invalid dates
                dob = None
            thismember['dob'] = dob
            thismember['gender'] = thisrow_dict['Gender'].upper().strip()
            thismember['hometown'] = ', '.join([thisrow_dict['City'].strip(),thisrow_dict['State'].strip()])
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
        # TODO: age should be input to this function, and used to determine if match found
        closematches = difflib.get_close_matches(name,self.members.keys())
        
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
        
        if name wasn't found, None is returned
        if no dob in members file, None is returned for dateofbirth
        
        :param name: name to search for
        :param age: age to match for
        :param asofdate: 'yyyy-mm-dd' date for which age is to be matched
        :rtype: (name,dateofbirth) or None if not found
        '''
        
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
                    # TODO: grandprix divisions are from age at Jan 1, while age grading depends on racedate
                    memberage = asofdate_dt.year - memberdob.year - int((asofdate_dt.month, asofdate_dt.day) < (memberdob.month, memberdob.day))
                    if memberage == age:
                        foundmember = True
                        membername = member['name']
                # invalid dob in member database
                except ValueError:
                    foundmember = True
                    membername = member['name']
                if foundmember: break
                
        if foundmember:
            return membername,memberdob
        else:
            return None
        
#----------------------------------------------------------------------
def main(): # TODO: Update this for testing
#----------------------------------------------------------------------
    pass
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()