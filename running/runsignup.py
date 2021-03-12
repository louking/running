###########################################################################################
#   runsignup - access methods for runsignup.com
#
#   Date        Author      Reason
#   ----        ------      ------
#   12/31/17    Lou King    Create from runningahead.com
#
#   Copyright 2017 Lou King
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
runsignup - access methods for runsignup.com
===================================================
'''

# standard
import logging
from threading import RLock
from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from os.path import dirname, abspath
from os import stat, chmod, rename, remove
from tempfile import NamedTemporaryFile

# pypi
import requests

# github

# other

# home grown
from loutilities.configparser import getitems
from loutilities. timeu import asctime
from loutilities.transform import Transform
from loutilities.csvwt import record2csv
from loutilities.nicknames import NameDenormalizer
names = NameDenormalizer()

# login API (deprecated)
login_url = 'https://runsignup.com/rest/login'
logout_url = 'https://runsignup.com/rest/logout'
members_url = 'https://runsignup.com/rest/club/{club_id}/members'

# OAuth stuff - NOT USED
# request_token_url = 'https://runsignup.com/oauth/requestToken.php'
# verify_url = 'https://runsignup.com/OAuth/Verify'
# access_token_url = 'https://runsignup.com/oauth/accessToken.php'

KMPERMILE = 1.609344

class accessError(Exception): pass
class notImplemented(Exception): pass
class parameterError(Exception): pass


thislogger = logging.getLogger("running.runsignup")

########################################################################
class RunSignUp():
    '''
    access methods for RunSignUp.com

    either key and secret OR email and password should be supplied
    key and secret take precedence

    :param key: key from runsignup (direct key, no OAuth)
    :param secret: secret from runsignup (direct secret, no OAuth)
    :param email: email for use by Login API (deprecated)
    :param password: password for use by Login API (deprecated)
    :param debug: set to True for debug logging of http requests, default False
    '''

    #----------------------------------------------------------------------
    def __init__(self, key=None, secret=None, email=None, password=None, debug=False):
        """
        initialize
        """

        # does user want to debug?
        logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
        if debug:
            # set up debug logging
            thislogger.setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        else:
            # turn off debug logging
            thislogger.setLevel(logging.NOTSET)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.NOTSET)
            requests_log.propagate = False

        if (not key and not email):
            raise parameterError('either key/secret or email/password must be supplied')
        if (key and not secret) or (secret and not key):
            raise parameterError('key and secret must be supplied together')
        if (email and not password) or (password and not email):
            raise parameterError('email and password must be supplied together')

        self.key = key
        self.secret = secret
        self.email = email
        self.password = password
        self.debug = debug
        self.client_credentials = {}
        if key:
            self.credentials_type = 'key'
        else:
            self.credentials_type = 'login'

    #----------------------------------------------------------------------
    def __enter__(self):
        self.open()
        return self

    #----------------------------------------------------------------------
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    #----------------------------------------------------------------------
    def open(self):

        # set up session for multiple requests
        self.session = requests.Session()

        # key / secret supplied - this take precedence
        if self.credentials_type == 'key':
            self.client_credentials = {'api_key'    : self.key,
                                       'api_secret' : self.secret}

        # email / password supplied
        else:     
            # login to runsignup - note temporary keys will expire 1 hour after last API call
            # see https://runsignup.com/API/login/POST
            r = requests.post(login_url, params={'format' : 'json'}, data={'email' : self.email, 'password' : self.password})
            resp = r.json()

            self.credentials_type = 'login'
            self.client_credentials = {'tmp_key'    : resp['tmp_key'],
                                       'tmp_secret' : resp['tmp_secret']}

    #----------------------------------------------------------------------
    def close(self):
        '''
        close down
        '''
        self.client_credentials = {}
        self.session.close()

        # TODO: should we also log out?

    #----------------------------------------------------------------------
    def members(self, club_id, **kwargs):
        '''
        return members accessible to this application

        :param club_id: numeric club id
        :param kwargs: non-default arguments, per https://runsignup.com/API/club/:club_id/members/GET
        :return: members list (format per https://runsignup.com/API/club/:club_id/members/GET)
        '''
        """
        return members accessible to this application
        """
        
        # max number of users in user list is 100, so need to loop, collecting
        # BITESIZE users at a time.  These are all added to users list, and final
        # list is returned to the caller
        BITESIZE = 100
        page = 1
        members = []
        while True:
            data = self._rsuget(members_url.format(club_id=club_id),
                                page=page,
                                results_per_page=BITESIZE,
                                include_questions = 'T',
                                **kwargs
                               )
            if len(data['club_members']) == 0: break

            theseusers = data['club_members']
            
            members += theseusers
            page += 1

            # stop iterating if we've reached the end of the data
            if len(data['club_members']) < BITESIZE: break
        
        return members
        
    #----------------------------------------------------------------------
    def _rsuget(self, methodurl, **payload):
        """
        get method for runsignup access
        
        :param methodurl: runsignup method url to call
        :param contentfield: content field to retrieve from response
        :param **payload: parameters for the method
        """
        
        thispayload = self.client_credentials.copy()
        thispayload.update(payload)
        thispayload.update({'format':'json'})

        resp = self.session.get(methodurl, params=thispayload)
        if resp.status_code != 200:
            raise accessError('HTTP response code={}, url={}'.format(resp.status_code,resp.url))

        data = resp.json()

        if 'error' in data:
            raise accessError('RSU response code={}-{}, url={}'.format(data['error']['error_code'],data['error']['error_msg'],resp.url))
    
        return data 
        
#----------------------------------------------------------------------
def updatemembercache(club_id, membercachefilename, key=None, secret=None, email=None, password=None, debug=False):
    if debug:
        # set up debug logging
        thislogger.setLevel(logging.DEBUG)
        thislogger.propagate = True
    else:
        # error logging
        thislogger.setLevel(logging.ERROR)
        thislogger.propagate = True

    # set up access to RunSignUp
    rsu = RunSignUp(key=key, secret=secret, email=email, password=password, debug=debug)
    rsu.open()

    # transform from RunSignUp to membercache format
    xform = Transform( {
                        'MemberID'       : lambda mem: mem['user']['user_id'],
                        'MembershipID'   : 'membership_id',
                        'MembershipType' : 'club_membership_level_name',
                        'FamilyName'     : lambda mem: mem['user']['last_name'],
                        'GivenName'      : lambda mem: mem['user']['first_name'],
                        'MiddleName'     : lambda mem: mem['user']['middle_name'],
                        'Gender'         : lambda mem: 'Female' if mem['user']['gender'] == 'F' else 'Male',
                        'DOB'            : lambda mem: mem['user']['dob'],
                        'Email'          : lambda mem: mem['user']['email'] if 'email' in mem['user'] else '',
                        'PrimaryMember'  : 'primary_member',
                        'JoinDate'       : 'membership_start',
                        'ExpirationDate' : 'membership_end',
                        'LastModified'   : 'last_modified',
                       },
                       sourceattr=False, # source and target are dicts
                       targetattr=False
                     )

    # members maintains the current cache through this processing {memberkey: [memberrec, ...]}
    # currmemberrecs maintains the records for current members as of today {memberkey: memberrec}
    members = {}
    currmemberrecs = {}

    # need today's date, in same sortable date format as data coming from RunSignUp
    dt = asctime('%Y-%m-%d')
    today = dt.dt2asc(datetime.now())

    # construct key from member cache record
    def getmemberkey(memberrec):
        lastname = memberrec['FamilyName']
        firstname = memberrec['GivenName']
        dob = memberrec['DOB']
        memberkey = '{},{},{}'.format(lastname, firstname, dob)
        return memberkey

    # add record to cache, return key
    def add2cache(memberrec):
        memberkey = getmemberkey(memberrec)
        members.setdefault(memberkey,[])

        # replace any records having same expiration date
        recordlist = [mr for mr in members[memberkey] if mr['ExpirationDate'] != memberrec['ExpirationDate']] + [memberrec]
        members[memberkey] = recordlist

        # keep list sorted
        sortby = 'ExpirationDate'
        members[memberkey].sort(key=lambda item: item[sortby])

        # remove any overlaps
        for i in range(1, len(members[memberkey])):
            lastrec = members[memberkey][i-1]
            thisrec = members[memberkey][i]
            # if there's an overlap, change join date to expiration date + 1 day
            if thisrec['JoinDate'] <= lastrec['ExpirationDate']:
                exp = thisrec['ExpirationDate']
                oldstart = thisrec['JoinDate']
                newstart = dt.dt2asc( dt.asc2dt(lastrec['ExpirationDate']) + timedelta(1) )
                thislogger.error('overlap detected: {} end={} was start={} now start={}'.format(memberkey, exp, oldstart, newstart))
                thisrec['JoinDate'] = newstart

        return memberkey

    # test if in cache
    def incache(memberrec):
        memberkey = getmemberkey(memberrec)
        if memberkey not in members:
            cachedmember = False
        elif memberrec['ExpirationDate'] in [m['ExpirationDate'] for m in members[memberkey]]:
            cachedmember = True
        else:
            cachedmember = False

        return cachedmember

    # lock cache update during execution
    rlock = RLock()
    with rlock:
        # track duration of update
        starttime = datetime.now()

        # import current cache
        # records in cache are organized in members dict with 'last,first,dob' key
        # within is list of memberships ordered by expiration date
        with open(membercachefilename, newline='') as memfile:
            # members maintains the current cache through this processing
            # currmemberrecs maintains the records for current members as of today
            cachedmembers = DictReader(memfile)
            for memberrec in cachedmembers:
                memberkey = add2cache(memberrec)

                # current member?
                if memberrec['JoinDate'] <= today and memberrec['ExpirationDate'] >= today:
                    # member should only be in current members once
                    if memberkey in currmemberrecs:
                        thislogger.error( 'member duplicated in cache: {}'.format(memberkey) )
                    
                    # regardless add this record to current members
                    currmemberrecs[memberkey] = memberrec

        # get current members from RunSignUp, transforming each to cache format
        rsumembers = rsu.members(club_id)
        rsucurrmembers = []
        for rsumember in rsumembers:
            memberrec = {}
            xform.transform(rsumember, memberrec)
            rsucurrmembers.append(memberrec)

        # add new member records to cache
        # remove known (not new) member records from currmemberrecs
        # after loop currmemberrecs should contain only deleted member records
        for memberrec in rsucurrmembers:
            # remember if was incache before we add
            currmember = incache(memberrec)

            # this will replace record with same ExpirationDate
            # this allows admin updated RunSignUp data to be captured in cache
            memberkey = add2cache(memberrec)

            # remove member records we knew about already
            # if not there, skip. probably replaced record in cache
            if currmember:
                try:
                    del currmemberrecs[memberkey]
                except KeyError:
                    pass

        # remove member records for deleted members
        for memberkey in currmemberrecs:
            removedrec = currmemberrecs[memberkey]
            memberkey = getmemberkey(removedrec)
            members[memberkey] = [mr for mr in members[memberkey] if mr != removedrec]
            thislogger.debug('membership removed from cache: {}'.format(removedrec))

        # recreate cache file
        # start with temporary file
        # sort members keys for ease of debugging
        cachedir = dirname(abspath(membercachefilename))
        sortedmembers = sorted(members.keys())
        with NamedTemporaryFile(mode='w', suffix='.rsucache', delete=False, dir=cachedir, newline='') as tempcache:
            tempmembercachefilename = tempcache.name
            cachehdr = 'MemberID,MembershipID,MembershipType,FamilyName,GivenName,MiddleName,Gender,DOB,Email,PrimaryMember,JoinDate,ExpirationDate,LastModified'.split(',')
            cache = DictWriter(tempcache, cachehdr)
            cache.writeheader()
            for memberkey in sortedmembers:
                for memberrec in members[memberkey]:
                    cache.writerow(memberrec)

        # set mode of temp file to be same as current cache file (see https://stackoverflow.com/questions/5337070/how-can-i-get-a-files-permission-mask)
        cachemode = stat(membercachefilename).st_mode & 0o777
        chmod(tempmembercachefilename, cachemode)

        # now overwrite the previous version of the membercachefile with the new membercachefile
        try:
            # atomic operation in Linux
            rename(tempmembercachefilename, membercachefilename)

        # should only happen under windows
        except OSError:
            remove(membercachefilename)
            rename(tempmembercachefilename, membercachefilename)

        # track duration of update
        finishtime = datetime.now()
        thislogger.debug( 'updatemembercache() duration={}'.format(finishtime-starttime) )

    # release access
    rsu.close()

    # let caller know the current members, in rsu api format
    return rsumembers

#----------------------------------------------------------------------
def members2csv(club_id, key, secret, mapping, filepath=None):
    '''
    Access club_id through RunSignUp API to retrieve members. Return
    list of members as if csv file. Optionally save csv file.

    :param club_id: club_id from RunSignUp
    :param key: api key for RunSignUp
    :param secret: api secret for RunSignUp
    :param mapping: OrderedDict {'outfield1':'infield1', 'outfield2':outfunction(inrec), ...} or ['inoutfield1', 'inoutfield2', ...]
    :param normfile: (optional) pathname to save csv file
    :rtype: csv file records, as list
    '''

    # get the members from the RunSignUp API
    with RunSignUp(key=key, secret=secret) as rsu:
        members = rsu.members(club_id)

    filerows = record2csv(members, mapping, filepath)

    return filerows

########################################################################
class ClubMembership():
    '''
    holds attributes for club membership
    '''
    # set up transformation to flatten record into ClubMembership object with attributes named as Transform keys
    # transform is from RunSignUp.members.get - see https://runsignup.com/API/club/:club_id/members/GET
    xformmapping = {
        'user_id': lambda mem: mem['user']['user_id'],
        'membership_id': 'membership_id',
        'club_membership_level_name': 'club_membership_level_name',
        'last_name': lambda mem: mem['user']['last_name'],
        'first_name': lambda mem: mem['user']['first_name'],
        'middle_name': lambda mem: mem['user']['middle_name'],
        'gender': lambda mem: mem['user']['gender'],
        'dob': lambda mem: mem['user']['dob'],
        'email': lambda mem: mem['user']['email'].lower() if 'email' in mem['user'] else '',
        'phone': lambda mem: mem['user']['phone'] if 'phone' in mem['user'] else '',
        'street': lambda mem: mem['user']['address']['street'] if 'address' in mem['user'] and 'street' in mem['user']['address'] else '',
        'city': lambda mem: mem['user']['address']['city'] if 'address' in mem['user'] and 'city' in mem['user']['address'] else '',
        'state': lambda mem: mem['user']['address']['state'] if 'address' in mem['user'] and 'state' in mem['user']['address'] else '',
        'zipcode': lambda mem: mem['user']['address']['zipcode'] if 'address' in mem['user'] and 'state' in mem['user']['address'] else '',
        'primary_member': 'primary_member',
        'membership_start': 'membership_start',
        'membership_end': 'membership_end',
        'last_modified': 'last_modified',
    }
    # don't convert any of this to int / float, except user_id, membership_id, zipcode
    knownstrings = list(xformmapping.keys())
    knownstrings.remove('user_id')
    knownstrings.remove('membership_id')
    knownstrings.remove('zipcode')
    xform = Transform(xformmapping,
        sourceattr=False,   # source is dict
        targetattr=True,    # target is ClubMembership
        knownstrings=knownstrings,
    )

    def transform(self, rawrsumembership):
        ClubMembership.xform.transform(rawrsumembership, self)

########################################################################
class ClubMember():
    '''
    holds club member object
    '''
    def __init__(self, **kwargs):
        for arg in kwargs:
            setattr(self, arg, kwargs[arg])

########################################################################
class ClubMemberships():
    '''
    determine members based on RunSignUp memberships

    example usage:

        with RunSignUp(key=key, secret=secret) as rsu:
            memberships = rsu.members(club_id, current_members_only=current_members_only, **memberargs)
        clubmemberships = ClubMemberships(memberships)

    :param memberships: memberships retrieved from RunSignUp
    :param membershipcache: todo: (optional) cache file specific for ClubMemberships
    '''

    userfields = ['first_name', 'last_name', 'email', 'street', 'city', 'dob', 'primary_member']
    alluserfields = ['user_id'] + userfields

    def __init__(self, memberships, membershipcache=None):
        '''
        load memberships data structure
        '''
        self.memberships = memberships

        # first pass, collect all memberships by dob
        self.attr2mships = {}
        for field in ClubMemberships.alluserfields:
            self.attr2mships[field] = {}

        for rsumembership in self.memberships:
            membership = ClubMembership()
            membership.transform(rsumembership)
            for field in ClubMemberships.alluserfields:
                self.attr2mships[field].setdefault(getattr(membership, field), [])
                self.attr2mships[field][getattr(membership, field)].append(membership)

        # make convenience handles
        self.userid2mships = self.attr2mships['user_id']
        self.firstname2mships = self.attr2mships['first_name']
        self.lastname2mships = self.attr2mships['last_name']
        self.email2mships = self.attr2mships['email']
        self.street2mships = self.attr2mships['street']
        self.city2mships = self.attr2mships['city']
        self.dob2mships = self.attr2mships['dob']

        # collect nicknames, and lastnames for debugging
        self.nicknames = []
        self.lastnames = []

        # second pass, try to identify members
        # main hash key is first user_id encountered for member (should be most recently used)
        # assumes member hasn't changed dob, but if they did we simply find two members
        self.userid2mem = {}
        self.alias2userid = {}
        for dob in self.dob2mships:
            # order of most recent membership_id first causes us to pick up last used name, address, user_id, etc
            self.dob2mships[dob].sort(key=lambda item: item.membership_id, reverse=True)

            # prepare to check for common person among memberships by saving some associations
            # note all of these have the same date of birth
            lastfirsts = {}
            firsts = {}
            lasts = {}
            for m in self.dob2mships[dob]:
                lastfirst = '{}/{}'.format(m.last_name, m.first_name).lower()
                lastfirsts.setdefault(lastfirst, [])
                lastfirsts[lastfirst].append(m)
                first = m.first_name.lower()
                firsts.setdefault(first, [])
                firsts[first].append(m)
                last = m.last_name.lower()
                lasts.setdefault(last, [])
                lasts[last].append(m)

            for mship in self.dob2mships[dob]:
                # prepare to check for common person
                thislastfirst = '{}/{}'.format(mship.last_name, mship.first_name).lower()
                thisfirst = mship.first_name.lower()
                thislast = mship.last_name.lower()
                thesenames = names.get(mship.first_name)

                # controls testing
                found = False

                # if we've seen this user_id before, then we know it's the same member
                if mship.user_id in self.userid2mem:
                    self.userid2mem[mship.user_id].mships.append(mship)
                    found = True

                # see if we have found this alias user_id before
                if not found and mship.user_id in self.alias2userid:
                    self.userid2mem[self.alias2userid[mship.user_id]].mships.append(mship)
                    found = True

                # maybe member is using the same name but a different user id
                if not found and thislastfirst in lastfirsts:
                    # check other memberships with same name and same birth date
                    for m in lastfirsts[thislastfirst]:
                        # if another membership has been recorded and matches this name probably same member
                        if m.user_id in self.userid2mem:
                            found = True
                            self.alias2userid[mship.user_id] = m.user_id
                            self.userid2mem[m.user_id].user_ids.append(mship.user_id)
                            self.userid2mem[m.user_id].mships.append(mship)
                            break

                # maybe member has changed their last name but has the same first name but different user id
                # most likey change of last name happens with a woman
                # thisfirst is derived from mship.first_name
                if not found and thisfirst in firsts and mship.gender == 'F':
                    # check other memberships with same first name and same birth date
                    for m in firsts[thisfirst]:
                        # if another membership has been recorded and matches this first name
                        # and phone number probably same member
                        if m.user_id in self.userid2mem and m.phone == mship.phone:
                            found = True
                            self.alias2userid[mship.user_id] = m.user_id
                            self.userid2mem[m.user_id].user_ids.append(mship.user_id)
                            self.userid2mem[m.user_id].mships.append(mship)

                            # for debugging
                            self.lastnames.append('{} ; {}'.format(
                                '{} {}'.format(m.first_name, m.last_name),
                                '{} {}'.format(mship.first_name, mship.last_name)
                            ))
                            break

                # maybe member is using a nickname which is different from a first name used in an earlier membership.
                # check for this if the last name is the same
                # thislast is derived from mship.last_name
                if not found and thislast in lasts:
                    for m in lasts[thislast]:
                        # if another membership has been recorded, and matches this last name
                        # and the first name is a derivative of the current name, probably the same member
                        # thesenames is derived from mship.first_name, may be None if no derivative names found
                        if m.user_id in self.userid2mem and thesenames and m.first_name.lower() in thesenames:
                            found = True
                            self.alias2userid[mship.user_id] = m.user_id
                            self.userid2mem[m.user_id].user_ids.append(mship.user_id)
                            self.userid2mem[m.user_id].mships.append(mship)

                            # for debugging
                            self.nicknames.append('{} ; {}'.format(
                                '{} {}'.format(m.first_name, m.last_name),
                                '{} {}'.format(mship.first_name, mship.last_name)
                            ))
                            break

                # otherwise assume this is a new member - create user_id record
                # note since we sorted earlier, these should be the most recent attr values
                if not found:
                    self.userid2mem[mship.user_id] = ClubMember(user_ids=[mship.user_id], mships=[mship])
                    for attr in ClubMemberships.userfields:
                        setattr(self.userid2mem[mship.user_id], attr, getattr(mship, attr))

    def filter_by(self, **filters):
        '''
        return memberships which match indicated attributes

        :param filters: dict of attributes/values to match/filter
        :return: list of ClubMembership items, ordered from most recent to least recent
        '''
        if not filters:
            raise parameterError('filter_by: must have some filters specified')
        for key in filters:
            if key not in ClubMemberships.userfields:
                raise parameterError('filter_by: filters keys must be one of {}'.format(ClubMemberships.userfields))

        first = True
        for key, val in filters.items():
            # handle first filter to get initial set
            if first:
                memberships = set(self.attr2mships[key][val])
                first = False
            # and (&) the remaining filters results into set
            else:
                key, val = next(filters)
                memberships &= set(self.attr2mships[key][val])

        # caller wants sorted list most recent membership first
        return list(memberships).sort(key=lambda m: m.membership_id, reverse=True)

    def members(self):
        '''
        generator function to retrieve members, in no particular order

        :return: ClubMember iterator
        '''
        return (
            self.userid2mem[member]
            for member in self.userid2mem
        )
