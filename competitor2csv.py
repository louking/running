#!/usr/bin/python
# ###############################################################################
# getmembers-competitor - get members who ran competitor race (e.g., Rock 'n' Roll Marathon)
#
# Author: L King
#
# REVISION HISTORY:
#   03/17/15    L King      Create
# ###############################################################################
'''
getmembers-competitor - get members who ran competitor race (e.g., Rock 'n' Roll Marathon)
==============================================================================================

Usage::

    TBA
'''

# standard libraries
import csv
import pdb
import argparse
from string import maketrans
from collections import OrderedDict

# home grown libraries
from . import version
from .competitor import Competitor

# convert competitorResult to expected format for runningclub.RaceResults
competitor2raceresult = OrderedDict([
    ('oaplace',     'place'),
    ('name',        'name'),
    ('genplace',    'gender place',),
    ('divplace',    'division place',),
    ('age',         'age'),
    ('gender',      'gender'),
    ('hometown',    'hometown'),
    ('racetime',    'time'),
    ('racedate',    'race date'),
    ('raceloc',     'race location'),
    ('racename',    'race name'),
    ('distmiles',   'miles'),
    ('distkm',      'km')
])

#-------------------------------------------------------------------------------
def getcompetitorrace(outfile,eventid,eventinstanceid,singleeventid,limit=None):
#-------------------------------------------------------------------------------
    '''
    create file for competitor race based on eventid, eventinstanceid, singleeventid
    
    :param outfile: base filename for output file, event and distance are appended to name
    :param eventid: event id from running.competitor.com
    :param eventinstanceid: event instance id from running.competitor.com
    :param singleeventid: single event id from running.competitor.com
    :param limit: limit number of records (for testing only)
    
    :rtype: name of file which was created
    '''

    cc = Competitor()
    cc.setraceyear(eventid,eventinstanceid,singleeventid)
    results = cc.getresults(limit)
    
    # build filename using racename and distance
    # racename needs to be str() else translate gets ValueError because transtab is not Unicode mapping
    racename = str(results[0].racename) 
    dist = '{:.1f}'.format(results[0].distmiles)
    if dist == 13.1:
        dist = 'halfmarathon'
    elif dist == 26.2:
        dist = 'marathon'
    else:
        dist = '{}miles'.format(dist)
    # change all ' ' to '-' and quotes to 'x' in racename
    transtab = maketrans(''' '"''','-xx')   
    tracename = racename.translate(transtab)
    outfilename = '{}-{}-{}.csv'.format(outfile,tracename,dist)
    
    # open output results file
    RS_ = open(outfilename,'wb')
    RS = csv.DictWriter(RS_,list(competitor2raceresult.values()))
    RS.writeheader()
    
    # write the results to the file
    for result in results:
        filerow = {}
        for attr in result.attrs:
            filerow[competitor2raceresult[attr]] = getattr(result,attr)
        RS.writerow(filerow)

    # close file
    RS_.close()
    
    # let caller know the name of the file which was built
    return outfilename
    
#-------------------------------------------------------------------------------
def getcompetitor(outfile):
#-------------------------------------------------------------------------------
    '''
    put competitor results into csv file per race
    
    :param outfile: base of output file name for competitor files
    
    :rtype: list containing names of files which were created
    '''
    
    # build list of files which are output
    resultfiles = []
    
    # build half marathon file
    thisfile = getcompetitorrace(outfile,54,227,797)
    resultfiles.append(thisfile)

    # build marathon file
    thisfile = getcompetitorrace(outfile,54,227,791)
    resultfiles.append(thisfile)
    
    # let caller know what files were built
    return resultfiles

#-------------------------------------------------------------------------------
def main():
#-------------------------------------------------------------------------------

    parser = argparse.ArgumentParser(version='running {0}'.format(version.__version__))
    parser.add_argument('outfile', help="base name for output file")
    parser.add_argument('-e','--eventid', help="eventid for competitor.com",type=int,default=None)
    parser.add_argument('-i','--instanceid', help="event instance for competitor.com (which year)",type=int,default=None)
    parser.add_argument('-s','--singleeventid', help="single eventid for competitor.com (which distance)",type=int,default=None)
    parser.add_argument('-l','--limit', help="limit number of records (for testing only)",type=int,default=None)
    args = parser.parse_args()
    
    # get arguments
    outfile = args.outfile
    eventid = args.eventid
    instanceid = args.instanceid
    singleeventid = args.singleeventid
    limit = args.limit
    
    # only collect information from competitor.com if output file is defined
    resultfile = getcompetitorrace(outfile,eventid,instanceid,singleeventid,limit)
    print(('generated {}'.format(resultfile)))
        
# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

