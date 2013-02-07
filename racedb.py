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
import time

# pypi

# github

# other
import sqlalchemy   # see http://www.sqlalchemy.org/ written with 0.8.0b2
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()   # create sqlalchemy Base class
from sqlalchemy import Column, Integer, Float, Boolean, String, Sequence, UniqueConstraint, ForeignKey
from sqlalchemy.orm import sessionmaker, object_mapper, relationship, backref
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
    engine = sqlalchemy.create_engine('{0}'.format(dbfilename))
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

    if updated:
        session.flush()
        
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
    results = relationship("RaceResult", backref='runner', cascade="all, delete, delete-orphan")

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
    results = relationship("RaceResult", backref='race', cascade="all, delete, delete-orphan")
    series = relationship("RaceSeries", backref='race', cascade="all, delete, delete-orphan")

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
    calcoverall = Column(Boolean)
    calcdivisions = Column(Boolean)
    calcagegrade = Column(Boolean)
    divisions = relationship("Divisions", backref='series', cascade="all, delete, delete-orphan")
    races = relationship("RaceSeries", backref='series', cascade="all, delete, delete-orphan")

    #----------------------------------------------------------------------
    def __init__(self, name, membersonly, overall, divisions, agegrade):
    #----------------------------------------------------------------------
        
        self.name = name
        self.membersonly = membersonly
        self.calcoverall = overall
        self.calcdivisions = divisions
        self.calcagegrade = agegrade

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<Series('%s','%s','%s','%s','%s')>" % (self.name, self.membersonly, self.calcoverall, self.calcdivisions, self.calcagegrade)
    
########################################################################
class RaceSeries(Base):
########################################################################
    '''
    * raceseries
        * race/id
        * series/id
   
    :param raceid: race.id
    :param seriesid: series.id
    '''
    __tablename__ = 'raceseries'
    id = Column(Integer, Sequence('raceseries_id_seq'), primary_key=True)
    raceid = Column(Integer, ForeignKey('race.id'))
    seriesid = Column(Integer, ForeignKey('series.id'))
    __table_args__ = (UniqueConstraint('raceid', 'seriesid'),)

    #----------------------------------------------------------------------
    def __init__(self, raceid, seriesid):
    #----------------------------------------------------------------------
        
        self.raceid = raceid
        self.seriesid = seriesid

    #----------------------------------------------------------------------
    def __repr__(self):
    #----------------------------------------------------------------------
        return "<RaceSeries(race='%s',series='%s')>" % (self.raceid, self.seriesid)
    
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
    divisionhigh = Column(Integer)

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
        
        for name in members.getmembers():
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
        
    if args.racefile:
        races = racefile.RaceFile(args.racefile)
        
        for race in races.getraces():
            newrace = Race(race['race'],race['year'],race['date'],race['time'],race['distance'])
            added = insert_or_update(session,Race,newrace,skipcolumns=['id'],name=newrace.name,year=newrace.year)
            if added:
                OUT.write('added or updated race {0}\n'.format(race))
            else:
                OUT.write ('no updates necessary {0}\n'.format(race))
        
        session.commit()
        
        dbraces = session.query(Race).all()
        for race in dbraces:
            OUT.write('found id={0}, race={1}\n'.format(race.id,race))
            
        #for series in races.series.keys():
        #    added = testdb.addseriesattributes(series,races.series[series])
        #    if added:
        #        OUT.write('added seriesattribute for series {0}, {1}\n'.format(series,races.series[series]))
        #    else:
        #        OUT.write('did not add seriesattribute for series {0}, {1}\n'.format(series,races.series[series]))

    session.close()
    OUT.close()
        
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()