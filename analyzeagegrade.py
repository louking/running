#!/usr/bin/python
# ###############################################################################
# analyzeagegrade - analyze age grade race data
#
# Author: L King
#
# REVISION HISTORY:
#   08/08/12    L King      Create
# ###############################################################################
"""
convertbeamgain -- convert beam gain files from Globalstar format to Hughes format
=====================================================================================

Usage::

    TBA
"""

# standard libraries
import csv
import pdb
import argparse
import math
import time

# other libraries
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.dates as mdates
import matplotlib.font_manager as fontmgr

# home grown libraries
import version
from loutilities import timeu
from runningclub import agegrade
import running.runningahead as runningahead
from running.runningahead import FIELD

class unexpectedEOF(Exception): pass
class invalidParameter(Exception): pass

METERSPERMILE = 1609.344
MAXMETER = 4999
SUBS = {1609:'1M',3219:'2M',4989:'5K',5000:'5K',8047:'5M',10000:'10K',15000:'15K',16093:'10M',21082:'HM',21097:'HM',42165:'Marathon',42195:'Marathon'} #

t = timeu.asctime('%m/%d/%Y')
exectime = None     # execution time

#-------------------------------------------------------------------------------
def distmap(dist):
#-------------------------------------------------------------------------------
    """
    map distance to display metric
    
    :param dist: distance to map
    :rtype: float display metric for distance
    """
    return dist/100
    
#-------------------------------------------------------------------------------
def getdatafromfile(agfile):
#-------------------------------------------------------------------------------
    '''
    plot the data in dists
    
    :param agfile: name of csv file containing age grade data
    :rtype: dists,stats where dists =  set of distances included in stats, stats = {'date':[datetime of race,...], 'dist':[distance(meters),...], 'time':[racetime(seconds),...], 'agfile':[agegrade%age,...]} 
    '''
    
    _IN = open(agfile,'r')
    IN = csv.DictReader(_IN,dialect='excel')

    stats = {}
    for stype in ['date','dist','time','agfile']:
        stats[stype] = []
        
    dists = set([])
    
    # collect data
    linenum = 0
    while True:
        try:
            inrow = IN.next()
            linenum += 1
        except StopIteration:
            break
            
        s_date = inrow['Date']
        date = t.asc2dt(s_date)
        
        dist = float(inrow['Distance (miles)']) * METERSPERMILE
        
        # calculate number of seconds in string field [[hh:]mm:]ss[.000]
        s_rtime = inrow['Net']
        timefields = iter(s_rtime.split(':'))
        rtime = 0.0
        thisunit = float(timefields.next())
        while True:
            rtime += thisunit
            try:
                thisunit = float(timefields.next())
            except StopIteration:
                break
            rtime *= 60 # doesn't happen if last field was processed before
        

        # age grade calculation was moved to crunch() to crunch age grade and pace
        # this just saves what was in the file in case I ever want to compare
        s_ag = inrow['AG']
        if s_ag:    
            if s_ag[-1] == '%':
                ag = float(s_ag[:-1])
            else:
                ag = float(s_ag)
        # we don't care about this entry if AG wasn't captured
        else:
            ag = None
            
        dists.add(round(dist))      # keep track of distances to nearest meter
        stats['date'].append(date)
        stats['dist'].append(dist)
        stats['time'].append(rtime)
        stats['agfile'].append(ag) # 'ag' done in crunch()
        #print(s_date,date,dist,ag)
        
    _IN.close()
    
    return dists, stats

#-------------------------------------------------------------------------------
def getdatafromra(who,gender=None):
#-------------------------------------------------------------------------------
    '''
    get the user's data from RunningAHEAD
    
    :param who: name of person to pull data for.  Must match what's in RunningAHEAD database exactly
    :param gender: gender, either 'M' or 'F' - for override of data in RunningAHEAD
    :rtype: dists,stats,dob,gender where dists =  set of distances included in stats, stats = {'date':[datetime of race,...], 'dist':[distance(meters),...], 'time':[racetime(seconds),...]}, dob = date of birth (datetime), gender = 'M'|'F'
    '''
    # set up RunningAhead object and get users we're allowed to look at
    ra = runningahead.RunningAhead()    
    users = ra.listusers()
    day = timeu.asctime('%Y-%m-%d') # date format in RunningAhead workout object
    
    # in case nothing is found
    dists = None
    stats = None
    dob = None
    
    workouts = None
    for user in users:
        thisuser = ra.getuser(user['token'])
        if 'givenName' not in thisuser: continue    # we need to know the name
        givenName = thisuser['givenName'] if 'givenName' in thisuser else ''
        familyName = thisuser['familyName'] if 'familyName' in thisuser else ''
        thisusername = ' '.join([givenName,familyName])
        if thisusername != who: continue            # not this user, keep looking
        
        # grab user's date of birth
        dob = day.asc2dt(thisuser['birthDate'])
        if not gender:
            gender = 'M' if thisuser['gender']=='male' else 'F'
        
        # if we're here, found the right user, now let's look at the workouts
        firstdate = day.asc2dt('1980-01-01')
        lastdate = day.asc2dt('2199-12-31')
        workouts = ra.listworkouts(user['token'],begindate=firstdate,enddate=lastdate,getfields=FIELD['workout'].keys())

        # we've found the right user and collected their data, so we're done
        break
        
    # save race workouts, if any found
    if workouts:
        tempstats = []
        for wo in workouts:
            if wo['workoutName'].lower() != 'race': continue
            thisdate = day.asc2dt(wo['date'])
            thisdist = runningahead.dist2meters(wo['details']['distance'])
            thistime = wo['details']['duration']
            
            tempstats.append((thisdate,{'date':thisdate,'dist':thisdist,'time':thistime}))
            
    # these may come sorted already, but just in case
    #tempstats.sort()
    
    # put the stats in the right format
    stats = {}
    for stype in ['date','dist','time']:
        stats[stype] = []
    dists = set([])

    for thisdate,thisstat in tempstats:
        for stattype in ['date','dist','time']:
            stats[stattype].append(thisstat[stattype])
        dist = thisstat['dist']
        dists.add(round(dist))      # keep track of distances to nearest meter

    return dists,stats,dob,gender

