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
analyzeagegrade - analyze age grade race data
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
SUBS = {1609:'1M',3219:'2M',4989:'5K',5000:'5K',8047:'5M',10000:'10K',15000:'15K',
        16093:'10M',21082:'HM',21097:'HM',42165:'Marathon',42195:'Marathon',
        80467:'50M',160934:'100M'} #

t = timeu.asctime('%m/%d/%Y')
# pull in age grade object
ag = agegrade.AgeGrade()
    

#-------------------------------------------------------------------------------
def distmap(dist):
#-------------------------------------------------------------------------------
    """
    map distance to display metric
    
    :param dist: distance to map
    :rtype: float display metric for distance
    """
    return dist/100
    
########################################################################
class AnalyzeAgeGrade():
########################################################################
    '''
    age grade analysis
    '''
    
    #-------------------------------------------------------------------------------
    def __init__(self):
    #-------------------------------------------------------------------------------
        self.exectime = time.time()
        self.gender = None
        self.dob = None
        self.cmapsm = None
        self.xlim = None
        self.ylim = None
        self.fig = plt.figure()
        self.renderfname = '{name}-ag-analysis-{date}-{time}.png'
        self.clear()
        
    #-------------------------------------------------------------------------------
    def clear(self):
    #-------------------------------------------------------------------------------
        '''
        clear statistics
        '''
        # stats = {'date':[datetime of race,...], 'dist':[distance(meters),...], 'time':[racetime(seconds),...], 'agfile':[agegrade%age,...]} 
        self.stats = {}
        for stype in ['date','dist','time','agfile']:
            self.stats[stype] = []
        
        # self.dists = set of distances included in stats
        self.dists = set([])
        
    #-------------------------------------------------------------------------------
    def add_stat(self, date, dist, time):
    #-------------------------------------------------------------------------------
        '''
        add an individual statistic
        
        :param date: date in datetime format
        :param dist: distance in meters
        :param time: time in seconds
        '''
        
        self.stats['date'].append(date)
        self.stats['dist'].append(dist)
        self.stats['time'].append(time)
        self.dists.add(round(dist))
        
    #-------------------------------------------------------------------------------
    def deduplicate(self):
    #-------------------------------------------------------------------------------
        '''
        remove statistics which are duplicates, assuming stats on same day
        for same distance are duplicated
        '''
        eps = .01   # epsilon -- if event distance is within this tolerance, it is considered the same
        

        

    #-------------------------------------------------------------------------------
    def set_renderfname(self,renderfname):
    #-------------------------------------------------------------------------------
        '''
        set filename template for rendered files
        
        form is similar to '{who}-ag-analysis-{date}-{time}.png'
        
        where:
        
            * who - comes from :meth:`set_runner` who parameter
            * date - comes from the time the :class:`AnalyzeAgeGrade` object was created, yyyy-mm-dd
            * time - comes from the time the :class:`AnalyzeAgeGrade` object was created, hhmm
        
        :param renderfname: filename template
        '''
        self.renderfname = renderfname
        
    #-------------------------------------------------------------------------------
    def set_runner(self,who,gender=None,dob=None):
    #-------------------------------------------------------------------------------
        '''
        set runner parameters required for age grade analysis
        
        :param who: name of runner
        :param gender: M or F
        :param dob: datetime date of birth
        '''
        self.who = who
        self.gender = gender
        self.dob = dob
        
    #-------------------------------------------------------------------------------
    def set_xlim(self,left,right):
    #-------------------------------------------------------------------------------
        '''
        set x limits
        
        :param left: value of left limit for x
        :param right: value of right limit for x
        '''
        self.xlim = (left,right)
        
    #-------------------------------------------------------------------------------
    def set_ylim(self,bottom,top):
    #-------------------------------------------------------------------------------
        '''
        set y limits
        
        :param bottom: value of bottom limit for y
        :param top: value of top limit for y
        '''
        self.ylim = (bottom,top)
        
    #-------------------------------------------------------------------------------
    def set_colormap(self,dists=None):
    #-------------------------------------------------------------------------------
        '''
        set color mapping for rendering, based on range of distance statistics
        
        :param dists: sequence containing range which must be met by colormap, defaults to stored statistics, meters
        '''
        # set up color normalization
        cnorm = colors.LogNorm()
        if dists:
            cnorm.autoscale(dists)
        else:
            cnorm.autoscale(self.stats['dist'])
        cmap = cm.jet
        self.cmapsm = cm.ScalarMappable(cmap=cmap,norm=cnorm)
        
    #-------------------------------------------------------------------------------
    def getdatafromfile(self, agfile):
    #-------------------------------------------------------------------------------
        '''
        plot the data in dists
        
        :param agfile: name of csv file containing age grade data
        :rtype: 
        '''
        
        _IN = open(agfile,'r')
        IN = csv.DictReader(_IN,dialect='excel')
    
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
                
            self.dists.add(round(dist))      # keep track of distances to nearest meter
            self.stats['date'].append(date)
            self.stats['dist'].append(dist)
            self.stats['time'].append(rtime)
            self.stats['agfile'].append(ag) # 'ag' done in crunch()
            #print(s_date,date,dist,ag)
            
        _IN.close()
    
    #-------------------------------------------------------------------------------
    def getdatafromra(self):
    #-------------------------------------------------------------------------------
        '''
        get the user's data from RunningAHEAD
        
        :rtype: dists,stats,dob,gender where dists =  set of distances included in stats, stats = {'date':[datetime of race,...], 'dist':[distance(meters),...], 'time':[racetime(seconds),...]}, dob = date of birth (datetime), gender = 'M'|'F'
        '''
        # set up RunningAhead object and get users we're allowed to look at
        ra = runningahead.RunningAhead()    
        users = ra.listusers()
        day = timeu.asctime('%Y-%m-%d') # date format in RunningAhead workout object
        
        # find correct user, grab their workouts
        workouts = None
        for user in users:
            thisuser = ra.getuser(user['token'])
            if 'givenName' not in thisuser: continue    # we need to know the name
            givenName = thisuser['givenName'] if 'givenName' in thisuser else ''
            familyName = thisuser['familyName'] if 'familyName' in thisuser else ''
            thisusername = ' '.join([givenName,familyName])
            if thisusername != self.who: continue            # not this user, keep looking
            
            # grab user's date of birth and gender, if not already supplied
            if not self.dob:
                self.dob = day.asc2dt(thisuser['birthDate'])
            if not self.gender:
                self.gender = 'M' if thisuser['gender']=='male' else 'F'
            
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
        for thisdate,thisstat in tempstats:
            for stattype in ['date','dist','time']:
                self.stats[stattype].append(thisstat[stattype])
            dist = thisstat['dist']
            self.dists.add(round(dist))      # keep track of distances to nearest meter
    
    #-------------------------------------------------------------------------------
    def crunch(self):
    #-------------------------------------------------------------------------------
        '''
        crunch the race data to put the age grade data into the stats
        
        '''
        ### DEBUG>
        debug = False
        if debug:
            tim = timeu.asctime('%Y-%m-%d-%H%M')
            _DEB = open('analyzeagegrade-debug-{}-crunch-{}.csv'.format(tim.epoch2asc(self.exectime,self.who)),'wb')
            fields = ['date','dist','time','ag']
            DEB = csv.DictWriter(_DEB,fields)
            DEB.writeheader()
        ### <DEBUG
            
        # calculate age grade for each sample    
        self.stats['ag'] = []
        for i in range(len(self.stats['dist'])):
            racedate = self.stats['date'][i]
            agegradeage = racedate.year - self.dob.year - int((racedate.month, racedate.day) < (self.dob.month, self.dob.day))
            distmiles = self.stats['dist'][i]/METERSPERMILE
            agpercentage,agtime,agfactor = ag.agegrade(agegradeage,self.gender,distmiles,self.stats['time'][i])
            self.stats['ag'].append(agpercentage)
            
            ### DEBUG>
            if debug:
                thisstat = {}
                for stattype in fields:
                    thisstat[stattype] = self.stats[stattype][i]
                DEB.writerow(thisstat)
            ### <DEBUG
            
        ### DEBUG>
        if debug:
            _DEB.close()
        ### <DEBUG
    
    #-------------------------------------------------------------------------------
    def render(self, size=False):
    #-------------------------------------------------------------------------------
        '''
        plot the data in dists
        
        :param size: true if size needed
        '''
        DEFAULTSIZE = 60
        
        ### DEBUG>
        debug = False
        if debug:
            tim = timeu.asctime('%Y-%m-%d-%H-%M')
            _DEB = open('analyzeagegrade-debug-{}-render.csv'.format(tim.epoch2asc(self.exectime)),'wb')
            fields = ['date','dist','ag','color','label']
            DEB = csv.DictWriter(_DEB,fields)
            DEB.writeheader()
        ### <DEBUG
    
        # open output file
        if size:
            s_size = 'size'
        else:
            s_size = 'color'
        tdate = timeu.asctime('%Y-%m-%d')
        ttime = timeu.asctime('%H%M')
        outfile = self.renderfname.format(who=self.who,date=tdate.epoch2asc(self.exectime),time=ttime.epoch2asc(self.exectime))
    
        # make hashed scatter lists
        hdate = {}
        hag = {}
        hsize = {}
        for thisd in self.dists:
            hdate[thisd] = []
            hag[thisd] = []
            hsize[thisd] = []
        for i in range(len(self.stats['dist'])):
            d = round(self.stats['dist'][i])
            hdate[d].append(self.stats['date'][i])
            hag[d].append(self.stats['ag'][i])
            if size:
                hsize[d].append(distmap(d))
    #            hsize[d].append(self.stats['size'][i])
            else:
                hsize[d].append(DEFAULTSIZE)
        
        # create figure and axes
        self.fig.clear()
        self.fig.autofmt_xdate()
        ax = self.fig.add_subplot(111)
        ax.set_ylabel('age grade percentage')
        #ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d') # dead?
        self.fig.suptitle("{0}'s age grade performance over time".format(self.who,s_size))
            
        lines = []
        labs = []
        l_dists = list(self.dists)
        l_dists.sort()
        self.fig.subplots_adjust(bottom=0.1, right=0.85, top=0.93)
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
            color = self.cmapsm.to_rgba(thisd)
            numels = len(hdate[thisd])
            line = ax.scatter(hdate[thisd],hag[thisd],s=hsize[thisd],c=[color for i in range(numels)],label=lab,linewidth=.5)
            #lines.append(line)
    
            ### DEBUG>
            if debug:
                thisstat = {}
                for i in range(len(hdate[thisd])):
                    thisstat['date'] = hdate[thisd][i]
                    thisstat['ag'] = hag[thisd][i]
                    thisstat['dist'] = thisd
                    thisstat['label'] = lab
                    thisstat['color'] = self.cmapsm.to_rgba(thisd)
                    DEB.writerow(thisstat)
            ### <DEBUG
    
        # set x (date) label format
        hfmt = mdates.DateFormatter('%m/%d/%y')
        ax.xaxis.set_major_formatter(hfmt)
        ax.xaxis.set_minor_formatter(hfmt)
        labels = ax.get_xticklabels()
        for label in labels:
            label.set_rotation(65)
            label.set_size('xx-small')
    
        # maybe user wants to set ylim
        # check to see if any points are outside this limit, and print warning
        if self.ylim:
            ax.set_ylim(self.ylim)
            outsidelimits = 0
            numpoints = 0
            for thisd in l_dists:
                for i in range(len(hdate[thisd])):
                    numpoints += 1
                    if hag[thisd][i] < self.ylim[0] or hag[thisd][i] > self.ylim[1]:
                        outsidelimits += 1
            if outsidelimits > 0:
                print '*** WARNING: {} of {} points found outside of ylim {}, runner {}'.format(outsidelimits,numpoints,self.ylim,self.who)
            
        ### DEBUG>
        if debug:
            _DEB.close()
        ### <DEBUG
    
        smallfont = fontmgr.FontProperties(size='x-small')
        ax.legend(loc=1,bbox_to_anchor=(1.19, 1),prop=smallfont)    #bbox_to_anchor moves legend outside axes
        self.fig.savefig(outfile,format='png')
    
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
    parser.add_argument('-y', '--ylim', help="y limits, of the form (bottom,top), e.g., (55,80)")
    parser.add_argument('-w', '--who', help="specify name to be used in plot header, and to pick user for --ra and --athlinks")
    parser.add_argument('-b', '--dob', help="specify birth date for age grade, in mm/dd/yyyy format, required if --agfile or --athlinks specified", default=None)
    parser.add_argument('-g', '--gender', help="specify gender for age grade, M or F, required if --agfile or --athlinks specified", default=None)
    parser.add_argument('-s', '--size', action='store_true', help="use --size if circle size by distance is desired")
    args = parser.parse_args()
    
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
            print "YLIM argument must be of the form(bottom,top), e.g., (55,80)"
            return
    else:
        ylim = None

    # set up to analyze age grade
    aag = AnalyzeAgeGrade()
    aag.set_runner(who,gender,dt_dob)
    
    # get data from age grade csv file
    if agfile:
        aag.getdatafromfile(agfile)
        
    # get data from RunningAHEAD
    if usera:
        aag.getdatafromra()
    
    # TODO: combine file data with RA data -- currently RA data takes precedence
    
    # add age grade percentage to each result
    aag.crunch()
    
    # set up rendering parameters in aag
    # TODO: add option to control color map setup
    aag.set_colormap()
    if ylim:
        aag.set_ylim(ylim[0],ylim[1])
    
    # plot distance statistics
    aag.render(size)
    
    
# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

