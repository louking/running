#!/usr/bin/python
###########################################################################################
# racedb  -- manage race database
#
#	Date		Author		Reason
#	----		------		------
#       01/23/13        Lou King        Create
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
racedb  -- manage race database
===================================================

racedb has the following tables:

* runner
    * name (keyfield)
    * dateofbirth (yyyy-mm-dd)
    * id (incr for join)
    * gender (M/F)
    * hometown (city, ST)
    * active (true/false)
    * lastupdate (yyyy-mm-dd hh:mm:ss)
    
* race
    * name
    * date (yyyy-mm-dd)
    * id (incr for join)
    * starttime
    * distance (miles)
    
* raceresult
    * runner/id
    * race/id
    * time (seconds)
    * overallplace
    * genderplace
    * divisionplace
    * lastupdate (yyyy-mm-dd hh:mm:ss)
    
'''

# standard
import pdb
import argparse
import sqlite3
import time

# pypi

# github

# home grown
from running import *
import version
from loutilities import timeu
import clubmember,racefile

t = timeu.asctime('%Y-%m-%d')

########################################################################
class RaceDB():
########################################################################
    '''
    manage race database
    
    :params dbfilename: filename for race database
    '''
    #----------------------------------------------------------------------
    def __init__(self,dbfilename):
    #----------------------------------------------------------------------
        
        # set up connection to db
        self.con = sqlite3.connect(dbfilename,detect_types=True)
        self.con.row_factory = sqlite3.Row
        
        #* runner
        #    * runnername (keyfield)
        #    * dateofbirth (yyyy-mm-dd) (keyfield)
        #    * runnerid (incr for join)
        #    * gender (M/F)
        #    * hometown (city, ST)
        #    * active (true/false)
        #    * lastupdate (yyyy-mm-dd)
        self.con.execute('''CREATE TABLE IF NOT EXISTS runner(
                         runnername TEXT,
                         dateofbirth,
                         runnerid INTEGER PRIMARY KEY ASC,
                         gender TEXT,
                         hometown TEXT,
                         active INT,
                         lastupdate TEXT
                         )''')

        #* race
        #    * racename
        #    * date (yyyy-mm-dd)
        #    * raceid (incr for join)
        #    * starttime
        #    * distance (miles)
        self.con.execute('''CREATE TABLE IF NOT EXISTS race (
                         racename TEXT,
                         racedate,
                         raceid INTEGER PRIMARY KEY ASC,
                         racestarttime,
                         racedistance FLOAT
                         )''')
        
        #* raceresult
        #    * runner/id
        #    * race/id
        #    * resulttime (seconds)
        #    * overallplace
        #    * genderplace
        #    * divisionplace
        #    * lastupdate (yyyy-mm-dd hh:mm:ss)
        self.con.execute('''CREATE TABLE IF NOT EXISTS raceresult (
                         runnerid INTEGER,
                         raceid INTEGER,
                         resulttime FLOAT,
                         overallplace INT,
                         genderplace INT,
                         divisionplace INT,
                         lastupdate TEXT
                         )''')

    #----------------------------------------------------------------------
    def __del__(self):
    #----------------------------------------------------------------------
        '''
        commit last updates
        '''
        
        self.con.close()
        
    #----------------------------------------------------------------------
    def addrunner(self,name,dateofbirth,gender,hometown):
    #----------------------------------------------------------------------
        '''
        add a runner to runner table, if runner doesn't already exist
        
        :param name: runner's name
        :param dateofbirth: yyyy-mm-dd date of birth
        :param gender: M|F
        :param hometown: city, ST
        '''
        
        changesmade = False
        
        # some argument error checking
        if str(gender).upper() not in ['M','F']:
            raise parameterError, 'invalid gender {0}'.format(gender)
        gender = gender.upper()
        
        try:
            if dateofbirth:
                dobtest = t.asc2dt(dateofbirth)
            # special handling for dateofbirth = None
            else:
                dateofbirth = ''
        except ValueError:
            raise parameterError, 'invalid dateofbirth {0}'.format(dateofbirth)
        
        params = (name,dateofbirth)
        theserows = self.con.execute('SELECT * FROM runner WHERE runnername=? AND dateofbirth=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in runner for {0} {1}'.format(name,dateofbirth)
        
        # found a row, update if something has changed
        if len(rows) == 1:
            if gender.upper() != rows[0]['gender'] or hometown != rows[0]['hometown']:
                params = (gender.upper(),hometown,1,t.epoch2asc(time.time()),name,dateofbirth)
                self.con.execute('UPDATE runner SET (gender=?,hometown=?,active=?,lastupdate=?) WHERE runnername=? AND dateofbirth=?',params)
                changesmade = True
                
        # no rows found, just insert the entry
        else:
            params = (name,dateofbirth,gender.upper(),hometown,1,t.epoch2asc(time.time()))
            self.con.execute('INSERT INTO runner (runnername,dateofbirth,gender,hometown,active,lastupdate) VALUES (?,?,?,?,?,?)',params)
            changesmade = True
        
        # tell caller if any changes were made
        return changesmade
    
    #----------------------------------------------------------------------
    def listrunners(self):
    #----------------------------------------------------------------------
        '''
        return a list of all runners in the db, (name,dateofbirth)
        
        :rtype: [(runnername,dateofbirth),... ]
        '''
        
        runners = []
        for row in self.con.execute('SELECT runnername, dateofbirth FROM runner'):
            runners.append((row['runnername'],row['dateofbirth']))
            
        return runners
    
    #----------------------------------------------------------------------
    def getrunnerid(self,name,dateofbirth):
    #----------------------------------------------------------------------
        '''
        return the id for a runner, or raise exception if not available
        
        :param name: runner's name
        :param dateofbirth: yyyy-mm-dd date of birth
        '''

        params = (name,dateofbirth)
        theserows = self.con.execute('SELECT * FROM runner WHERE runnername=? AND dateofbirth=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in runner for {0} {1}'.format(name,dateofbirth)
        
        if len(rows) == 0:
            raise parameterError, 'could not find runner {0} {1}'.format(name,dateofbirth)
        
        return rows[0]['runnerid']
        
    #----------------------------------------------------------------------
    def addrace(self,name,date,starttime,distance):
    #----------------------------------------------------------------------
        '''
        add or update a race in race table
        
        :param name: race name
        :param date: yyyy-mm-dd date of race
        :param starttime: hh:mm time of race
        :param distance: in miles
        '''
        
        changesmade = False
        
        # some argument error checking
        # allow invalid race dates -- these should be corrected before race results are put in db
        #try:
        #    if date:
        #        dobtest = t.asc2dt(date)
        #    # special handling for dateofbirth = None
        #    else:
        #        raise ValueError, 'date of race is required, given {0}'.format(date)
        #except ValueError:
        #    raise parameterError, 'invalid race date {0}'.format(date)
        
        params = (name,date)
        theserows = self.con.execute('SELECT * FROM race WHERE racename=? AND racedate=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in race for {0} {1}'.format(name,date)
        
        # found a row, update if something has changed
        if len(rows) == 1:
            if starttime != rows[0]['racestarttime'] or distance != rows[0]['racedistance']:
                params = (starttime,distance,name,dateofbirth)
                self.con.execute('UPDATE race SET (racestarttime=?,racedistance=?) WHERE racename=? AND racedate=?',params)
                changesmade = True
                
        # no rows found, just insert the entry
        else:
            params = (name,date,starttime,distance)
            self.con.execute('INSERT INTO race (racename,racedate,racestarttime,racedistance) VALUES (?,?,?,?)',params)
            changesmade = True
        
        # tell caller if any changes were made
        return changesmade
    
    #----------------------------------------------------------------------
    def listraces(self):
    #----------------------------------------------------------------------
        '''
        return a list of all races in the db, (name,date,distance)
        
        :rtype: [(name,date,starttime,distance),... ]
        '''
        
        races = []
        for row in self.con.execute('SELECT racename, racedate, racestarttime, racedistance FROM race'):
            races.append((row['racename'],row['racedate'],row['racestarttime'],row['racedistance']))
            
        return races
    
    #----------------------------------------------------------------------
    def getraceid(self,name,date):
    #----------------------------------------------------------------------
        '''
        return the id for a race, or raise exception if not available
        
        :param name: race name
        :param date: yyyy-mm-dd date of race
        '''

        params = (name,date)
        theserows = self.con.execute('SELECT * FROM race WHERE racename=? AND racedate=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in race for {0} {1}'.format(name,date)
        
        if len(rows) == 0:
            raise parameterError, 'could not find race {0} {1}'.format(name,date)
        
        return rows[0]['raceid']
        
    #----------------------------------------------------------------------
    def commit(self):
    #----------------------------------------------------------------------
        '''
        commit last updates
        '''
        
        self.con.commit()
        
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    '''
    test code for this module
    '''
    parser = argparse.ArgumentParser(version='{0} {1}'.format('running',version.__version__))
    parser.add_argument('-m','--memberfile',help='file with member information',default=None)
    parser.add_argument('-r','--racefile',help='file with race information',default=None)
    args = parser.parse_args()
    
    OUT = open('racedbtest.txt','w')
    testdb = RaceDB('testdb.db')

    if args.memberfile:
        members = clubmember.ClubMember(args.memberfile)
        
        for name in members.members:
            thesemembers = members.members[name]
            for thismember in thesemembers:
                added = testdb.addrunner(thismember['name'],thismember['dob'],thismember['gender'],thismember['hometown'])
                if added:
                    OUT.write('added runner {0}\n'.format(thismember))
                else:
                    OUT.write('did not add runner {0}\n'.format(thismember))
                
        testdb.commit()
        
        runners = testdb.listrunners()
        for runner in runners:
            name,dateofbirth = runner
            runnerid = testdb.getrunnerid(name,dateofbirth)
            OUT.write('found id={0}, runner={1}\n'.format(runnerid,runner))
    
    if args.racefile:
        races = racefile.RaceFile(args.racefile)
        
        for race in races.races:
            added = testdb.addrace(race['race'],race['date'],race['time'],race['distance'])
            if added:
                OUT.write('added race {0}\n'.format(race))
            else:
                OUT.write ('did not add race {0}\n'.format(race))
        
        testdb.commit()
        
        dbraces = testdb.listraces()
        for race in dbraces:
            name,date,starttime,distance = race
            raceid = testdb.getraceid(name,date)
            OUT.write('found id={0}, race={1}\n'.format(raceid,race))
            
    OUT.close()
    
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()