#-------------------------------------------------------------------------------
def crunch(stats,gender,dob):
#-------------------------------------------------------------------------------
    '''
    crunch the race data to put the age grade data into the stats
    
    :param stats: list of {'dist':distance(meters), 'date':racedate, 'size':size of circle, 'ag':agegrade%age} entries ('size' optional)
    :param gender: gender, either 'M' or 'F'
    :param dob: date of birth, datetime format
    '''
    ### DEBUG>
    debug = False
    if debug:
        tim = timeu.asctime('%Y-%m-%d-%H-%M')
        _DEB = open('analyzeagegrade-debug-{}-crunch.csv'.format(tim.epoch2asc(exectime)),'wb')
        fields = ['date','dist','time','ag']
        DEB = csv.DictWriter(_DEB,fields)
        DEB.writeheader()
    ### <DEBUG
        
    # pull in age grade object
    ag = agegrade.AgeGrade()

    # calculate age grade for each sample    
    stats['ag'] = []
    for i in range(len(stats['dist'])):
        racedate = stats['date'][i]
        agegradeage = racedate.year - dob.year - int((racedate.month, racedate.day) < (dob.month, dob.day))
        distmiles = stats['dist'][i]/METERSPERMILE
        agpercentage,agtime,agfactor = ag.agegrade(agegradeage,gender,distmiles,stats['time'][i])
        stats['ag'].append(agpercentage)
        
        ### DEBUG>
        if debug:
            thisstat = {}
            for stattype in fields:
                thisstat[stattype] = stats[stattype][i]
            DEB.writerow(thisstat)
        ### <DEBUG
        
    ### DEBUG>
    if debug:
        _DEB.close()
    ### <DEBUG

#-------------------------------------------------------------------------------
def render(dists,stats,who,size,ylim=None):
#-------------------------------------------------------------------------------
    '''
    plot the data in dists
    
    :param dists: set of distances included in stats
    :param stats: list of {'dist':distance(meters), 'size':size of circle, 'ag':agegrade%age} entries ('size' optional)
    :param who: name for file header
    :param size: true if size needed
    :param ylim: limits on y axis as two-sequence
    '''
    DEFAULTSIZE = 60
    
    ### DEBUG>
    debug = False
    if debug:
        tim = timeu.asctime('%Y-%m-%d-%H-%M')
        _DEB = open('analyzeagegrade-debug-{}-render.csv'.format(tim.epoch2asc(exectime)),'wb')
        fields = ['date','dist','ag','color','label']
        DEB = csv.DictWriter(_DEB,fields)
        DEB.writeheader()
    ### <DEBUG

    # open output file
    if size:
        s_size = 'size'
    else:
        s_size = 'color'
    outfile = '{0}-ag-analysis-{1}.png'.format(who,s_size)

    # make hashed scatter lists
    hdate = {}
    hag = {}
    hsize = {}
    for thisd in dists:
        hdate[thisd] = []
        hag[thisd] = []
        hsize[thisd] = []
    for i in range(len(stats['dist'])):
        d = round(stats['dist'][i])
        hdate[d].append(stats['date'][i])
        hag[d].append(stats['ag'][i])
        if size:
            hsize[d].append(distmap(d))
