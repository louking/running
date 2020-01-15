#!/usr/bin/python
###########################################################################################
#   racewx-render - render data from racewx.py
#
#	Date		Author		Reason
#	----		------		------
#	03/29/13        Lou King        Create
#
###########################################################################################
'''
racewx-render - render data from racewx.py
===================================================
'''

# standard
import pdb
import argparse
import csv
import copy
import re
import math

# pypi
import pytz 

# github

# other
import matplotlib.pyplot as plt
from matplotlib import dates
import matplotlib.font_manager as fm

# home grown
from . import version
from . import racewx
from running import *
from loutilities import timeu

#----------------------------------------------------------------------
def main():
#----------------------------------------------------------------------

    parser = argparse.ArgumentParser(version='{0} {1}'.format('running',version.__version__))
    parser.add_argument('infile',help='file generated by racewx')
    parser.add_argument('racename',help='race name')
    args = parser.parse_args()
    
    infile = args.infile
    racename = args.racename

    # get input
    _WX = open(infile,'rb')
    WX = csv.DictReader(_WX)
    wxdata = []
    for wx in WX:
        wxdata.append(wx)
    _WX.close()
    
    # for now, filter out all but the max 'exectime' entries
    lastexec = max([int(wx['exectime']) for wx in wxdata])
    while int(wxdata[0]['exectime']) != lastexec:
        wxdata.pop(0)
        
    # pull out fields to plot
    wxplot = {}
    plotfields = ['time','temperature','windchill','heatindex','dewpoint','windSpeed','windBearing','cloudCover','precipProbability','precipIntensity','cloudCover']
    for f in plotfields:
        wxplot[f] = [float(wx[f]) if wx[f]!='' else None for wx in wxdata]

    # get range on 30 minute boundaries
    starttime = int(wxplot['time'][0])
    fintime   = int(wxplot['time'][-1])
    adjstart  = (starttime // (30*60)) * (30*60)     # rounds to next lowest 30 minute boundary
    adjfin    = ((fintime-1 + 30*60) // (30*60)) * (30*60)         # rounds to next highest 30 minute boundary
    startdt = timeu.epoch2dt(adjstart)
    findt   = timeu.epoch2dt(adjfin)
    
    # time zone stuff, based on starting point
    lat = float(wxdata[0]['lat'])
    lon = float(wxdata[0]['lon'])
    tzid = racewx.gettzid(lat,lon)
    tz = pytz.timezone(tzid)
    wxplot['localtime'] = [timeu.utcdt2tzdt(timeu.epoch2dt(tm),tzid) for tm in wxplot['time']]
    
    # plot data
    fig = plt.figure()
    ttitle = timeu.asctime('%m/%d/%Y')
    racedate = ttitle.epoch2asc(wxplot['time'][0])
    fdate = ttitle.epoch2asc(lastexec)
    fig.suptitle('forecast for {race} {date}\nforecast date {fdate}\nPowered by Forecast.io'.format(race=racename,date=racedate,fdate=fdate),size='small')
    
    # set some formatting parameters
    lw = 0.5    # line width
    windcolor = 'b'
    legendx = 1.35
    
    # plot control
    exists = {}
    for f in ['windchill','heatindex']:
        exists[f] = len([it for it in wxplot[f] if it is not None]) != 0
    for f in ['precipIntensity']:
        exists[f] = len([it for it in wxplot[f] if it > 0.0]) != 0

    # plot temperatures
    ax1 = fig.add_subplot(311)
    ax1.plot(wxplot['localtime'],wxplot['temperature'],'k-',label='temperature', linewidth=lw)
    if exists['windchill']:
        ax1.plot(wxplot['localtime'],wxplot['windchill'],'b-',label='wind chill', linewidth=lw)
    if exists['heatindex']:
        ax1.plot(wxplot['localtime'],wxplot['heatindex'],'r-',label='heat index', linewidth=lw)
    ax1.plot(wxplot['localtime'],wxplot['dewpoint'],'g-',label='dew point', linewidth=lw)
    
    ax1.set_xlim(startdt,findt)
    fig.subplots_adjust(top=0.88,right=0.75,bottom=0.15)
    
    hfmt = dates.DateFormatter('%H:%M',tz=tz)
    ax1.xaxis.set_major_formatter(hfmt)
    ax1.xaxis.set_major_locator(dates.MinuteLocator(interval=30))    
    ax1.grid('on')
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax1.get_yticklabels(), fontsize='small')
    ax1.set_ylabel('degrees  \nFahrenheit', fontsize='small')

    #font = fm.FontProperties(fname='Humor-Sans.ttf')
    font = fm.FontProperties()
    xsmallfont = copy.deepcopy(font)
    xsmallfont.set_size('x-small')
    ax1.legend(prop=xsmallfont,loc='upper right', bbox_to_anchor=(legendx, 1))

    # plot wind
    ax2 = fig.add_subplot(312)
    ax2.plot(wxplot['localtime'],wxplot['windSpeed'],label='wind speed', linewidth=lw, color=windcolor)
    # note polar-> rectangular flips x,y from standard transformation because theta is from North instead of East
    # not sure why need to invert U and V to get barb to point in right direction.  Maybe vector comes from U,V and points to origin?
    U = [-1*wxplot['windSpeed'][i]*math.sin(math.radians(wxplot['windBearing'][i])) for i in range(len(wxplot['windSpeed']))] 
    V = [-1*wxplot['windSpeed'][i]*math.cos(math.radians(wxplot['windBearing'][i])) for i in range(len(wxplot['windSpeed']))]
    xdates = dates.date2num(wxplot['localtime'])    # barbs requires floats, not datetime
    ax2.barbs(xdates,wxplot['windSpeed'], U, V, length=5, barbcolor=windcolor, flagcolor=windcolor, linewidth=lw)

    ax2.set_xlim(dates.date2num(startdt),dates.date2num(findt))
    miny,maxy = ax2.get_ylim()
    ax2.set_ylim(round(miny*0.8),round(maxy*1.2))
    ax2.xaxis.set_major_formatter(hfmt)
    ax2.xaxis.set_major_locator(dates.MinuteLocator(interval=30))
    ax2.grid('on')
    #plt.setp(ax2.get_xticklabels(), rotation='vertical', fontsize='small')
    plt.setp(ax2.get_xticklabels(), visible=False)
    plt.setp(ax2.get_yticklabels(), fontsize='small')    
    ax2.set_ylabel('miles per hour', fontsize='small')
    ax2.legend(prop=xsmallfont,loc='upper right', bbox_to_anchor=(legendx, 1))
    
    ax3 = fig.add_subplot(313)
    precipprob = [100*(prob or 0) for prob in wxplot['precipProbability']]
    cloudcover = [100*(cover or 0) for cover in wxplot['cloudCover']]
    ax3.plot(wxplot['localtime'],precipprob,label='rain probability', linewidth=lw, color='b')
    ax3.plot(wxplot['localtime'],cloudcover,label='cloud cover', linewidth=lw, color='g')
    ax3.set_ylabel('percent', fontsize='small')

    ax3.set_xlim(dates.date2num(startdt),dates.date2num(findt))
    ax3.xaxis.set_major_formatter(hfmt)
    ax3.xaxis.set_major_locator(dates.MinuteLocator(interval=30))
    ax3.grid('on')
    ax3.set_ylim(0,100)
    plt.setp(ax3.get_xticklabels(), rotation='vertical', fontsize='small')
    plt.setp(ax3.get_yticklabels(), fontsize='small')    
    ax3.legend(prop=xsmallfont,loc='upper right', bbox_to_anchor=(legendx, 1.1))

    if exists['precipIntensity']:
        ax4 = ax3.twinx()
        #ax4.plot(wxplot['localtime'],wxplot['precipIntensity'],label='intensity', linewidth=lw, color='r')
        #ax4.set_yscale('log')
        ax4.semilogy(wxplot['localtime'],wxplot['precipIntensity'],label='intensity', nonposy='mask',linewidth=lw, color='r')
        #ax4.set_ylabel('precipitation 0.002 very light sprinkling, 0.017 light precipitation, 0.1 precipitation, and 0.4 very heavy precipitation')
        ax4.set_ylabel('intensity',fontsize='small')
        ax4.set_ylim(0,0.5)
        plt.setp(ax4.get_yticklabels(), fontsize='small')    
        ax4.legend(prop=xsmallfont,loc='upper right', bbox_to_anchor=(legendx, 0.75))

    tfile = timeu.asctime('%Y-%m-%d')
    fdate = tfile.epoch2asc(lastexec)
    racename = re.sub('\s','',racename) # remove whitespace
    outfile = 'race-weather-{race}-{fdate}.png'.format(race=racename,fdate=fdate)
    fig.savefig(outfile,format='png')


# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

