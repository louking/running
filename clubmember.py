#!/usr/bin/python
###########################################################################################
# clubmember - manage club member information 
#
#	Date		Author		Reason
#	----		------		------
#       01/07/13        Lou King        Create
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
# 12/30 is used below because excel incorrectly treats 1900 as leap year
# here, we're assuming that noone was born in 1900, which seems safe
# see http://www.lexicon.net/sjmachin/xlrd.html for more details
EXCELEPOCH = tYmd.asc2dt('1899-12-30')

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
            thismember['name'] = name
            try:
                dob = tYmd.dt2asc(EXCELEPOCH + datetime.timedelta(thisrow_dict['DOB']))
            except TypeError:   # handle invalid dates
                dob = None
            thismember['dob'] = dob
            thismember['gender'] = thisrow_dict['Gender']
            thismember['hometown'] = ', '.join([thisrow_dict['City'],thisrow_dict['State']])
            if name not in self.members:
                self.members[name] = []
            self.members[name].append(thismember)    # allows for possibility that multiple members have same name
    
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
        closematches = difflib.get_close_matches(name,self.members.keys())
        
        rval = {}
        if len(closematches) > 0:
            topmatch = closematches.pop(0)
            rval['exactmatch'] = (name.lower() == topmatch.lower()) # ok to ignore case
            rval['matchingmembers'] = self.members[topmatch][:] # make a copy
            rval['closematches'] = closematches[:]
            
        return rval
        
#----------------------------------------------------------------------
def main(): # TODO: Update this for testing
#----------------------------------------------------------------------
    pass
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()