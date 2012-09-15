#!/usr/bin/python
# ##########################################################################################
#	gpx2kml - convert gpx file to kml format
#
#	Date		Author		Reason
#	----		------		------
#	08/29/12	Lou King	Create
#
# ##########################################################################################

# standard
import pdb
import optparse
import datetime
import os.path
from lxml import etree

# pypi
from pykml.factory import KML_ElementMaker as KML
from pykml.factory import GX_ElementMaker as GX

# github
import gpxpy
import gpxpy.geo

# home grown
from goccutils.inc import timeu # TBD need to figure out loutilities issue

METERPMILE = 1609.3439941
t = timeu.asctime('%Y-%m-%dT%H:%M:%SZ')

# ###############################################################################
def main():
# ###############################################################################

    usage = "usage: %prog [options] <gpxfile>\n\n"
    usage += "where:\n"
    usage += "  <gpxfile>\tgpx formatted file"

    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--points", dest="points", action="store_true", help="specify if points output is desired", default=False)
    parser.add_option("-f", "--flyover", dest="flyover", action="store_true", help="specify if flyover output is desired", default=False)
    parser.add_option("-c", "--color", dest="color", help="track color if not flyover", default='641400FF')
    parser.add_option("-o", "--output", dest="output", help="output file", default=None)
    (options, args) = parser.parse_args()

    # see http://www.zonums.com/gmaps/kml_color/
    colors = {'pink':'64781EF0', 'blue':'64F01E14'}
    
    gpxfile = args.pop(0)
    if options.output == None:
        outfile = os.path.basename(gpxfile) + '.kml'
    else:
        outfile = options.output

    # get input
    _GPX = open(gpxfile,'r')
    gpx = gpxpy.parse(_GPX)

    # create a KML file skeleton
    stylename = "sn_shaded_dot"
    color = colors[options.color]
    sty = KML.Style(
        KML.IconStyle(
            KML.scale(1.2),
            KML.Icon(
                KML.href("http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png")
                ),
            KML.color(colors[options.color]),
            ),
        id=stylename,
        )
    iconstylename = '#sn_shaded_dot'

    doc = KML.Document(
        KML.Name('generated from {0}'.format(gpxfile)),
        KML.open(1),
        )
    doc.append(sty)

    '''
    <TimeStamp>
      <when>1997-07-16T07:30:15Z</when>
    </TimeStamp>
    '''
    # loop through gpx tracks, creating kml placemarks
    times = []
    coords = []
    dists = []
    points = []
    lastpoint = None
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if not lastpoint:
                    lastpoint = point
                plon = point.longitude
                plat = point.latitude
                pelev = point.elevation
                points.append(point)
                thisdist = gpxpy.geo.distance(lastpoint.latitude, lastpoint.longitude, lastpoint.elevation, plat, plon, pelev)
                lastpoint = point
                dists.append(thisdist)
                ptime = t.dt2asc(point.time)
                times.append(ptime)
                coords.append('{lon},{lat},{alt}'.format(lon = plon,lat = plat,alt = 0))
    
    if options.flyover:
        plm = KML.Placemark()
        doc.append(plm)
        track = GX.track()
        plm.append(track)
        
        for when in times:
            track.append(KML.when(when))
        for coord in coords:
            track.append(KML.coordinates(coord))
            
        '''
        doc.append(KML.Placemark(
            KML.LookAt(
                KML.longitude(plon),
                KML.latitude(plat),
                KML.tilt(45),
                KML.heading(0),  # make this behind the guy
                KML.altitudeMode("relativeToGround"),
                KML.range(50),
                ),
            KML.Point(
                KML.altitudeMode("relativeToGround"),
                ,
                ,
                )
            ))
        '''
        
    elif options.points:
        #for coord in coords:
        #    ls.append(KML.coordinates(coord))
        lasttime = t.asc2epoch(times[0])
        totdist = 0
        for i in range(len(times)):
            thistime = t.asc2epoch(times[i])
            dur = thistime - lasttime
            lasttime = thistime
            totdist += dists[i]
            ex = KML.ExtendedData(
                KML.Data(KML.displayName('time'),KML.value(times[i])),
                KML.Data(KML.displayName('duration'),KML.value(dur)),
                KML.Data(KML.displayName('totdistance'),KML.value(int(round(totdist)))),
                )
            plm = KML.Placemark(
                #KML.name(times[i]),
                KML.name(''),
                KML.styleUrl(iconstylename),
                )
            plm.append(ex)
            plm.append(KML.Point(
                KML.altitudeMode('clampToGround'),
                KML.coordinates(coords[i])))
            doc.append(plm)
    
    else:
        if options.color:
            doc.append(
                KML.Style(
                    KML.LineStyle(
                    KML.color(colors[options.color]),
                    KML.width(5),
                    ),
                id=options.color))
            stylename = '#{0}'.format(options.color)
        
        '''
        <LineString id="ID">
          <!-- specific to LineString -->
          <gx:altitudeOffset>0</gx:altitudeOffset>  <!-- double -->
          <extrude>0</extrude>                      <!-- boolean -->
          <tessellate>0</tessellate>                <!-- boolean -->
          <altitudeMode>clampToGround</altitudeMode> 
              <!-- kml:altitudeModeEnum: clampToGround, relativeToGround, or absolute -->
              <!-- or, substitute gx:altitudeMode: clampToSeaFloor, relativeToSeaFloor -->
          <gx:drawOrder>0</gx:drawOrder>            <!-- integer --> 
          <coordinates>...</coordinates>            <!-- lon,lat[,alt] -->
        </LineString>
        '''
        plm = KML.Placemark(
            KML.name('runtrack'),
            )
        if options.color:
            plm.append(KML.styleUrl(stylename))
        doc.append(plm)
        ls = KML.LineString(
            KML.altitudeMode('clampToGround'),
#            KML.extrude(1),
#            KML.tessellate(1),
            )
        plm.append(ls)
        #for coord in coords:
        #    ls.append(KML.coordinates(coord))
        kcoords = ''
        for coord in coords:
            kcoords += coord + ' \n'
        ls.append(KML.coordinates(kcoords))
        
    _GPX.close()

    kml = KML.kml(doc)
    
    docstr = etree.tostring(kml, pretty_print=True)
    OUT = open(outfile,'w')
    OUT.write(docstr)
    OUT.close()

# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

