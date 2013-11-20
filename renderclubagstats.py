#!/usr/bin/python
###########################################################################################
#   renderclubagstats - render age grade statistics for a club
#
#   Date        Author      Reason
#   ----        ------      ------
#   11/17/13    Lou King    Create
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
renderclubagstats - render age grade statistics for a club
===================================================================

Render club age grade statistics, based on collected athlinks statistics (collectathlinksresults),
club data in runningahead (analyzeagegrade) and club results (TODO: club database)

Usage::
                        
'''

# standard
import pdb
import argparse
import tempfile
import csv

# pypi

# github

# other

# home grown
from loutilities import timeu
import analyzeagegrade
import athlinksresults
import version

class invalidParameter(Exception): pass
METERSPERMILE = 1609.344

#----------------------------------------------------------------------
def render(athlinksfile,outfile,begindate,enddate):
#----------------------------------------------------------------------
    '''
    Render club age grade statistics, based on collected athlinks statistics (collectathlinksresults),
    club data in runningahead (analyzeagegrade) and club results (TODO: club database)
    
    :param athlinksfile: file with athlinks results, output from collectathlinksresults
    :param outfile: output file name template, like '{who}-ag-analysis-{date}-{time}.png'
    :param begindate: render races between begindate and enddate, yyyy-mm-dd
    :param enddate: render races between begindate and enddate, yyyy-mm-dd
    '''
    # for now error if no athlinks file, maybe future lack of athlinks file is ok
    if not athlinksfile: raise invalidParameter, 'athlinks file required'

    # create object for age grade rendering
    aag = analyzeagegrade.AnalyzeAgeGrade()
    
    # set output file rendering
    if outfile:
        aag.set_renderfname(outfile)
        
    # set up rendering parameters
    # TODO: set xlim based on begindate, enddate
    # not sure quite how to do this at time of writing this
    #aag.set_xlim(begindate,enddate)    # have to use matplotlib function date2num?
    aag.set_ylim(25,100)
    aag.set_colormap([200,100*METERSPERMILE])
    
    # reading athlinksfile
    athlf = athlinksresults.AthlinksResultFile(athlinksfile)
    athlf.open()
    
    # read records from athlinksfile
    # records are assumed to be sorted by individual
    # gather each individual's result statistics, then render the result statistics for that individual
    result = athlf.next()
    aag.set_runner(result.name,result.gender,result.dob)
    thisname = result.name
    while True:
        # collect this result
        timesecs = timeu.timesecs(result.resulttime)
        if timesecs > 0:
            aag.add_stat(result.racedate,result.distkm*1000,timesecs)
        
        # if we've completed the last runner's result collection,
        # render the results, and set up for the next runner
        result = athlf.next()
        if result is None or result.name != thisname:
            aag.crunch()    # calculate age grade for each result
            aag.render()    # send viz to file
            aag.clear()     # set up for next runner

            # are we done?
            if result is None:
                break
            
            # not done, but we have a new runner
            aag.set_runner(result.name,result.gender,result.dob)
            thisname = result.name
            
        
    
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    render race results from athlinks, 
    
    searchfile must have at least the following headings:
    
        * GivenName - first name
        * FamilyName - last name
        * Gender - Male or Female (or M or F)
        * DOB - date of birth in yyyy-mm-dd format
        * City - city of residence [optional]
        * State - state of residence [optional]
    '''
    
    parser = argparse.ArgumentParser(description=descr,formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('running',version.__version__))
    parser.add_argument('-a','--athlinksfile', help="file with athlinks results, output from collectathlinksresults",default=None)
    parser.add_argument('-o','--outfile', help="output file name template, like '{who}-ag-analysis-{date}-{time}.png', default=%(default)s",default='{who}-ag-analysis-{date}.png')
    parser.add_argument('-b','--begindate', help="render races between begindate and enddate, yyyy-mm-dd",default=None)
    parser.add_argument('-e','--enddate', help="render races between begindate and enddate, yyyy-mm-dd",default=None)
    args = parser.parse_args()

    athlinksfile = args.athlinksfile
    outfile = args.outfile

    argtime = timeu.asctime('%Y-%m-%d')
    if args.begindate:
        begindate = argtime.asc2epoch(args.begindate)
    else:
        begindate = argtime.asc2epoch('1970-01-01')
    if args.enddate:
        enddate = argtime.asc2epoch(args.enddate)
    else:
        enddate = argtime.asc2epoch('2030-12-31')
        
    # render all the data
    render(athlinksfile,outfile,begindate,enddate)
        
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()