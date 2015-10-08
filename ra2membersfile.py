#!/usr/bin/python
###########################################################################################
#   ra2membersfile - retrieve RunningAHEAD member file to be put into file similar to RA export file
#
#   Date        Author      Reason
#   ----        ------      ------
#   09/17/15    Lou King    Create
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
'''
ra2membersfile - retrieve RunningAHEAD member file to be put into file similar to RA export file
=========================================================================================================
'''

# standard
import unicodecsv
import pdb
import argparse

# pypi

# github

# other

# home grown
import runningahead
filehdr = ["MemberID","MembershipType","FamilyName","GivenName","MiddleName","Gender","DOB","Email","EmailOptIn","PrimaryMember","RenewalDate","JoinDate","ExpirationDate","Street1","Street2","City","State","PostalCode","Country","Telephone","EntryType"
]
from loutilities import csvwt

#----------------------------------------------------------------------
def adddetails(details, memberrecord):
#----------------------------------------------------------------------
    '''
    add details of membership to member record

    :param id: member implied
    :param memberrecord: dict to be updated with detailed information
    '''

    memberrecord['FamilyName'] = details['person'].get('familyName',None)
    memberrecord['GivenName'] = details['person'].get('givenName',None)
    memberrecord['MiddleName'] = details['person'].get('middleName',None)
    gender = details['person'].get('gender',None)
    memberrecord['Gender'] = 'Male' if gender == 'm' else 'Female' if gender == 'f' else None
    memberrecord['DOB'] = details['person'].get('birthDate',None)
    memberrecord['Email'] = details['person'].get('email',None)
    memberrecord['Telephone'] = details['person'].get('phone',None)

    # EmailOptIn

    # RenewalDate
    # ExpirationDate may have already been put in record, if so that takes precedence because it is
    # specific to this record while details has latest expiration date for member
    if 'ExpirationDate' not in memberrecord or not memberrecord['ExpirationDate']:
        memberrecord['ExpirationDate'] = details.get('expiration',None)
    memberrecord['JoinDate'] = details.get('join',None)

    memberrecord['Street1'] = details['address'].get('street1',None)
    memberrecord['Street2'] = details['address'].get('street2',None)
    memberrecord['City'] = details['address'].get('city',None)
    memberrecord['State'] = details['address'].get('state',None)
    memberrecord['PostalCode'] = details['address'].get('postalCode',None)
    memberrecord['Country'] = details['address'].get('country',None)

    # EntryType

#----------------------------------------------------------------------
def ra2members(club, accesstoken, membercachefilename=None, update=False, filename=None, debug=False, **filters):
#----------------------------------------------------------------------
    '''
    retrieve RunningAHEAD members and create a file or list containing
    the member data, similar to export format from RunningAHEAD

    :param club: RunningAHEAD slug for club name
    :param accesstoken: access token for a priviledged viewer for this club
    :param membercachefilename: name of optional file to cache detailed member data
    :param update: update member cache based on latest information from RA
    :param filename: name of file for output. If None, list is returned and file is not created
    :param debug: True turns on requests debug
    :param filters: see http://api.runningahead.com/docs/club/list_members for valid filters
    '''

    # initialize
    ra = runningahead.RunningAhead(membercachefilename=membercachefilename, debug=debug)
    memberlist = csvwt.wlist()
    members = unicodecsv.DictWriter(memberlist,filehdr)
    members.writeheader()

    # retrieve membership types
    membershiptypes = ra.listmembershiptypes(club,accesstoken)
    mshipxlate = {}
    for membershiptype in membershiptypes:
        mshipxlate[membershiptype['id']] = membershiptype['name']

    # retrieve memberships
    memberships = ra.listmemberships(club,accesstoken,**filters)

    # loop for each membership, saving information for each of the members in the membership
    for membership in memberships:
        member = {'PrimaryMember':'Yes'}
        member['MemberID'] = '@{}'.format(membership['id'])
        member['MembershipType'] = mshipxlate[membership['membershipId']]
        # need to get expiration from top record, else latest expiration is retrieved
        member['ExpirationDate'] = membership.get('expiration',None)
        adddetails(ra.getmember(club, membership['id'], accesstoken, update=update), member)
        members.writerow(member)

        # collect records for secondary members, if there are any
        member['PrimaryMember'] = None
        if 'members' in membership:
            for thismember in membership['members']:
                adddetails(ra.getmember(club, thismember['id'], accesstoken, update=update), member)
                members.writerow(member)

    # clean up
    ra.close()
    
    # write the file if requested
    if filename:
        with open(filename,'wb') as outfile:
            outfile.writelines(memberlist)

    return memberlist

#----------------------------------------------------------------------
def file2members(fname):
#----------------------------------------------------------------------
    '''
    debug function to read file created by ra2members and return memberlist

    :param fname: name of file
    :rtype: list of strings read from file, suitable for input to csv.DictReader
    '''
    with open(fname,'rb') as infile:
        memberlist = infile.readlines()

    return memberlist
    
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    retrieve members from RunningAHEAD and create a file similar to RA export file
    '''
    
    parser = argparse.ArgumentParser(description=descr,formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('running',version.__version__))
    args = parser.parse_args()

    # this would be a good place for unit tests
    
# ##########################################################################################
#   __main__
# ##########################################################################################
if __name__ == "__main__":
    main()