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
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

# github

# other

# home grown
from loutilities.configparser import getitems
from loutilities. timeu import asctime
from loutilities.transform import Transform
from loutilities.csvwt import record2csv

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
########################################################################
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
    #----------------------------------------------------------------------
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
            raise parameterError, 'either key/secret or email/password must be supplied'
        if (key and not secret) or (secret and not key):
            raise parameterError, 'key and secret must be supplied together'
        if (email and not password) or (password and not email):
            raise parameterError, 'email and password must be supplied together'

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
    #----------------------------------------------------------------------
        self.open()
        return self

    #----------------------------------------------------------------------
    def __exit__(self, exc_type, exc_value, traceback):
    #----------------------------------------------------------------------
        self.close()

    #----------------------------------------------------------------------
    def open(self):
    #----------------------------------------------------------------------

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
    #----------------------------------------------------------------------
        '''
        close down
        '''
        self.client_credentials = {}
        self.session.close()

        # TODO: should we also log out?

    #----------------------------------------------------------------------
    def members(self, club_id):
    #----------------------------------------------------------------------
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
                                include_questions = 'T'
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
    #----------------------------------------------------------------------
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
            raise accessError, 'HTTP response code={}, url={}'.format(resp.status_code,resp.url)

        data = resp.json()

        if 'error' in data:
            raise accessError, 'RSU response code={}-{}, url={}'.format(data['error']['error_code'],data['error']['error_msg'],resp.url)
    
        return data 
        
#----------------------------------------------------------------------
def updatemembercache(club_id, membercachefilename, key=None, secret=None, email=None, password=None, debug=False):
#----------------------------------------------------------------------
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
        members[memberkey].sort(lambda a,b: cmp(a[sortby],b[sortby]))

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
        with open(membercachefilename, 'rb') as memfile:
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
        with NamedTemporaryFile(mode='wb', suffix='.rsucache', delete=False, dir=cachedir) as tempcache:
            tempmembercachefilename = tempcache.name
            cachehdr = 'MemberID,MembershipID,MembershipType,FamilyName,GivenName,MiddleName,Gender,DOB,Email,PrimaryMember,JoinDate,ExpirationDate,LastModified'.split(',')
            cache = DictWriter(tempcache, cachehdr)
            cache.writeheader()
            for memberkey in sortedmembers:
                for memberrec in members[memberkey]:
                    cache.writerow(memberrec)

        # set mode of temp file to be same as current cache file (see https://stackoverflow.com/questions/5337070/how-can-i-get-a-files-permission-mask)
        cachemode = stat(membercachefilename).st_mode & 0777
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
#----------------------------------------------------------------------
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

