#!/usr/bin/python
###########################################################################################
# agegrade - calculate age grade statistics
#
#	Date		Author		Reason
#	----		------		------
#       02/17/13        Lou King        Create
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
agegrade - calculate age grade statistics
===================================================
'''

# standard
import pdb
import argparse
import csv
import pickle
import os.path
import shutil

# pypi

# github

# home grown
import version
from running import *
from loutilities import csvwt

# exceptions for this module.  See __init__.py for package exceptions
class missingConfiguration(Exception): pass

#----------------------------------------------------------------------
def getagtable(agegradewb):
#----------------------------------------------------------------------
    '''
    in return data structure:
    
    dist is distance in meters (approx)
    openstd is number of seconds for open standard for this distance
    age is age in years (integer)
    factor is age grade factor
    
    :param agegradewb: excel workbook containing age grade factors
    
    :rtype: {'F':{dist:{'OC':openstd,age:factor,age:factor,...},...},'M':{dist:{'OC':openstd,age:factor,age:factor,...},...}}
    '''
    
    agegradedata = {}
    
    # convert the workbook to csv
    c = csvwt.Xls2Csv(agegradewb)
    gen2sheet = {'F':'Women','M':'Men'}
    sheets = c.getfiles()
    
    for gen in ['F','M']:
        SHEET = open(sheets[gen2sheet[gen]],'rb')
        sheet = csv.DictReader(SHEET)
        
        # convert fields to keys - e.g., '5.0' -> 5, skipping non-numeric keys
        f2age = {}
        for f in sheet.fieldnames:
            try:
                k = int(float(f))
                f2age[f] = k
            except ValueError:
                pass
        
        # create gender
        agegradedata[gen] = {}
        
        # add each row to data structure, but skip non-running events
        for r in sheet:
            if r['dist(km)'] == '0.0': continue
            
            dist = int(round(float(r['dist(km)'])*1000))
            openstd = float(r['OC'])
            
            # create dist
            agegradedata[gen][dist] = {'OC':openstd}
            
            # add each age factor
            for f in sheet.fieldnames:
                if f in f2age:
                    age = f2age[f]
                    agegradedata[gen][dist][age] = float(r[f])
            
            
        SHEET.close()
    
    del c
    return agegradedata

########################################################################
class AgeGrade():
########################################################################
    '''
    AgeGrade object 
    
    agegradewb is in format per http://www.howardgrubb.co.uk/athletics/wmalookup06.html
    if agegradewb parameter is missing, previous configuration is used
    configuration is created through command line: agegrade.py [-a agworkbook | -c agconfigfile]
    
    :param agegradewb: excel workbook containing age grade factors
    '''
    #----------------------------------------------------------------------
    def __init__(self,agegradewb=None):
    #----------------------------------------------------------------------
        # use age grade workbook if specified
        if agegradewb:
            self.agegradedata = getagtable(agegradewb)
        
        # otherwise, pick up the data from the configuration
        else:
            pathn = os.path.join(CONFIGDIR,'agegrade.cfg')
            if not os.path.exists(pathn):
                raise missingConfiguration, 'agegrade configuration not found, run agegrade.py to configure'
            
            C = open(pathn)
            self.agegradedata = pickle.load(C)
            C.close()
            
    #----------------------------------------------------------------------
    def agegrade(self,age,gen,distmiles,time):
    #----------------------------------------------------------------------
        '''
        returns age grade statistics for the indicated age, gender, distance, result time
        
        :param age: integer age.  If float is supplied, integer portion is used (no interpolation of fractional age)
        :param gen: gender - M or F
        :param distmiles: distance (miles)
        :param time: time for distance (seconds)
        
        :rtype: (age performance percentage, age graded result) - percentage is between 0 and 100, result is in seconds
        '''
        
        # check for some input errors
        if gen not in ['F','M']:
            raise parameterError, 'gen must be M or F'
        if age not in range(5,100):
            raise parameterError, 'age must be integer between 5 and 99 inclusive'

        # number of meters in a mile -- close enough for this data set
        mpermile = 1609
        
        # some known conversions
        cdist = {26.2:42200,13.1:21100}
        
        # determine distance in meters
        if distmiles in cdist:
            distmeters = cdist[distmiles]
        else:
            distmeters = distmiles*mpermile
        
        # check distance within range
        distlist = self.agegradedata[gen].keys()
        minmeters = min(distlist)
        maxmeters = max(distlist)
        if distmeters < minmeters or distmeters > maxmeters:
            raise parameterError, 'distmiles must be between {0:f0.3} and {1:f0.1}'.format(minmeters/mpermile,maxmeters/minpermile)

        # find surrounding Xi points, and corresponding Fi, OCi points
        distlist.sort()
        lastd = distlist[0]
        for i in range(1,len(distlist)):
            if distmeters <= distlist[i]:
                x0 = lastd
                x1 = distlist[i]
                f0 = self.agegradedata[gen][x0][age]
                f1 = self.agegradedata[gen][x1][age]
                oc0 = self.agegradedata[gen][x0]['OC']
                oc1 = self.agegradedata[gen][x1]['OC']
                break
            lastd = distlist[i]
            
        # interpolate factor and openstd (see http://en.wikipedia.org/wiki/Linear_interpolation)
        factor = f0 + (f1-f0)*((distmeters-x0)/(x1-x0))
        openstd = oc0 + (oc1-oc0)*((distmeters-x0)/(x1-x0))
        
        # return age grade statistics
        agpercentage = 100*(openstd/factor)/time
        agresult = time*factor
        return agpercentage,agresult

#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    Update configuration for agegrade.py.  One of --agworkbook or --agconfigfile must be used,
    but not both.
    
    --agworkbook creates an agconfigfile and puts it in the configuration directory.
    --agconfigfile simply places the indicated file into the configuration directory.
    '''
    
    parser = argparse.ArgumentParser(description=descr,formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('running',version.__version__))
    parser.add_argument('-a','--agworkbook',help='filename of age grade workbook.', default=None)
    parser.add_argument('-c','--agconfigfile',help='filename of age grade config file',default=None)
    args = parser.parse_args()

    # must have one of the options
    if not args.agworkbook and not args.agconfigfile:
        print 'one of --agworkbook or --agconfigfile must be specified'
        return
        
    # can't have both of the options
    if args.agworkbook and args.agconfigfile:
        print 'only one of --agworkbook or --agconfigfile should be specified'
        return

    # configuration file will be here    
    pathn = os.path.join(CONFIGDIR,'agegrade.cfg')

    # workbook specified
    if args.agworkbook:
        agegradedata = getagtable(args.agworkbook)
        C = open(pathn,'w')
        pickle.dump(agegradedata,C)
        C.close()
    
    # config file specified
    else:
        # make sure this is a pickle file
        try:
            C = open(args.agconfigfile)
            test = pickle.load(C)
            C.close()
        except IOError:
            print '{0}: not found'.format(args.agconfigfile)
            return
        except KeyError:
            print '{0}: invalid format'.format(args.agconfigfile)
            return
            
        shutil.copyfile(args.agconfigfile,pathn)
        
    print 'updated {0}'.format(pathn)
    
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()