#            hsize[d].append(stats['size'][i])
        else:
            hsize[d].append(DEFAULTSIZE)
    
    # set up color normalization
    cnorm = colors.LogNorm()
    cnorm.autoscale(stats['dist'])
    
    cmap = cm.jet
    cmapsm = cm.ScalarMappable(cmap=cmap,norm=cnorm)
    
    fig = plt.figure()
    fig.autofmt_xdate()
    ax = fig.add_subplot(111)
    ax.set_ylabel('age grade percentage')
    ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
    fig.suptitle("\n{0}'s age grade performance over time".format(who,s_size))
        
    lines = []
    labs = []
    l_dists = list(dists)
    l_dists.sort()
    fig.subplots_adjust(bottom=0.1, right=0.8, top=0.9)
    ax.grid(b=True)
    for thisd in l_dists:
        if int(thisd) in SUBS:
            lab = SUBS[int(thisd)]
        else:
            if thisd <=MAXMETER:
                lab = '{0}m'.format(int(thisd))
            else:
                lab = '{0:.1f}K'.format(thisd/1000)
        labs.append(lab)
        color = cmapsm.to_rgba(thisd)
        numels = len(hdate[thisd])
        line = ax.scatter(hdate[thisd],hag[thisd],s=hsize[thisd],c=[color for i in range(numels)],label=lab,linewidth=.5)
        #line = ax.scatter(hdate[thisd],hag[thisd],s=60,c=cmapsm.to_rgba(thisd),label=lab,edgecolors='none')
        lines.append(line)

        ### DEBUG>
        if debug:
            thisstat = {}
            for i in range(len(hdate[thisd])):
                thisstat['date'] = hdate[thisd][i]
                thisstat['ag'] = hag[thisd][i]
                thisstat['dist'] = thisd
                thisstat['label'] = lab
                thisstat['color'] = cmapsm.to_rgba(thisd)
                DEB.writerow(thisstat)
        ### <DEBUG

    # set x label format
    hfmt = mdates.DateFormatter('%m/%d/%y')
    ax.xaxis.set_major_formatter(hfmt)
    ax.xaxis.set_minor_formatter(hfmt)
    
    labels = ax.get_xticklabels()
    for label in labels:
        label.set_rotation(65)
        label.set_size('xx-small')

    # maybe user wants to set ylim
    # TODO: check to see if any points are outside this limit, and print warning
    if ylim:
        ax.set_ylim(ylim)
        
    ### DEBUG>
    if debug:
        _DEB.close()
    ### <DEBUG

    smallfont = fontmgr.FontProperties(size='small')
    ax.legend(loc=1,bbox_to_anchor=(1.25, 1),prop=smallfont)    #bbox_to_anchor moves legend outside axes
    fig.savefig(outfile,format='png')
    del fig
    
#-------------------------------------------------------------------------------
def main():
#-------------------------------------------------------------------------------

    usage = "     where:"
    usage += "\n        agfile is csv file containing Date, Distance (miles), AG headers"
    usage += "\n        who is name for chart header (default Lou)"

    parser = argparse.ArgumentParser(version='running {0}'.format(version.__version__))
    parser.add_argument('--agfile', help="age grade csv file, with fields 'Date', 'Distance (miles)', 'AG' (optional, takes precedence)", default=None)
    parser.add_argument('--ra', action='store_true', help="use --ra to get data from RunningAHEAD")
    parser.add_argument('--athlinks', action='store_true', help="use --athlinks to get data from athlinks [TBA]")
    parser.add_argument('-y', '--ylim', help="y limits, of the form (min,max), e.g., (55,80)")
    parser.add_argument('-w', '--who', help="specify name to be used in plot header, and to pick user for --ra and --athlinks")
    parser.add_argument('-b', '--dob', help="specify birth date for age grade, in mm/dd/yyyy format, required if --agfile specified", default=None)
    parser.add_argument('-g', '--gender', help="specify gender for age grade, M or F, required if --agfile specified", default=None)
    parser.add_argument('-s', '--size', action='store_true', help="use --size if circle size by distance is desired")
    args = parser.parse_args()
    
    # execution time for debug file names
    global exectime
    exectime = time.time()
    
    # get arguments
    agfile = args.agfile
    usera = args.ra
    useathlinks = args.athlinks
    who = args.who
    if args.dob:
        dt_dob = t.asc2dt(args.dob)
    else:
        dt_dob = None
    gender = args.gender
    size = args.size
    if args.ylim:
        try:
            ylim = eval(args.ylim)
            if len(ylim) != 2 or type(ylim[0]) not in [int,float] or type(ylim[0]) not in [int,float]:
                raise ValueError
        except:
            print "YLIM argument must be of the form(min,max), e.g., (55,80)"
            return

    # get data from age grade csv file
    if agfile:
        dists,stats = getdatafromfile(agfile)
        
    # get data from RunningAHEAD
    if usera:
        dists,stats,radob,gender = getdatafromra(who,gender)
        # let command line DOB take preference to what's in RunningAHEAD
        if not dt_dob:
            dt_dob = radob
    
    # TODO: combine file data with RA data -- currently RA data takes precedence
    
    # add age grade percentage to each result
    crunch(stats,gender,dt_dob)
    
    # plot distance statistics
    render(dists,stats,who,size,ylim)
    
    
# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

