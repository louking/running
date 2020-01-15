#!/usr/bin/python
# ##########################################################################################
#	comparegpx - compare two gpx files
#
#	Date		Author		Reason
#	----		------		------
#	08/29/12	Lou King	Create
#
# ##########################################################################################
'''
comparegpx - compare two gpx files
=======================================
'''

# standard
import pdb
import optparse
import datetime
import os.path
import csv
import collections

# pypi
from pykml.factory import KML_ElementMaker as KML
from pykml.factory import GX_ElementMaker as GX

# github
import gpxpy
import gpxpy.geo

# home grown
from loutilities import timeu 

METERPMILE = 1609.3439941
t = timeu.asctime('%Y-%m-%dT%H:%M:%SZ')

class invalidCoeff(Exception): pass

# ###############################################################################
def main():
# ###############################################################################

    usage = "usage: %prog [options] <gpxfile1> <gpxfile2>\n\n"
    usage += "where:\n"
    usage += "  <gpxfile>\tgpx formatted file"

    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-o", "--output", dest="output", help="output file", default=None)
    (options, args) = parser.parse_args()

    gpxfile = {}
    _GPX = {}
    gpx = {}
    for f in range(2):
        gpxfile[f] = args.pop(0)
        _GPX[f] = open(gpxfile[f],'r')
        gpx[f] = gpxpy.parse(_GPX[f])
        _GPX[f].close()

    # loop through gpx tracks, collecting data
    times = {}
    dists = {}
    for f in range(2):
        times[f] = []
        dists[f] = []
        lastpoint = None
        totdist = 0
        for track in gpx[f].tracks:
            for segment in track.segments:
                for point in segment.points:
                    if not lastpoint:
                        lastpoint = point
                    plon = point.longitude
                    plat = point.latitude
                    pelev = point.elevation
                    thisdist = gpxpy.geo.distance(lastpoint.latitude, lastpoint.longitude, lastpoint.elevation, plat, plon, pelev)
                    lastpoint = point
                    totdist += thisdist
                    dists[f].append(totdist)
                    times[f].append(timeu.dt2epoch(point.time))
    
    # analyze every 5 seconds of data, interpolating between points, for all overlapping tracks
    earliest = max(times[0][0], times[1][0])    #max forces intersection
    latest = min(times[0][-1], times[1][-1])    #min forces intersection
    earliest = (int(earliest+5)//5)*5    # round to next 5 second boundary
    latest = (int(latest)//5)*5          # round to last 5 second boundary
    
    results = {}
    for f in range(2):
        titer = iter(times[f])
        diter = iter(dists[f])
        tdeq = collections.deque([],2)
        ddeq = collections.deque([],2)
        try:
            for time in range(earliest,latest,5):
                if time not in results:
                    results[time] = {0:None, 1:None}

                while len(tdeq) < 2 or tdeq[-1] < time: # try to scan times to get mult 5 time between measured time points
                    tdeq.append(next(titer))
                    ddeq.append(next(diter))
                
                #pdb.set_trace()
                interpcoeff = float(time-tdeq[0]) / (tdeq[1]-tdeq[0])
                if interpcoeff < 0 or interpcoeff > 1:  # logic error if this is true
                    raise invalidCoeff
                    
                thisdist = ddeq[0] + interpcoeff*(ddeq[1]-ddeq[0])
                results[time][f] = thisdist
                
        except StopIteration:
            pass
    
    if options.output == None:
        outfile = os.path.basename(gpxfile[0]) + '.csv'
    else:
        outfile = options.output
    OUT = open(outfile,'w')
    OUT.write('time,{0},{1}\n'.format(gpxfile[0],gpxfile[1]))
    for time in range(earliest,latest,5):
        OUT.write('{0},{1},{2}\n'.format(t.epoch2asc(time),results[time][0],results[time][1]))
    OUT.close()

# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

