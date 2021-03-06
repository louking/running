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
club data in runningahead ( (TODO: RA data) analyzeagegrade) and club results (runningclub.exportresults)

Usage::
    TBA
    
'''

# standard
import argparse
import csv
import datetime
import collections
import time

# pypi
from IPython.core.debugger import Tracer; debug_here = Tracer()

# github

# other
import matplotlib.pyplot as plt

# home grown
from loutilities import timeu
from runningclub import render as ren
from running.running import ultrasignupresults, analyzeagegrade, athlinksresults, version, runningaheadresults


class invalidParameter(Exception): pass
METERSPERMILE = 1609.344

# table for driving trend plotting
TRENDLIMITS = collections.OrderedDict([
               ((0,4999.99),         ('<5K','b')),
               ((5000.00,21097.50),  ('5K - <HM','g')),
               ((21097.51,42194.99), ('HM - Mara','orange')),
               ((42195.00,200000),   ('Ultra','r')),
              ])

# priorities for deduplication
# lowest priority value of duplicate entries is kept
PRIO_CLUBRACES = 1
PRIO_ULTRASIGNUP = 2
PRIO_ATHLINKS = 3
PRIO_RUNNINGAHEAD = 4
    
#----------------------------------------------------------------------
def mean(items):
#----------------------------------------------------------------------
    return float(sum(items))/len(items) if len(items) > 0 else float('nan')

#----------------------------------------------------------------------
def initaagrunner(aag,thisname,gender,dob):
#----------------------------------------------------------------------
    '''
    initializaze :class:`AnalyzeAgeGrade` object, if not already initialized
    
    :param aag: :class:`AnalyzeAgeGrade` objects, by runner name
    :param thisname: runner name
    :param gender: M or F
    :param dob: datetime date of birth
    '''
    if thisname not in aag:
        aag[thisname] = analyzeagegrade.AnalyzeAgeGrade()
        aag[thisname].set_runner(thisname,gender,dob)
    
        
#----------------------------------------------------------------------
def collectathlinks(aag,athlinksfile):
#----------------------------------------------------------------------
    '''
    Collect club age grade statistics, based on collected athlinks statistics (collectathlinksresults)
    
    :param aag: :class:`AnalyzeAgeGrade` objects, by runner name
    :param athlinksfile: file with athlinks results, output from athlinksresults
    '''
    # reading athlinksfile
    athlf = athlinksresults.AthlinksResultFile(athlinksfile)
    athlf.open()
    
    # read records from athlinksfile
    # gather each individual's result statistics, render later
    while True:
        result = next(athlf)
        if result is None: break
        
        thisname = result.name.lower()

        # initialize aag data structure, if not already done
        initaagrunner(aag,thisname,result.gender,result.dob)
    
        # collect this result
        timesecs = timeu.timesecs(result.resulttime)
        if timesecs > 0:
            aag[thisname].add_stat(result.racedate,result.distkm*1000,timesecs,race=result.racename,
                                   loc=result.raceloc,fuzzyage=result.fuzzyage,
                                   source='athlinks',priority=PRIO_ATHLINKS)

#----------------------------------------------------------------------
def collectultrasignup(aag,ultrasignupfile):
#----------------------------------------------------------------------
    '''
    Collect club age grade statistics, based on collected ultrasignup statistics (collectultrasignupresults)
    
    :param aag: :class:`AnalyzeAgeGrade` objects, by runner name
    :param ultrasignupfile: file with ultrasignup results, output from ultrasignupresults
    '''
    # reading ultrasignupfile
    ultra = ultrasignupresults.UltraSignupResultFile(ultrasignupfile)
    ultra.open()
    
    # read records from ultrasignupfile
    # gather each individual's result statistics, render later
    while True:
        result = next(ultra)
        if result is None: break
        
        thisname = result.name.lower()

        # initialize aag data structure, if not already done
        initaagrunner(aag,thisname,result.gender,result.dob)
    
        # collect this result
        timesecs = timeu.timesecs(result.time)
        if timesecs > 0:
            aag[thisname].add_stat(result.date,result.km*1000,timesecs,race=result.race,
                                   loc=result.loc,source='ultrasignup',priority=PRIO_ULTRASIGNUP)

#----------------------------------------------------------------------
def collectrunningahead(aag,runningaheadfile):
#----------------------------------------------------------------------
    '''
    Collect club age grade statistics, based on collected runningahead statistics (collectrunningaheadresults)
    
    :param aag: :class:`AnalyzeAgeGrade` objects, by runner name
    :param runningaheadfile: file with runningahead results, output from runningaheadresults
    '''
    # reading runningaheadfile
    rafile = runningaheadresults.RunningAheadResultFile(runningaheadfile)
    rafile.open()
    
    # read records from runningaheadfile
    # gather each individual's result statistics, render later
    while True:
        result = next(rafile)
        if result is None: break
        
        thisname = result.name.lower()

        # initialize aag data structure, if not already done
        initaagrunner(aag,thisname,result.gender,result.dob)
    
        # collect this result
        timesecs = timeu.timesecs(result.time)
        if timesecs > 0:
            aag[thisname].add_stat(result.date,result.km*1000,timesecs,race=result.race,source='runningahead',priority=PRIO_RUNNINGAHEAD)
        
#----------------------------------------------------------------------
def collectclub(aag,clubfile):
#----------------------------------------------------------------------
    '''
    Collect club age grade statistics, based on collected athlinks statistics (collectathlinksresults)
    
    :param aag: :class:`AnalyzeAgeGrade` objects, by runner name
    :param clubfile: file with club results, output from runningclub.exportresults
    '''
    # reading clubfile
    _clubf = open(clubfile,'r',newline='')
    clubf = csv.DictReader(_clubf)
    
    # TODO: move this to exportresults, a la athlinksresults; rename exportresults to clubresults
    tfile = timeu.asctime('%Y-%m-%d')
    class ClubResult():
        def __init__(self,name,dob,gender,racename,racedate,distmiles,distkm,resulttime,ag):
            self.name = name
            self.dob = tfile.asc2dt(dob)
            self.gender = gender
            self.racename = racename
            self.racedate = tfile.asc2dt(racedate)
            self.distmiles = float(distmiles)
            self.distkm = float(distkm)
            self.resulttime = timeu.timesecs(resulttime)
            self.ag = float(ag)
    
    # read records from clubfile
    # gather each individual's result statistics, render later
    while True:
        # if we've completed the last runner's result collection,
        # render the results, and set up for the next runner
        try:
            row = next(clubf)
            result = ClubResult(row['name'],row['dob'],row['gender'],row['race'],row['date'],row['miles'],row['km'],row['time'],row['ag'])
        except StopIteration:
            result = None
            
        # are we done?
        if result is None: break
        
        thisname = result.name.lower()

        # initialize aag data structure, if not already done
        initaagrunner(aag,thisname,result.gender,result.dob)
    
        # collect this result
        timesecs = result.resulttime
        if timesecs > 0:
            aag[thisname].add_stat(result.racedate,result.distkm*1000,timesecs,race=result.racename,source='clubraces',priority=PRIO_CLUBRACES)
        
            
#----------------------------------------------------------------------
def render(aag,outfile,summaryfile,detailfile,minagegrade,minraces,mintrend,begindate,enddate):
#----------------------------------------------------------------------
    '''
    render collected results

    :param outfile: output file name template, like '{who}-ag-analysis-{date}-{time}.png'
    :param summaryfile: summary file name template (.csv), may include {date} field
    :param detailfile: summary file name template (.csv), may include {date} field
    :param minagegrade: minimum age grade
    :param minraces: minimum races in the same year as enddate
    :param mintrend: minimum races over the full period for trendline
    :param begindate: render races between begindate and enddate, datetime
    :param enddate: render races between begindate and enddate, datetime
    '''
    firstyear = begindate.year
    lastyear = enddate.year
    yearrange = list(range(firstyear,lastyear+1))
    
    summfields = ['name','age','gender']
    distcategories = ['overall'] + [TRENDLIMITS[tlimit][0] for tlimit in TRENDLIMITS]
    for stattype in ['1yr agegrade','avg agegrade','trend','numraces','stderr','r-squared','pvalue']:
        for distcategory in distcategories:
            summfields.append('{}\n{}'.format(stattype,distcategory))
        if stattype == 'numraces':
            for year in yearrange:
                summfields.append('{}\n{}'.format(stattype,year))
    
    tfile = timeu.asctime('%Y-%m-%d')
    summaryfname = summaryfile.format(date=tfile.epoch2asc(time.time()))
    _SUMM = open(summaryfname,'w',newline='')
    SUMM = csv.DictWriter(_SUMM,summfields)
    SUMM.writeheader()
    
    detailfname = detailfile.format(date=tfile.epoch2asc(time.time()))
    detlfields = ['name','dob','gender'] + analyzeagegrade.AgeGradeStat.attrs + ['distmiles', 'distkm', 'rendertime']
    detlfields.remove('priority')   # priority is internal
    _DETL = open(detailfname,'w',newline='')
    DETL = csv.DictWriter(_DETL,detlfields,extrasaction='ignore')
    DETL.writeheader()
    
    # create a figure used for everyone -- required to save memory
    fig = plt.figure()
    
    # loop through each member we've recorded information about
    for thisname in aag:
        rendername = thisname.title()
        
        # remove duplicate entries
        aag[thisname].deduplicate()   
        
        # crunch the numbers, and remove entries less than minagegrade
        aag[thisname].crunch()    # calculate age grade for each result
        stats = aag[thisname].get_stats()
        #for stat in stats:
        #    if stat.ag < minagegrade:
        #        aag[thisname].del_stat(stat)
        
        # write detailed file before filtering
        name,gender,dob = aag[thisname].get_runner()
        detlout = {'name':rendername,'gender':gender,'dob':tfile.dt2asc(dob)}
        for stat in stats:
            for attr in analyzeagegrade.AgeGradeStat.attrs:
                detlout[attr] = getattr(stat,attr)
                if attr == 'date':
                    detlout[attr] = tfile.dt2asc(detlout[attr])
            # interpret some of the data from the raw stat
            detlout['distkm'] = detlout['dist'] / 1000.0
            detlout['distmiles'] = detlout['dist']/METERSPERMILE
            rendertime = ren.rendertime(detlout['time'],0)
            while len(rendertime.split(':')) < 3:
                rendertime = '0:'+rendertime
            detlout['rendertime'] = rendertime
            DETL.writerow(detlout)
            
        jan1 = tfile.asc2dt('{}-1-1'.format(lastyear))
        runnerage = timeu.age(jan1,dob)
        
        # filter out runners younger than 14
        if runnerage < 14: continue

        # filter out runners who have not run enough races
        stats = aag[thisname].get_stats()
        if enddate:
            lastyear = enddate.year
        else:
            lastyear = timeu.epoch2dt(time.time()).year
        lastyearstats = [s for s in stats if s.date.year==lastyear]
        if len(lastyearstats) < minraces: continue
        
        # set up output file name template
        if outfile:
            aag[thisname].set_renderfname(outfile)

        # set up rendering parameters
        aag[thisname].set_xlim(begindate,enddate)
        aag[thisname].set_ylim(minagegrade,100)
        aag[thisname].set_colormap([200,100*METERSPERMILE])

        # clear figure, set up axes
        fig.clear()
        ax = fig.add_subplot(111)
        
        # render the results
        aag[thisname].render_stats(fig)    # plot statistics

        # set up to collect averages
        avg = collections.OrderedDict()

        # draw trendlines, write output
        allstats = aag[thisname].get_stats()
        avg['overall'] = mean([s.ag for s in allstats])
        trend = aag[thisname].render_trendline(fig,'overall',color='k')

        # retrieve output filename for hyperlink
        # must be called after set_runner and set_renderfname
        thisoutfile = aag[thisname].get_outfilename()
       
        summout = {}
        summout['name'] = '=HYPERLINK("{}","{}")'.format(thisoutfile,rendername)
        summout['age'] = runnerage
        summout['gender'] = gender
        oneyrstats = [s.ag for s in allstats if s.date.year == lastyear]
        if len(oneyrstats) > 0:
            summout['1yr agegrade\noverall'] = mean(oneyrstats)
        summout['avg agegrade\noverall'] = avg['overall']
        if len(allstats) >= mintrend:
            summout['trend\noverall'] = trend.slope
            summout['stderr\noverall'] = trend.stderr
            summout['r-squared\noverall'] = trend.rvalue**2
            summout['pvalue\noverall'] = trend.pvalue
        summout['numraces\noverall'] = len(allstats)
        for year in yearrange:
            summout['numraces\n{}'.format(year)] = len([s for s in allstats if s.date.year==year])
        for tlimit in TRENDLIMITS:
            distcategory,distcolor = TRENDLIMITS[tlimit]
            tstats = [s for s in allstats if s.dist >= tlimit[0] and s.dist <= tlimit[1]]
            if len(tstats) < mintrend: continue
            avg[distcategory] = mean([s.ag for s in tstats])
            trend = aag[thisname].render_trendline(fig,distcategory,thesestats=tstats,color=distcolor)
            
            oneyrcategory = [s.ag for s in tstats if s.date.year == lastyear]
            if len(oneyrcategory) > 0:
                summout['1yr agegrade\n{}'.format(distcategory)] = mean(oneyrcategory)
            summout['avg agegrade\n{}'.format(distcategory)] = avg[distcategory]
            summout['trend\n{}'.format(distcategory)] = trend.slope
            summout['stderr\n{}'.format(distcategory)] = trend.stderr
            summout['r-squared\n{}'.format(distcategory)] = trend.rvalue**2
            summout['pvalue\n{}'.format(distcategory)] = trend.pvalue
            summout['numraces\n{}'.format(distcategory)] = len(tstats)
        SUMM.writerow(summout)
        
        # annotate with averages
        avgstr = 'averages\n'
        for lab in avg:
            thisavg = int(round(avg[lab]))
            avgstr += '  {}: {}%\n'.format(lab,thisavg)
        avgstr += 'age (1/1/{}): {}'.format(lastyear,runnerage)
        
        # TODO: add get_*lim() to aag -- xlim and ylim are currently side-effect of aag.render_stats()
        x1,xn = ax.get_xlim()
        y1,yn = ax.get_ylim()
        xy = (x1+10,y1+10)
        aag[thisname].render_annotate(fig,avgstr,xy)
        
        # save file
        aag[thisname].save(fig)
         
    _SUMM.close()
    _DETL.close()
    
#----------------------------------------------------------------------
def main(): 
#----------------------------------------------------------------------
    descr = '''
    render race results from athlinks, club
    '''
    
    parser = argparse.ArgumentParser(description=descr, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     version='{0} {1}'.format('running', version.__version__))
    parser.add_argument('-c','--clubfile', help="file with club results, output from exportresults",default=None)
    parser.add_argument('-a','--athlinksfile', help="file with athlinks results, output from athlinksresults",default=None)
    parser.add_argument('-u','--ultrasignupfile', help="file with club results, output from ultrasignupresults",default=None)
    parser.add_argument('-R','--runningaheadfile', help="file with club results, output from runningaheadresults",default=None)
    parser.add_argument('-o','--outfile', help="output file name template, like '{who}-ag-analysis-{date}-{time}.png', default=%(default)s",default='{who}-ag-analysis-{date}.png')
    parser.add_argument('-s','--summaryfile', help="summary file name template, default=%(default)s",default='ag-analysis-summary-{date}.csv')
    parser.add_argument('-d','--detailfile', help="detail file name template, default=%(default)s",default='ag-analysis-detail-{date}.csv')
    parser.add_argument('-g','--minagegrade', help="minimum age grade for charts, default=%(default)s",default=25)
    parser.add_argument('-r','--minraces', help="minimum races in the same year as ENDDATE, default=%(default)s",default=3)
    parser.add_argument('-t','--mintrend', help="minimum races between BEGINDATE and ENDDATE for trendline, default=%(default)s",default=5)
    parser.add_argument('-b','--begindate', help="render races between begindate and enddate, yyyy-mm-dd",default=None)
    parser.add_argument('-e','--enddate', help="render races between begindate and enddate, yyyy-mm-dd",default=None)
    args = parser.parse_args()

    athlinksfile = args.athlinksfile
    ultrasignupfile = args.ultrasignupfile
    runningaheadfile = args.runningaheadfile
    clubfile = args.clubfile
    outfile = args.outfile
    summaryfile = args.summaryfile
    detailfile = args.detailfile
    minagegrade = args.minagegrade
    minraces = args.minraces
    mintrend = args.mintrend

    argtime = timeu.asctime('%Y-%m-%d')
    if args.begindate:
        begindate = argtime.asc2dt(args.begindate)
    else:
        begindate = None
    if args.enddate:
        tmpenddate = argtime.asc2dt(args.enddate)
        enddate = datetime.datetime(tmpenddate.year,tmpenddate.month,tmpenddate.day,23,59,59)
    else:
        enddate = None
    
    # data structure to hold AnalyzeAgeGrade objects
    aag = {}
    
    # need data source file
    if not athlinksfile and not clubfile and not ultrasignupfile and not runningaheadfile:
        raise invalidParameter('athlinksfile, ultrasignupfile, runningaheadfile and/or clubfile required')

    # collect data from athlinks, if desired
    if athlinksfile:
        collectathlinks(aag,athlinksfile)
        
    # collect data from ultrasignup, if desired
    if ultrasignupfile:
        collectultrasignup(aag,ultrasignupfile)
        
    # collect data from runningahead, if desired
    if runningaheadfile:
        collectrunningahead(aag,runningaheadfile)
        
    # collect data from results database, if desired
    if clubfile:
        collectclub(aag,clubfile)
        
    # render all the data
    render(aag,outfile,summaryfile,detailfile,minagegrade,minraces,mintrend,begindate,enddate)
        
# ##########################################################################################
#	__main__
# ##########################################################################################
if __name__ == "__main__":
    main()