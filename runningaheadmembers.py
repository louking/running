#!/usr/bin/python
###########################################################################################
# runningaheadmembers -- class pulls in individual memberships for later processing
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/11/15        Lou King        Create
#
#   Copyright 2015 Lou King
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

# standard
import csv
from datetime import datetime
import difflib

# home grown
from loutilities import timeu
ymd = timeu.asctime('%Y-%m-%d')
from loutilities.csvwt import wlist

class unsupportedFileType(): pass

########################################################################
class RunningAheadMember():
########################################################################
    '''
    Represents single RunningAHEAD member

    :param membership: membership record from RunningAHEAD export file
    '''

    # translate selected fields of file header to attributes we want to keep
    filehdr = 'MembershipType,FamilyName,GivenName,MiddleName,Gender,DOB,Email,EmailOptIn,PrimaryMember,RenewalDate,JoinDate,ExpirationDate,Street1,Street2,City,State,PostalCode,Country,Telephone,EntryType'.split(',')
    memberattr = 'membershiptype,lname,fname,mname,gender,dob,email,emailoptin,primarymember,renew,join,expiration,street1,street2,city,state,zip,country,telephone,entrytype'.split(',')
    memberxlate = dict(zip(filehdr,memberattr))

    # only repr these fields
    reprattr = 'fname,lname,dob,join,renew,expiration'.split(',')

    #----------------------------------------------------------------------
    def __init__(self,membership):
    #----------------------------------------------------------------------

        for key in self.filehdr:
            if key in self.memberxlate:
                setattr(self,self.memberxlate[key],membership[key])

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------

        reprval = '{}('.format(self.__class__)
        for attr in self.reprattr:
            if attr[0:2] == '__' or attr == 'fields': continue
            reprval += '{}={},'.format(attr,getattr(self,attr))
        reprval = reprval[:-1]  #remove trailing comma
        reprval += ')'
        return reprval



