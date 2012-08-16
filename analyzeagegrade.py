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

    analyzeagegrade [options] agegradecsv file
    
    TBA
"""

# standard libraries
import csv
import pdb
from optparse import OptionParser
import math
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.dates as mdates
import matplotlib.font_manager as fontmgr
import timeu

# home grown libraries
import version

class unexpectedEOF(Exception): pass
class invalidParameter(Exception): pass

METERSPERMILE = 1609.344
MAXMETER = 9999
t = timeu.asctime('%m/%d/%Y')

################################################################################
def distmap(dist):
################################################################################
    """
    map distance to display metric
    
    :param dist: distance to map
    :rtype: float display metric for distance
    """
    return dist/100
    
################################################################################
def main():
################################################################################

    usage =  "  %prog [options] agfile [who]"
    usage += "\n     where:"
    usage += "\n        agfile is csv file containing Date, Distance (miles), AG headers"
    usage += "\n        who is name for chart header (default Lou)"

    parser = OptionParser(usage=usage,version='lourunning {0}'.format(version.__version__))
    parser.add_option('-s', '--size', action='store_true', dest='size', help="use if circle size by distance is desired")
    parser.set_defaults(plot=False) 
    (options, args) = parser.parse_args()
    if len(args) == 0 or len(args) > 2:
        parser.error("incorrect number of arguments")
    agfile = args.pop(0)
    if len(args) > 0:
        who = args.pop(0)
    else:
        who = "Lou"
    
    _IN = open(agfile,'r')
    IN = csv.DictReader(_IN,dialect='excel')

    s_size = 'color'
    if options.size:
        s_size = 'size'
    outfile = '{0}-ag-analysis-{1}.png'.format(who,s_size)
    stats = {}
    for stype in ['date','dist','size','ag']:
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
        
        s_ag = inrow['AG']
        if not s_ag: continue   # we don't care about this entry if AG wasn't captured
        if s_ag[-1] == '%':
            ag = float(s_ag[:-1])
        else:
            ag = float(s_ag)
            
        dists.add(round(dist))      # keep track of distances to nearest meter
        stats['date'].append(date)
        stats['dist'].append(dist)
        stats['size'].append(distmap(dist))
        stats['ag'].append(ag)
        #print(s_date,date,dist,ag)
        
    _IN.close()
    
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
        if options.size:
            hsize[d].append(stats['size'][i])
        else:
            hsize[d].append(60)
        
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
    fig.suptitle("{0}'s age grade performance over time\n{1} indicates race distance".format(who,s_size))
        
    lines = []
    labs = []
    l_dists = list(dists)
    l_dists.sort()
    fig.subplots_adjust(bottom=0.1, right=0.8, top=0.9)
    ax.grid(b=True)
    for thisd in l_dists:
        if thisd <=MAXMETER:
            lab = '{0}m'.format(int(thisd))
        else:
            lab = '{0:.1f}km'.format(thisd/1000)
        labs.append(lab)
        line = ax.scatter(hdate[thisd],hag[thisd],s=hsize[thisd],c=cmapsm.to_rgba(thisd),label=lab,linewidth=.5)
        #line = ax.scatter(hdate[thisd],hag[thisd],s=60,c=cmapsm.to_rgba(thisd),label=lab,edgecolors='none')
        lines.append(line)
    smallfont = fontmgr.FontProperties(size='small')
    ax.legend(loc=1,bbox_to_anchor=(1.25, 1),prop=smallfont)    #bbox_to_anchor moves legend outside axes
    fig.savefig(outfile,format='png')
        
    
# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

