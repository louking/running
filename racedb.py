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

racedb has the following tables.  See classes of same name (with camelcase) for definitions.

    * runner
    * race
    * raceresult
    * series
    * divisions
       
'''

# standard
import pdb
import argparse
import sqlite3
import time

# pypi

# github

# other
import sqlalchemy   # see http://www.sqlalchemy.org/ written with 0.8.0b2
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()   # create sqlalchemy Base class
from sqlalchemy import Column, Integer, Float, Boolean, String, Sequence, UniqueConstraint, ForeignKey
from sqlalchemy.orm import sessionmaker, object_mapper
Session = sessionmaker()    # create sqalchemy Session class

# home grown
from running import *
import version
from loutilities import timeu
import clubmember,racefile

t = timeu.asctime('%Y-%m-%d')

#----------------------------------------------------------------------
def setracedb(dbfilename):
#----------------------------------------------------------------------
    '''
    initialize race database
    
    :params dbfilename: filename for race database
    '''
    # set up connection to db -- assume sqlite3 for now
    engine = sqlalchemy.create_engine('sqlite:///{0}'.format(dbfilename))
    Base.metadata.create_all(engine)
    Session.configure(bind=engine)

#----------------------------------------------------------------------
def insert_or_update(session, model, newinstance, skipcolumns=[], **kwargs):
#----------------------------------------------------------------------
    '''
    insert a new element or update an existing on based on kwargs query
    
    :param session: session within which update occurs
    :param model: table model
    :param newinstance: instance of table model which is to become representation in the db
    :param skipcolumns: list of column names to skip checking for any changes
    :param kwargs: query criteria
    '''

    updated = False

    instances = session.query(model).filter_by(**kwargs).all()

    # weirdness -- how'd this happen?
    if len(instances) > 1:
        raise dbConsistencyError, 'found multiple rows in {0} for {1}'.format(model,kwargs)
    
    # found a matching object, may need to update some of its attributes
    if len(instances) == 1:
        instance = instances[0]
        for col in object_mapper(newinstance).columns:
            # skip indicated keys
            if col.key in skipcolumns: continue
            
            # if any columns are different, update those columns
            # and return to the caller that it's been updated
            if getattr(instance,col.key) != getattr(newinstance,col.key):
                setattr(instance,col.key,getattr(newinstance,col.key))
                updated = True
    
    # new object, just add to database
    else:
        session.add(newinstance)
        updated = True

    return updated

########################################################################
class Runner(Base):
########################################################################
    '''
    * runner
        * id (incr for join)
        * name
        * dateofbirth (yyyy-mm-dd)
        * gender (M/F)
        * hometown (city, ST)
        * active (true/false)
        * lastupdate (yyyy-mm-dd)

    :param name: runner's name
    :param dateofbirth: yyyy-mm-dd date of birth
    :param gender: M | F
    :param hometown: runner's home town
    '''
    __tablename__ = 'runner'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(50))
    dateofbirth = Column(String(10))
    gender = Column(String(1))
    hometown = Column(String(50))
    active = Column(Boolean)
    #lastupdate = Column(String(10))
    __table_args__ = (UniqueConstraint('name', 'dateofbirth'),)

    #----------------------------------------------------------------------
    def __init__(self, name, dateofbirth, gender, hometown):
    #----------------------------------------------------------------------
        try:
            if dateofbirth:
                dobtest = t.asc2dt(dateofbirth)
            # special handling for dateofbirth = None
            else:
                dateofbirth = ''
        except ValueError:
            raise parameterError, 'invalid dateofbirth {0}'.format(dateofbirth)
        
        self.name = name
        self.dateofbirth = dateofbirth
        self.gender = gender
        self.hometown = hometown
        self.active = True
        #self.lastupdate = t.epoch2asc(time.time())

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Runner('%s','%s','%s','%s','%s')>" % (self.name, self.dateofbirth, self.gender, self.hometown, self.active)
    
########################################################################
class Race(Base):
########################################################################
    '''
    * race
        * id (incr for join)
        * name
        * year
        * date (yyyy-mm-dd)
        * starttime
        * distance (miles)
    
    :param name: race name
    :param year: year of race
    :param date: yyyy-mm-dd date of race
    :param starttime: hh:mm starr of race
    :param distance: race distance in miles
    '''
    __tablename__ = 'race'
    id = Column(Integer, Sequence('race_id_seq'), primary_key=True)
    name = Column(String(50))
    year = Column(Integer)
    date = Column(String(10))
    starttime = Column(String(5))
    distance = Column(Float)
    __table_args__ = (UniqueConstraint('name', 'year'),)

    #----------------------------------------------------------------------
    def __init__(self, name, year, date, starttime, distance):
    #----------------------------------------------------------------------

        self.name = name
        self.year = year
        self.date = date
        self.starttime = starttime
        self.distance = distance

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Race('%s','%s','%s','%s','%s')>" % (self.name, self.year, self.date, self.starttime, self.distance)
    
########################################################################
class RaceResult(Base):
########################################################################
    '''
    * raceresult
        * runner/id
        * race/id
        * time (seconds)
        * overallplace
        * genderplace
        * divisionplace
    
    :param runnerid: runner.id
    :param raceid: race.id
    :param time: time in seconds
    :param overallplace: runner's place in race overall
    :param genderplace: runner's place in race within gender
    :param divisionplace: runner's place in race within division (see division table) - default None
    :param agtime: age grade time in seconds - default None
    '''
    __tablename__ = 'raceresult'
    id = Column(Integer, Sequence('raceresult_id_seq'), primary_key=True)
    runnerid = Column(Integer, ForeignKey('runner.id'))
    raceid = Column(Integer, ForeignKey('race.id'))
    time = Column(Float)
    agtime = Column(Float)
    overallplace = Column(Integer)
    genderplace = Column(Integer)
    divisionplace = Column(Integer)
    __table_args__ = (UniqueConstraint('runnerid', 'raceid'),)

    #----------------------------------------------------------------------
    def __init__(self, runnerid, raceid, time, overallplace, genderplace, divisionplace=None, agtime=None):
    #----------------------------------------------------------------------
        
        self.runnerid = runnerid
        self.raceid = raceid
        self.time = time
        self.overallplace = overallplace
        self.genderplace = genderplace
        self.divisionplace = divisionplace
        self.agtime = agtime

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<RaceResult('%s','%s','%s','%s','%s','%s','%s')>" % (self.runnerid, self.raceid, self.time, self.overallplace, self.genderplace, self.divisionplace, self.agtime)
    
########################################################################
class Series(Base):
########################################################################
    '''
    * series (attributes)
        * name
        * membersonly
        * overall
        * divisions
        * agegrade

    :param name: series name
    :param membersonly: True if series applies to club members only
    :param overall: True if overall results are to be calculated
    :param divisions: True if division results are to be calculated
    :param agegrade: True if age graded results are to be calculated
    '''
    __tablename__ = 'series'
    id = Column(Integer, Sequence('series_id_seq'), primary_key=True)
    name = Column(String(50),unique=True)
    membersonly = Column(Boolean)
    overall = Column(Boolean)
    divisions = Column(Boolean)
    agegrade = Column(Boolean)

    #----------------------------------------------------------------------
    def __init__(self, name, membersonly, overall, divisions, agegrade):
    #----------------------------------------------------------------------
        
        self.name = name
        self.membersonly = membersonly
        self.overall = overall
        self.divisions = divisions
        self.agegrade = agegrade

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Series('%s','%s','%s','%s','%s')>" % (self.name, self.membersonly, self.overall, self.divisions, self.agegrade)
    
########################################################################
class Divisions(Base):
########################################################################
    '''
    * divisions
        * seriesid
        * divisionlow - age
        * divisionhigh - age
    
    :param seriesid: series.id
    :param divisionlow: low age in division
    :param divisionhigh: high age in division
    '''
    __tablename__ = 'divisions'
    id = Column(Integer, Sequence('raceresult_id_seq'), primary_key=True)
    seriesid = Column(Integer, ForeignKey('series.id'))
    divisionlow = Column(Integer)
    divisionlhigh = Column(Integer)

    #----------------------------------------------------------------------
    def __init__(self, seriesid, divisionlow, divisionhigh):
    #----------------------------------------------------------------------
        
        self.seriesid = seriesid
        self.divisionlow = divisionlow
        self.divisionhigh = divisionhigh

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Divisions '%s','%s','%s')>" % (self.seriesid, self.divisionlow, self.divisionhigh)
    
########################################################################
class RaceDBold():     # TODO: remove in favor of SQLAlchemy based classes
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
                         )'''
        )

        #* race
        #    * name
        #    * year (yyyy)
        #    * date (yyyy-mm-dd)
        #    * raceid (incr for join)
        #    * starttime
        #    * distance (miles)
        self.con.execute('''CREATE TABLE IF NOT EXISTS race (
                         name TEXT,
                         year int,
                         date,
                         raceid INTEGER PRIMARY KEY ASC,
                         starttime,
                         distance FLOAT
                         )'''
        )
        
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
                         )'''
        )
        
        #* divisions
        #    * series
        #    * divisionlow - age
        #    * divisionhigh - age
        self.con.execute('''CREATE TABLE IF NOT EXISTS divisions (
                         series TEXT,
                         divisionlow INT,
                         divisionhigh INT
                         )'''
        )

        #* seriesattributes
        #    * series
        #    * flags
        #       see SERFLAGS for flag bit definitions
        self.con.execute('''CREATE TABLE IF NOT EXISTS seriesattributes (
                         series TEXT,
                         flags INTEGER
                         )'''
        )

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
            row = rows[0]
            if gender.upper() != row['gender'] or hometown != row['hometown']:
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
        
        row = rows[0]
        return rows['runnerid']
        
    #----------------------------------------------------------------------
    def addrace(self,name,year,date,starttime,distance):
    #----------------------------------------------------------------------
        '''
        add or update a race in race table
        
        :param name: race name
        :param year: yyyy year of race
        :param date: yyyy-mm-dd date of race
        :param starttime: hh:mm time of race
        :param distance: in miles
        '''
        
        changesmade = False
        
        params = (name,year)
        theserows = self.con.execute('SELECT * FROM race WHERE name=? AND year=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in race for {0} {1}'.format(name,year)
        
        # found a row, update if something has changed
        if len(rows) == 1:
            row = rows[0]
            if starttime != row['starttime'] or distance != row['distance']:
                params = (starttime,date,distance,name,year)
                self.con.execute('UPDATE race SET (starttime=?,date=?,distance=?) WHERE name=? AND year=?',params)
                changesmade = True
                
        # no rows found, just insert the entry
        else:
            params = (name,year,date,starttime,distance)
            self.con.execute('INSERT INTO race (name,year,date,starttime,distance) VALUES (?,?,?,?,?)',params)
            changesmade = True
        
        # tell caller if any changes were made
        return changesmade
    
    #----------------------------------------------------------------------
    def listraces(self):
    #----------------------------------------------------------------------
        '''
        return a list of all races in the db, (name,date,distance)
        
        :rtype: [(name,year,date,starttime,distance),... ]
        '''
        
        races = []
        for row in self.con.execute('SELECT name, year, date, starttime, distance FROM race'):
            races.append((row['name'],row['year'],row['date'],row['starttime'],row['distance']))
            
        return races
    
    #----------------------------------------------------------------------
    def getraceid(self,name,year):
    #----------------------------------------------------------------------
        '''
        return the id for a race, or raise exception if not available
        
        :param name: race name
        :param year: yyyy year of race
        '''

        params = (name,year)
        theserows = self.con.execute('SELECT * FROM race WHERE name=? AND year=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in race for {0} {1}'.format(name,year)
        
        if len(rows) == 0:
            raise parameterError, 'could not find race {0} {1}'.format(name,year)
        
        row = rows[0]
        return row['raceid']
        
    #----------------------------------------------------------------------
    def getdivisions(self,series):
    #----------------------------------------------------------------------
        '''
        return a list of all divisions, based on series
        
        :rtype: [(divisionlow,divisionhigh),... ] - age tuples
        '''
        
        divisions = []
        params = (series,)
        for row in self.con.execute('SELECT divisionlow, divisionhigh FROM divisions WHERE series=?',params):
            divisions.append((row['divisionlow'],row['divisionhigh']))
            
        return divisions
    
    #----------------------------------------------------------------------
    def addresult(self,runnerid,raceid,resulttime,overallplace,genderplace,divisionplace=None,agtime=None):
    #----------------------------------------------------------------------
        '''
        add or update the race result for a given runner/race
        
        :param runnerid: runnerid from runner table
        :param raceid: raceid from race table
        :param resulttime: time in seconds, float
        :param overallplace: place for this result overall for race
        :param genderplace: place for this result within gender for race
        :param divplace: place for this result within division for race
        :param agtime: age graded time in seconds, float
        '''

        changesmade = False
        
        params = (runnerid,raceid)
        theserows = self.con.execute('SELECT * FROM raceresult WHERE reunnerid=? AND raceid=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in raceraceresults for reunnerid={0} raceid={1}'.format(runnerid,raceid)
        
        # found a row, update if something has changed
        if len(rows) == 1:
            row = rows[0]
            if (resulttime != row['resulttime']
                or overallplace != row['overallplace']
                or genderplace != row['genderplace']
                or divplace != row['divplace']
                or agtime != row['agtime']
               ):
                params = (resulttime,overallplace,genderplace,divisionplace,agtime,runnerid,raceid)
                self.con.execute('UPDATE raceresult SET (overallplace=?,genderplace=?,divplace=?,divplace=?) WHERE runnerid=? AND raceid=?',params)
                changesmade = True
                
        # no rows found, just insert the entry
        else:
            params = (runnerid,raceid,resulttime,overallplace,genderplace,divisionplace,agtime)
            self.con.execute('INSERT INTO raceresult (runnerid,raceid,resulttime,overallplace,genderplace,divisionplace,agtime) VALUES (?,?,?,?,?,?,?)',params)
            changesmade = True
        
        # tell caller if any changes were made
        return changesmade
    
    #----------------------------------------------------------------------
    def addseriesattributes(self,series,seriesattr):
    #----------------------------------------------------------------------
        '''
        add or update a seriesattribute in seriesattributes table
        
        :param series: series name
        :param seriesattr: dict with keys same as SERFLAGS, with boolean values
        '''
        
        changesmade = False
        
        params = (series,)
        theserows = self.con.execute('SELECT * FROM seriesattributes WHERE series=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in seriesattributes for {0}'.format(series,year)
        
        # what will new flags be?
        updflags = 0
        for key in SERFLAGS:
            if seriesattr[key]:
                updflags += SERFLAGS[key]

        # found a row, update if any of the flags changed
        if len(rows) == 1:
            row = rows[0]
            flags = row['flags']
            somethingchanged = False
            for key in SERFLAGS:
                if seriesattr[key] != ((flags & SERFLAGS[key]) != 0):
                    somethingchanged = True
                    break
            if somethingchanged:
                params = (updflags,series)
                self.con.execute('UPDATE seriesattributes SET (flags=?) WHERE series=?',params)
                changesmade = True
                
        # no rows found, just insert the entry
        else:
            params = (series,updflags)
            self.con.execute('INSERT INTO seriesattributes (series,flags) VALUES (?,?)',params)
            changesmade = True
        
        # tell caller if any changes were made
        return changesmade
    
    #----------------------------------------------------------------------
    def getseriesattributes(self,series):
    #----------------------------------------------------------------------
        '''
        return series attributes, based on series
        
        :rtype: {key:boolean, ...} - see SERFLAGS for keys
        '''
        
        params = (series,)
        theserows = self.con.execute('SELECT * FROM seriesattributes WHERE series=?', params)
        rows = theserows.fetchall()
        if len(rows) > 1:
            # weirdness -- how'd this happen?
            raise dbConsistencyError, 'found multiple rows in seriesattributes for {0}'.format(series,year)
        
        # will remain like this if no rows were found
        seriesattr = {}

        # otherwise, set seriesattr based on flags bits
        if len(rows) == 1:
            row = rows[0]
            flags = row['flags']
            
            for key in SERFLAGS:
                seriesattr[key] = False
                if flags & SERFLAGS[key] != 0:
                    seriesattr[key] = True
                    
        return seriesattr
    
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
    setracedb('testdb.db')
    session = Session()
    
    if args.memberfile:
        members = clubmember.ClubMember(args.memberfile)
        
        for name in members.members:
            thesemembers = members.members[name]
            for thismember in thesemembers:
                runner = Runner(thismember['name'],thismember['dob'],thismember['gender'],thismember['hometown'])
                #if runner.name == 'Doug Batey':
                #    pdb.set_trace()
                added = insert_or_update(session,Runner,runner,skipcolumns=['id'],name=runner.name,dateofbirth=runner.dateofbirth)
                if added:
                    OUT.write('added or updated {0}\n'.format(runner))
                else:
                    OUT.write('no updates necessary {0}\n'.format(runner))
                
        session.commit()
        
        runners = session.query(Runner).all()
        for runner in runners:
            OUT.write('found id={0}, runner={1}\n'.format(runner.id,runner))
        
        session.close()
        
    
    OUT.close()
    
    '''
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
            added = testdb.addrace(race['race'],race['year'],race['date'],race['time'],race['distance'])
            if added:
                OUT.write('added race {0}\n'.format(race))
            else:
                OUT.write ('did not add race {0}\n'.format(race))
        
        testdb.commit()
        
        dbraces = testdb.listraces()
        for race in dbraces:
            name,year,date,starttime,distance = race
            raceid = testdb.getraceid(name,year)
            OUT.write('found id={0}, race={1}\n'.format(raceid,race))
            
        for series in races.series.keys():
            added = testdb.addseriesattributes(series,races.series[series])
            if added:
                OUT.write('added seriesattribute for series {0}, {1}\n'.format(series,races.series[series]))
            else:
                OUT.write('did not add seriesattribute for series {0}, {1}\n'.format(series,races.series[series]))
        
        testdb.commit()

    OUT.close()
    '''    
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()