########################################################################
class RunningAheadMembers():
########################################################################
    '''
    Collect member data from RunningAHEAD individual membership export
    file, containing records from the beginning of the club's member
    registration until present.

    Provide access functions to gain access to these membership records.

    :param memberfile: member filename, filehandle or string of file records
    :param overlapfile: debug file to test for overlaps between records
    '''

    #----------------------------------------------------------------------
    def __init__(self,memberfile,overlapfile=None):
    #----------------------------------------------------------------------

        # initialize class attributes
        self.closematches = None
        self.names = {}
        self.dobnames = {}

        # check for type of memberfile, assume not opened here
        openedhere = False

        # if str, assume this is the filename
        if type(memberfile) == str:
            memberfileh = open(memberfile, 'rb')
            openedhere = True

        # if file, remember handle
        elif type(memberfile) == file:
            memberfileh = memberfile

        # if list, it works like a handle
        elif type(memberfile) in [list,wlist]:
            memberfileh = memberfile

        # otherwise, not handled
        else:
            raise unsupportedFileType

        # input is csv file
        INCSV = csv.DictReader(memberfileh)
        
        ## preprocess file to remove overlaps between join date and expiration date across records
        # each member's records are appended to a list of records in dict keyed by (lname,fname,dob)
        for membership in INCSV:
            asc_joindate = membership['JoinDate']
            asc_expdate = membership['ExpirationDate']
            fname = membership['GivenName']
            lname = membership['FamilyName']
            dob = membership['DOB']
            memberid = membership['MemberID']
            fullname = '{}, {}'.format(lname,fname)

            # get list of records associated with each member, pulling out significant fields
            thisrec = {'MemberID':memberid,'name':fullname,'join':asc_joindate,'expiration':asc_expdate,'dob':dob,'fullrec':membership,'RunningAheadMember':RunningAheadMember(membership)}
            # careful - this tuple order is assumed in several places
            thisname = (lname,fname,dob)
            if not thisname in self.names:
                self.names[thisname] = []
            self.names[thisname].append(thisrec)

        #debug
        if overlapfile:
            _OVRLP = open(overlapfile,'wb')
            OVRLP = csv.DictWriter(_OVRLP,['MemberID','name','dob','renewal','join','expiration','tossed'],extrasaction='ignore')
            OVRLP.writeheader()

        # sort list of records under each name, and remove overlaps between records
        # create dobnames access from self.names
        # self.dobnames allows access to self.names -- self.dobnames[dob] can be used to find key for self.names[lname,fname,dob]
        for thisname in self.names:
            # self.dobnames allows access to self.names key based on dob
            lname,fname,dob = thisname
            if dob not in self.dobnames:
                self.dobnames[dob] = []
            if (lname,fname) not in self.dobnames[dob]:
                self.dobnames[dob].append({'lname':lname,'fname':fname})

            # sort should result so records within a name are by join date within expiration year
            # see http://stackoverflow.com/questions/72899/how-do-i-sort-a-list-of-dictionaries-by-values-of-the-dictionary-in-python
            self.names[thisname] = sorted(self.names[thisname],key=lambda k: (k['expiration'],k['join']))
            toss = []
            for i in range(1,len(self.names[thisname])):
                # if overlapped record detected, push this record's join date after last record's expiration
                # note this only works for overlaps across two records -- if overlaps occur across three or more records that isn't detected
                # this seems ok as only two record problems have been seen so far
                if self.names[thisname][i]['join'] <= self.names[thisname][i-1]['expiration']:
                    lastexp_dt = ymd.asc2dt(self.names[thisname][i-1]['expiration'])
                    thisexp_dt = ymd.asc2dt(self.names[thisname][i]['expiration'])
                    jan1_dt = datetime(lastexp_dt.year+1,1,1)
                    jan1_asc = ymd.dt2asc(jan1_dt)
            
                    # ignore weird record anomalies where this record duration is fully within last record's
                    if jan1_dt > thisexp_dt:
                        toss.append(i)
                        self.names[thisname][i]['tossed'] = 'Y'
            
                    # debug
                    if overlapfile:
                        OVRLP.writerow(self.names[thisname][i-1])    # this could get written multiple times, I suppose
                        OVRLP.writerow(self.names[thisname][i])
            
                    # update this record's join dates
                    self.names[thisname][i]['join'] = jan1_asc
                    self.names[thisname][i]['fullrec']['JoinDate'] = jan1_asc
                    self.names[thisname][i]['RunningAheadMember'].join = jan1_asc
            
            # throw out anomalous records. reverse toss first so the pops don't change the indexes.
            toss.reverse()
            for i in toss:
                self.names[thisname].pop(i)

        # close the debug file if present
        if overlapfile:
            _OVRLP.close()

        # close the file if opened here
        if openedhere:
            memberfileh.close()

    #----------------------------------------------------------------------
    def membership_iter(self,raw = False):
    #----------------------------------------------------------------------
    # TODO: is raw needed?
        '''
        generator function that yields full record for each of memberships

        :param raw: True to yield dict, False to yield RunningAheadMember object, default False
        '''
        for thisname in self.names:
            for thismembership in self.names[thisname]:
                if not raw:
                    yield thismembership['RunningAheadMember']
                else:
                    yield thismembership['fullrec']

    #----------------------------------------------------------------------
    def member_iter(self,raw=False):
    #----------------------------------------------------------------------
    # TODO: is raw needed?
        '''
        generator function that yields latest membership record for each of names with
        JoinDate updated to earliest JoinDate

        :param raw: True to yield dict, False to yield RunningAheadMember object, default False
        '''
        for thisname in self.names:
            if not raw:
                thismembership = self.names[thisname][-1]['RunningAheadMember']
                thismembership.join = self.names[thisname][0]['join']
                yield thismembership
            else:
                thismembership = self.names[thisname][-1]['fullrec']
                thismembership['JoinDate'] = self.names[thisname][0]['join']
                yield thismembership

    #----------------------------------------------------------------------
    def getmember(self, memberkey):
    #----------------------------------------------------------------------
        '''
        retrieve latest membership record for memberkey with 
        JoinDate updated to earliest JoinDate

        :param memberkey: (lname,fname,dob)
        :rtype: RunningAheadMember object
        '''

        thismembership = self.names[memberkey][-1]['RunningAheadMember']
        thismembership.join = self.names[memberkey][0]['join']
        return thismembership

    #----------------------------------------------------------------------
    def getmemberships(self, memberkey):
    #----------------------------------------------------------------------
        '''
        retrieve list of membership records for memberkey

        :param memberkey: (lname,fname,dob)
        :rtype: [RunningAheadMember object, ...]
        '''

        thesememberships = []
        for thismembership in self.names[memberkey]:
            thesememberships.append(thismembership['RunningAheadMember'])
        return thesememberships

    #----------------------------------------------------------------------
    def getmemberkey(self, lname, fname, dob, cutoff=0.6, n=10):
    #----------------------------------------------------------------------
        '''
        retrieve member key based on name, dob

        if name wasn't found, None is returned
        if None is returned, check close matches using getclosematches()
        
        :param lname: last name
        :param fname: first name
        :param dob: date of birth yyyy-mm-dd
        :param cutoff: float in range (0,1] ratio of closeness to match name
        :param n: number of names checked for closeness (most similar)
        :rtype: (lname,fname,dob) or None if not found
        '''
        # no matches missed yet
        self.closematches = []

        # check dob
        if dob not in self.dobnames:
            return None

        # make list of members with this dob
        nameskeys = [('{} {}'.format(n['fname'],n['lname']).lower(),n) for n in self.dobnames[dob]]
        possiblenames = [nk[0] for nk in nameskeys]
        possiblekeys  = [(nk[1]['lname'],nk[1]['fname'],dob) for nk in nameskeys]

        # make list of close matches
        searchname = '{} {}'.format(fname,lname).lower()
        closematches = difflib.get_close_matches(searchname,possiblenames,n=10,cutoff=cutoff)
        for match in closematches:
            # this should be first time through loop, so self.closematches will be empty list
            if match == searchname:
                return possiblekeys[possiblenames.index(match)]
            else:
                self.closematches.append(possiblekeys[possiblenames.index(match)])

        # didn't find exact match
        return None


    #----------------------------------------------------------------------
    def getclosematchkeys(self):
    #----------------------------------------------------------------------
        '''
        can be called after findmembers() to return list of members found, but did not match exactly
        
        :rtype: [(lname,fname,dob), ...]
        '''
        
        return self.closematches
