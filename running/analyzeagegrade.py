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
import argparse
import time
import logging
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')
log = logging.getLogger('running.analyzeagegrade')
log.setLevel(logging.INFO)

# other libraries
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.dates as mdates
import matplotlib.font_manager as fontmgr
from scipy import stats

# home grown libraries
from running.running import version
from loutilities import timeu
from runningclub import agegrade
import running.running.runningahead as runningahead
from running.running.runningahead import FIELD

class unexpectedEOF(Exception): pass
class invalidParameter(Exception): pass

METERSPERMILE = 1609.344
MAXMETER = 4999
SUBS = {1609:'1M',3219:'2M',4989:'5K',5000:'5K',8047:'5M',10000:'10K',15000:'15K',
        16093:'10M',21082:'HM',21097:'HM',42165:'Marathon',42195:'Marathon',
        80467:'50M',160934:'100M'} #

tdisp = timeu.asctime('%m/%d/%Y')
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
class AgeGradeStat():
########################################################################
    '''
    statistic for age grade analysis, for a single runner
    
    :param date: date in datetime format
    :param dist: distance in meters
    :param time: time in seconds
    :param ag: age grade percentage (float, 0-100)
    :param race: race name
    :param loc: location of race
    :param source: source of data
    :param fuzzyage: 'Y' if age check was done based on age group rather than exact age, None otherwise
    :param priority: priority for deduplication, lowest value is kept (lower number = higher priority)
    '''
    attrs = 'race,date,loc,dist,time,ag,source,fuzzyage,priority'.split(',')
    
    #-------------------------------------------------------------------------------
    def __init__(self,date=None,dist=None,time=None,ag=None,race=None,loc=None,source=None,fuzzyage=None,priority=1):
    #-------------------------------------------------------------------------------
        self.date = date
        self.dist = dist
        self.time = time
        self.ag = ag
        self.race = race
        self.loc = loc
        self.source = source
        self.fuzzyage = fuzzyage
        self.priority = priority
        
    #-------------------------------------------------------------------------------
    def __repr__(self):
    #-------------------------------------------------------------------------------
        retval = '{}({}, {} meters, {} secs'.format(self.__class__,tdisp.dt2asc(self.date),self.dist,self.time)
        if self.ag:
            retval += ', age grade = {}'.format(self.ag)
        if self.race:
            retval += ', {}'.format(self.race)
        retval += ')'
        return retval

########################################################################
class TrendLine():
########################################################################
    '''
    regression line parameters (ref http://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.linregress.html)
    
    :param slope: slope of the regression line
    :param intercept: intercept fo the regression line
    :param rvalue: correlation coefficient
    :param pvalue: two-sided p-value for hypothesis test whose null hypothesis is that the slope is zero
    :param stderr: standard error of the estimate
    '''
    
    #-------------------------------------------------------------------------------
    def __init__(self,slope,intercept,rvalue,pvalue,stderr):
    #-------------------------------------------------------------------------------
        self.slope = slope
        self.intercept = intercept
        self.rvalue = rvalue
        self.pvalue = pvalue
        self.stderr = stderr
        
    #-------------------------------------------------------------------------------
    def __repr__(self):
    #-------------------------------------------------------------------------------
        retval = 'analyzeagegrade.TrendLine(slope {:0.2f}, intercept {:0.2f}, rvalue {:0.2f}, pvalue {:0.2f}, stderr {:0.2f})'.format(
            self.slope, self.intercept, self.rvalue, self.pvalue,self.stderr)
        return retval
    
        
########################################################################
class AnalyzeAgeGrade():
########################################################################
    '''
    age grade analysis
    '''
    
    #-------------------------------------------------------------------------------
    def __init__(self, size=False):
    #-------------------------------------------------------------------------------
        self.exectime = time.time()
        self.gender = None
        self.dob = None
        self.cmapsm = None
        self.renderfname = '{who}-ag-analysis-{date}-{time}.png'
        self.xlim = {'left':None,'right':None}
        self.ylim = None    # TODO: make 'top','bottom' dict
        
        # sized markers or just color
        self.size = size
        if size:
            self.s_size = 'size'
        else:
            self.s_size = 'color'
        
        self.clear()
        
    #-------------------------------------------------------------------------------
    def clear(self):
    #-------------------------------------------------------------------------------
        '''
        clear statistics
        '''
        # stats = list(AgeGradeStat(),... ) 
        self.stats = []
        
        # self.dists = set of distances included in stats, rounded
        self.dists = set([])

    #-------------------------------------------------------------------------------
    def add_stat(self, date, dist, time, **kwargs):
    #-------------------------------------------------------------------------------
        '''
        add an individual statistic
        
        :param date: date in datetime format
        :param dist: distance in meters
        :param time: time in seconds
        :param kwargs: keyword arguments, must match AgeGradeState attrs
        '''
        
        self.stats.append(AgeGradeStat(date,dist,time,**kwargs))
        self.dists.add(round(dist))
        
    #-------------------------------------------------------------------------------
    def del_stat(self, stat):
    #-------------------------------------------------------------------------------
        '''
        delete the indicated statistic
        
        :param stat: :class:`AgeGradeStat` to delete
        '''
        try:
            self.stats.remove(stat)
        except ValueError:
            log.warning('del_stat: failed to delete {}'.format(stat))
        
    #-------------------------------------------------------------------------------
    def get_stats(self):
    #-------------------------------------------------------------------------------
        '''
        return stats collected
        
        :rtype: list of :class:`AgeGradeStat` entries
        '''
        return self.stats
    
    #-------------------------------------------------------------------------------
    def deduplicate(self):
    #-------------------------------------------------------------------------------
        '''
        remove statistics which are duplicates, assuming stats on same day
        for same distance are duplicated
        '''
        
        ## sort statistics by (date,dist)
        #decstats = [((s.date,s.dist,s.priority),s) for s in self.stats]
        #decstats.sort()
        #
        ## collect unique statistics, within epsilon distance
        #EPS = .1   # epsilon -- if event distance is within this tolerance, it is considered the same
        #
        #key,firststat = decstats.pop(0)
        #deduped = [firststat]
        #for key,thisstat in decstats:
        #    laststat = deduped[-1]
        #    # only accumulate if date or distance mismatch from last collected
        #    if laststat.date != thisstat.date or abs((laststat.dist-thisstat.dist)/laststat.dist) > EPS:
        #        deduped.append(thisstat)
        #
        #dupremoved = len(self.stats) - len(deduped)
        #if dupremoved > 0:
        #    log.debug('{} duplicate points removed, runner {}'.format(dupremoved,self.who))
        
        # be careful of degenerate case
        if len(self.stats) == 0:
            return

        # collect unique statistics, within epsilon distance
        EPS = .1   # epsilon -- if event distance is within this tolerance, it is considered the same

        # sort self.stats into stats, by date,distance
        decstats = sorted([((s.date,s.dist),s) for s in self.stats])
        stats = [ds[1] for ds in decstats]
        
        # deduplicate stats, paying attention to priority when races determined to be the same
        deduped = []
        while len(stats) > 0:
            # get the first entry, that's the first "samerace"
            thisstat = stats.pop(0)
            sameraces = [(thisstat.priority,thisstat)]
            
            # pull races off stats when the race date and distance are the same
            # distance has to be within epsilon to be deduced to be the same
            while   len(stats) > 0 \
                    and thisstat.date == stats[0].date \
                    and abs((thisstat.dist - stats[0].dist) / thisstat.dist) <= EPS:
                stat = stats.pop(0)
                sameraces.append((stat.priority,stat))
            
            # sort same races by priority, and add highes priority (lowest valued) to deduped list
            sameraces.sort()
            prio,stat = sameraces[0]
            deduped.append(stat)
        
        dupremoved = len(self.stats) - len(deduped)
        if dupremoved > 0:
            log.debug('{} duplicate points removed, runner {}'.format(dupremoved,self.who))

        # replace self.stats with deduplicated version
        self.stats = deduped

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
    def get_outfilename(self):
    #-------------------------------------------------------------------------------
        '''
        get output filename
        
        must be called after :meth:`set_runner` and :meth:`set_renderfname`
        
        :rtype: name of output file for plot
        '''
        tdate = timeu.asctime('%Y-%m-%d')
        ttime = timeu.asctime('%H%M')
        outfilename = self.renderfname.format(who=self.who,date=tdate.epoch2asc(self.exectime),time=ttime.epoch2asc(self.exectime))
        return outfilename
    
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
    def get_runner(self):
    #-------------------------------------------------------------------------------
        '''
        return runner data
        
        :rtype: name,gender,dob
        '''
        return self.who,self.gender,self.dob
    
    #-------------------------------------------------------------------------------
    def set_xlim(self,left,right):
    #-------------------------------------------------------------------------------
        '''
        set x limits
        
        :param left: datetime value of left limit for x
        :param right: datetime value of right limit for x
        '''
        #self.xlim = (left,right)
        self.xlim = {'left':None,'right':None}
        if left:
            self.xlim['left'] = left
        if right:
            self.xlim['right'] = right
        
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
            cnorm.autoscale([s.dist for s in self.stats])
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
                inrow = next(IN)
                linenum += 1
            except StopIteration:
                break
                
            s_date = inrow['Date']
            date = tdisp.asc2dt(s_date)
            
            dist = float(inrow['Distance (miles)']) * METERSPERMILE
            
            # calculate number of seconds in string field [[hh:]mm:]ss[.000]
            s_rtime = inrow['Net']
            timefields = iter(s_rtime.split(':'))
            rtime = 0.0
            thisunit = float(next(timefields))
            while True:
                rtime += thisunit
                try:
                    thisunit = float(next(timefields))
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
            self.stats.append(AgeGradeStat(date,dist,rtime))
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
            workouts = ra.listworkouts(user['token'],begindate=firstdate,enddate=lastdate,getfields=list(FIELD['workout'].keys()))
    
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
                
                tempstats.append((thisdate,AgeGradeStat(thisdate,thisdist,thistime)))
                
        # these may come sorted already, but just in case
        #tempstats.sort()
        
        # put the stats in the right format
        for thisdate,thisstat in tempstats:
            self.stats.append(thisstat)
            self.dists.add(round(thisstat.dist))      # keep track of distances to nearest meter
    
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
        for i in range(len(self.stats)):
            racedate = self.stats[i].date
            agegradeage = racedate.year - self.dob.year - int((racedate.month, racedate.day) < (self.dob.month, self.dob.day))
            distmiles = self.stats[i].dist/METERSPERMILE
            agpercentage,agtime,agfactor = ag.agegrade(agegradeage,self.gender,distmiles,self.stats[i].time)
            self.stats[i].ag = agpercentage
            
            ### DEBUG>
            if debug:
                thisstat = {}
                for field in fields:
                    thisstat[field] = getattr(self.stats[i],field)
                DEB.writerow(thisstat)
            ### <DEBUG
            
        ### DEBUG>
        if debug:
            _DEB.close()
        ### <DEBUG
    
    #-------------------------------------------------------------------------------
    def render_stats(self,fig):
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
    
        # make hashed scatter lists
        hdate = {}
        hag = {}
        hsize = {}
        for thisd in self.dists:
            hdate[thisd] = []
            hag[thisd] = []
            hsize[thisd] = []
        for i in range(len(self.stats)):
            d = round(self.stats[i].dist)
            hdate[d].append(self.stats[i].date)
            hag[d].append(self.stats[i].ag)
            if self.size:
                hsize[d].append(distmap(d))
    #            hsize[d].append(self.stats['size'][i])
            else:
                hsize[d].append(DEFAULTSIZE)
        
        # create figure and axes
        fig.autofmt_xdate()
        ax = fig.get_axes()[0]  # only one axes instance
        ax.set_ylabel('age grade percentage')
        #ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d') # dead?
        fig.suptitle("{}".format(self.who))
            
        lines = []
        labs = []
        l_dists = sorted(self.dists)
        fig.subplots_adjust(bottom=0.1, right=0.85, top=0.93)
        ax.grid(b=True)
        for thisd in l_dists:
            # some results for this distance may have been pulled out due to filtering
            if len(hag[thisd]) == 0: continue
            
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
    
        # maybe user wants to set xlim
        ax.set_xlim(left=self.xlim['left'],right=self.xlim['right'])
            
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
                log.warning('{} of {} points found outside of ylim {}, runner {}'.format(outsidelimits,numpoints,self.ylim,self.who))
        
        # annotate
        
        ### DEBUG>
        if debug:
            _DEB.close()
        ### <DEBUG
    
    
    #-------------------------------------------------------------------------------
    def render_annotate(self, fig, s, xy, **kwargs):
    #-------------------------------------------------------------------------------
        '''
        plot a trend line
        
        see http://matplotlib.org/api/axes_api.html#matplotlib.axes.Axes.annotate for parameters
        '''
        ax = fig.get_axes()[0]  # only one axes instance
        ax.annotate(s,xy,**kwargs)
        
    #-------------------------------------------------------------------------------
    def render_trendline(self, fig, label, thesestats=None, color=None):
    #-------------------------------------------------------------------------------
        '''
        plot a trend line
        
        :param label: label for trendline
        :param thesestats: list of :class:`AgeGradeStat`, or None if all stats to be used
        :param color: color per matplotlib for trendline, or None to automate
        :rtype: :class:`TrendLine` containing parameters of trendline
        '''
        
        ax = fig.get_axes()[0]  # only one axes instance

        if not thesestats:
            thesestats = self.stats
        
        x = [mdates.date2num(s.date) for s in thesestats]
        y = [s.ag for s in thesestats]
        
        slope,intercept,rvalue,pvalue,stderr = stats.linregress(x,y)
        xline = ax.get_xlim()  # returns floats, not datetimes
        yline = [slope*thisx+intercept for thisx in xline]
        
        if color:
            ax.plot(xline,yline,color=color,linestyle='-',label=label)
        else:
            ax.plot(xline,yline,linestyle='-',label=label)

        return TrendLine(slope,intercept,rvalue,pvalue,stderr)
        
    #-------------------------------------------------------------------------------
    def save(self,fig):
    #-------------------------------------------------------------------------------
        '''
        save the plot in indicated file
        '''
        outfile = self.get_outfilename()
    
        ax = fig.get_axes()[0]  # only one axes instance
        smallfont = fontmgr.FontProperties(size='x-small')
        ax.legend(loc=1,bbox_to_anchor=(1.19, 1),prop=smallfont)    #bbox_to_anchor moves legend outside axes
        fig.savefig(outfile,format='png')
        
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
        dt_dob = tdisp.asc2dt(args.dob)
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
            print("YLIM argument must be of the form(bottom,top), e.g., (55,80)")
            return
    else:
        ylim = None

    # set up to analyze age grade
    aag = AnalyzeAgeGrade(size)
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
    
    # plot statistics
    fig = plt.figure()
    ax = fig.add_subplot(111)
    aag.render_stats(fig)
    aag.render_trendline(fig,'trend',color='k')
    aag.save(fig)
    
    
# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

